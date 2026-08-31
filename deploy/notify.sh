#!/usr/bin/env bash
#
# deploy/notify.sh — send a deploy notification to Slack (and/or email).
#
# Usage:  notify.sh <ok|fail|crash> "<summary>" [systemd-unit]
#
#   ok     deploy succeeded              -> :white_check_mark:  summary only
#   fail   deploy failed + rolled back   -> :rotating_light:    summary + journal tail
#   crash  poll job died unexpectedly    -> :warning:           summary + journal tail
#
# Channels come from /etc/tracey-deploy/notify.env (NOTIFY_EMAIL / NOTIFY_WEBHOOK).
# Called by poll-deploy.sh (ok/fail) and by tracey-deploy-notify@.service (crash).
set -euo pipefail

STATUS="${1:-fail}"
SUMMARY="${2:-(no summary)}"
UNIT="${3:-tracey-deploy.service}"
CONFIG="${CONFIG:-/etc/tracey-deploy/notify.env}"

# shellcheck disable=SC1090
[ -f "$CONFIG" ] && . "$CONFIG" || true

host="$(hostname -s 2>/dev/null || hostname)"
when="$(date -Is)"

case "$STATUS" in
  ok)    icon=":white_check_mark:" ; head="[traceyDB] deploy OK on ${host}"      ; want_log=0 ;;
  crash) icon=":warning:"          ; head="[traceyDB] deploy job CRASHED on ${host}" ; want_log=1 ;;
  *)     icon=":rotating_light:"   ; head="[traceyDB] deploy FAILED on ${host}"  ; want_log=1 ;;
esac

body="${head}
${when}

${SUMMARY}"

if [ "$want_log" -eq 1 ]; then
  log="$(journalctl -u "$UNIT" -n 40 --no-pager -o cat 2>/dev/null || echo '(journal unavailable)')"
  body="${body}

last log lines:
\`\`\`
${log}
\`\`\`
verify https://tracey.unil.ch/  ·  sudo journalctl -u ${UNIT} -n 120"
fi

sent=0

if [ -n "${NOTIFY_EMAIL:-}" ] && command -v mail >/dev/null 2>&1; then
  printf '%s\n' "$body" | mail -s "$head" "$NOTIFY_EMAIL" && sent=1 || true
fi

if [ -n "${NOTIFY_WEBHOOK:-}" ]; then
  if ! payload="$(printf '%s %s' "$icon" "$body" \
        | python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))' 2>/dev/null)"; then
    payload="{\"text\": \"${icon} ${head}\"}"
  fi
  curl -fsS -m 10 -X POST -H 'Content-Type: application/json' -d "$payload" "$NOTIFY_WEBHOOK" >/dev/null && sent=1 || true
fi

if [ "$sent" -eq 0 ]; then
  echo "notify: nothing sent (no working channel in $CONFIG)" >&2
  exit 1
fi
echo "notify: $STATUS sent"
