#!/usr/bin/env bash
#
# deploy/poll-deploy.sh — pull-based CD for traceyDB.
#
# Run periodically by tracey-deploy.timer (as the user that can sudo, e.g.
# cpulidoq). It checks origin for `deploy/*` tags and, when a newer one than
# the last deployed appears, runs deploy/deploy.sh against it.
#
# Creating + pushing a `deploy/<stamp>` tag is the human approval step:
#     git tag -a deploy/20260831-1400 -m "Deploy: what changed"
#     git push origin deploy/20260831-1400
#
# The whole body lives in main() so that `git reset --hard` (which may rewrite
# THIS file) cannot change code that bash has not parsed yet.
set -euo pipefail

main() {
  local CLONE="${CLONE:-$HOME/tracey-deploy}"
  local STATE_DIR="${STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/tracey-deploy}"
  local TAG_GLOB='deploy/*'
  local LAST_FILE="$STATE_DIR/last-tag"
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
  echo "$(date -Is)  new deploy tag: $target_tag ($target_sha)  [previous: ${last_tag:-none}]"

  local rc=0
  DEPLOY_REF="$target_tag" bash "$CLONE/deploy/deploy.sh" || rc=$?

  # Mark the tag as handled whether it succeeded or was rolled back, so a bad
  # tag does not redeploy every 2 minutes. Fix forward with a new tag.
  echo "$target_tag" > "$LAST_FILE"

  if [ "$rc" -eq 0 ]; then
    echo "$(date -Is)  deploy OK: $target_tag"
  else
    echo "$(date -Is)  deploy FAILED (rc=$rc): $target_tag — deploy.sh rolled back; push a new tag to retry"
  fi
  return "$rc"
}

main "$@"
