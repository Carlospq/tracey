#!/usr/bin/env bash
#
# deploy/poll-deploy.sh — pull-based CD for traceyDB.
#
# Run periodically by tracey-deploy.timer (as the user that can sudo, e.g.
# cpulidoq). It checks origin for `deploy/*` tags and, when a newer one than
# the last deployed appears AND its CI checks are green, runs deploy/deploy.sh.
#
# Creating + pushing a `deploy/<stamp>` tag is the human approval step:
#     git tag -a deploy/20260831-1400 -m "Deploy: what changed"
#     git push origin deploy/20260831-1400
#
# Set REQUIRE_CI=0 to skip the CI-green gate (emergency use). The manual path,
# `DEPLOY_REF=<ref> deploy/deploy.sh`, never checks CI.
#
# The whole body lives in main() so that `git reset --hard` (which may rewrite
# THIS file) cannot change code that bash has not parsed yet.
set -euo pipefail

REPO="${REPO:-Carlospq/tracey}"

# Print one word describing the CI state of a commit:
#   green | pending | nochecks | unreachable | failed=<name,name>
ci_status() {
  local sha="$1" json
  if ! json="$(curl -fsS -m 15 -H 'Accept: application/vnd.github+json' \
        "https://api.github.com/repos/$REPO/commits/$sha/check-runs" 2>/dev/null)"; then
    echo "unreachable"; return 0
  fi
  CI_JSON="$json" python3 - <<'PY'
import json, os
d = json.loads(os.environ["CI_JSON"])
runs = d.get("check_runs", [])
if not runs:
    print("nochecks")
elif any(r.get("status") != "completed" for r in runs):
    print("pending")
else:
    bad = [r["name"] for r in runs
           if r.get("conclusion") not in ("success", "neutral", "skipped")]
    print("failed=" + ",".join(bad) if bad else "green")
PY
}

main() {
  local CLONE="${CLONE:-$HOME/tracey-deploy}"
  local STATE_DIR="${STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/tracey-deploy}"
  local TAG_GLOB='deploy/*'
  local LAST_FILE="$STATE_DIR/last-tag"
  local REFUSED_FILE="$STATE_DIR/last-refused"
  local LOCK_FILE="$STATE_DIR/lock"

  mkdir -p "$STATE_DIR"

  # Never let two poll runs (or a poll + a slow previous deploy) overlap.
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "$(date -Is)  another deploy is in progress — skipping this tick"
    return 0
  fi

  cd "$CLONE"
  git fetch --tags --force --prune origin --quiet
  # Keep the control clone's own tooling (this script, deploy.sh) current.
  git reset --hard origin/main --quiet

  # Newest deploy/* tag (annotated tags sort by tagger date).
  local target_tag
  target_tag="$(git tag -l "$TAG_GLOB" --sort=-creatordate | head -n1)"
  if [ -z "$target_tag" ]; then
    echo "$(date -Is)  no $TAG_GLOB tags on origin yet — nothing to do"
    return 0
  fi

  local last_tag
  last_tag="$(cat "$LAST_FILE" 2>/dev/null || true)"
  if [ "$target_tag" = "$last_tag" ]; then
    return 0   # already handled this tag; stay quiet
  fi

  local target_sha
  target_sha="$(git rev-list -n1 "$target_tag" 2>/dev/null || echo '?')"

  # --- CI-green gate -----------------------------------------------------
  if [ "${REQUIRE_CI:-1}" = "1" ]; then
    local refused now ci
    refused="$(cat "$REFUSED_FILE" 2>/dev/null || true)"
    now="$(date +%s)"
    # If we already refused THIS tag less than 5 min ago, don't hammer the API.
    if [ "${refused%%:*}" = "$target_tag" ] && [ $(( now - ${refused##*:} )) -lt 300 ]; then
      return 0
    fi
    ci="$(ci_status "$target_sha")"
    if [ "$ci" != "green" ]; then
      case "$refused" in
        "$target_tag:$ci:"*) : ;;                                  # already logged this state
        *) echo "$(date -Is)  NOT deploying $target_tag ($target_sha): CI = $ci" ;;
      esac
      printf '%s:%s:%s' "$target_tag" "$ci" "$now" > "$REFUSED_FILE"
      return 0
    fi
    : > "$REFUSED_FILE"
    echo "$(date -Is)  CI green for $target_sha"
  fi

  echo "$(date -Is)  new deploy tag: $target_tag ($target_sha)  [previous: ${last_tag:-none}]"

  local rc=0
  DEPLOY_REF="$target_tag" bash "$CLONE/deploy/deploy.sh" || rc=$?

  # Mark the tag as handled whether it succeeded or was rolled back, so a bad
  # tag does not redeploy every 2 minutes. Fix forward with a new tag.
  echo "$target_tag" > "$LAST_FILE"

  if [ "$rc" -eq 0 ]; then
    echo "$(date -Is)  deploy OK: $target_tag"
    sudo bash "$CLONE/deploy/notify.sh" ok \
      "Deployed $target_tag ($target_sha) to production." || true
  else
    echo "$(date -Is)  deploy FAILED (rc=$rc): $target_tag — deploy.sh rolled back; push a new tag to retry"
    sudo bash "$CLONE/deploy/notify.sh" fail \
      "Deploy of $target_tag ($target_sha) failed — deploy.sh rolled production back. Push a new tag to retry." || true
  fi

  # We did our job (checked CI, deployed, reported the result). Return 0 so
  # systemd does not ALSO fire OnFailure=; that path is reserved for this
  # script crashing before it could notify.
  return 0
}

main "$@"
