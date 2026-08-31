#!/usr/bin/env bash
#
# deploy/deploy.sh — deploy traceyDB to the UNIL production server.
#
# WHO RUNS THIS: a user with passwordless sudo (e.g. cpulidoq).
# The web install is owned by the unprivileged 'tracey' user, so this script
# does the code steps with `sudo -u tracey` and only the restart as root.
#
# WHAT IT DOES:
#   1. refuses to run if the server working tree has uncommitted tracked changes
#   2. checks out the target revision in /home/tracey/tracey  (as tracey)
#   3. pip install + migrate + collectstatic                  (as tracey)
#   4. restarts gunicorn                                      (sudo, as root)
#   5. health-checks http://127.0.0.1:5005/
#   6. rolls back to the previous commit if the health check fails
#
# USAGE:
#   deploy/deploy.sh                      # deploy origin/main
#   DEPLOY_REF=v1.4.0 deploy/deploy.sh    # deploy a tag
#   DEPLOY_REF=<sha>  deploy/deploy.sh    # manual rollback to a known-good commit
#   SKIP_MIGRATE=1    deploy/deploy.sh    # skip `manage.py migrate`
#
set -euo pipefail

# ------------------------------------------------------------------ config ---
APP_USER="${APP_USER:-tracey}"
APP_DIR="${APP_DIR:-/home/tracey/tracey}"
VENV="${VENV:-/home/tracey/tracey_prod}"
SERVICE="${SERVICE:-gunicorn.service}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5005/}"
DEPLOY_REF="${DEPLOY_REF:-origin/main}"
SKIP_MIGRATE="${SKIP_MIGRATE:-0}"

PY="$VENV/bin/python3"
PIP="$PY -m pip"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
err() { printf '\n\033[1;31m!!!\033[0m %s\n' "$*" >&2; }

# Run a command inside the app dir as the app user.
as_app() { sudo -u "$APP_USER" -H bash -c "cd '$APP_DIR' && $*"; }

update_code() {
  local ref="$1"
  as_app "git fetch --tags --prune origin"
  as_app "git checkout -f main && git reset --hard '$ref'"
  as_app "$PIP install --no-input -q -r requirements.txt"
  if [ "$SKIP_MIGRATE" != "1" ]; then
    as_app "$PY manage.py migrate --noinput"
  fi
  as_app "$PY manage.py collectstatic --noinput"
}

restart_service() { sudo systemctl restart "$SERVICE"; }

health_ok() {
  local i
  for i in $(seq 1 10); do
    if curl -fsS -o /dev/null --max-time 5 "$HEALTH_URL"; then return 0; fi
    sleep 2
  done
  return 1
}

# ------------------------------------------------------------------ deploy ---
log "Checking the server working tree is clean ..."
DIRTY="$(as_app "git status --porcelain --untracked-files=no" || true)"
if [ -n "$DIRTY" ]; then
  err "$APP_DIR has uncommitted changes to tracked files:"
  printf '%s\n' "$DIRTY" >&2
  err "Refusing to deploy — commit, stash or revert them on the server first."
  exit 1
fi

PREV_SHA="$(as_app "git rev-parse HEAD")"
log "Current revision : $PREV_SHA"
log "Deploy target    : $DEPLOY_REF"

log "Updating code, dependencies, migrations, static files ..."
update_code "$DEPLOY_REF"
NEW_SHA="$(as_app "git rev-parse HEAD")"
log "New revision     : $NEW_SHA"

if [ "$NEW_SHA" = "$PREV_SHA" ]; then
  log "Nothing changed — $NEW_SHA already deployed. Restarting anyway."
fi

log "Restarting $SERVICE ..."
restart_service

log "Health check: $HEALTH_URL"
if health_ok; then
  log "DEPLOY OK — $NEW_SHA is live."
  exit 0
fi

err "Health check FAILED after deploying $NEW_SHA — rolling back to $PREV_SHA"
SKIP_MIGRATE=1 update_code "$PREV_SHA"
restart_service
if health_ok; then
  err "Rolled back to $PREV_SHA. Deploy of $NEW_SHA was aborted."
else
  err "ROLLBACK IS ALSO UNHEALTHY — manual intervention needed NOW."
fi
exit 1
