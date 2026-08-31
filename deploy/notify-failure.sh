#!/usr/bin/env bash
#
# deploy/notify-failure.sh — send an alert when a deploy fails.
#
# Wired via `OnFailure=tracey-deploy-notify@%n.service` on tracey-deploy.service.
# Runs as root (so it can read the journal). Reads channel config from
# /etc/tracey-deploy/notify.env — set NOTIFY_EMAIL and/or NOTIFY_WEBHOOK there.
#
# Manual test:  sudo deploy/notify-failure.sh tracey-deploy.service
#
set -euo pipefail

UNIT="${1:-tracey-deploy.service}"
CONFIG="${CONFIG:-/etc/tracey-deploy/notify.env}"

# shellcheck disable=SC1090
[ -f "$CONFIG" ] && . "$CONFIG" || true

host="$(hostname -s 2>/dev/null || hostname)"
when="$(date -Is)"
log="$(journalctl -u "$UNIT" -n 40 --no-pager -o cat 2>/dev/null || echo '(journal unavailable)')"

subject="[traceyDB] deploy FAILED on ${host}"
body="${UNIT} failed at ${when} on ${host}

deploy.sh rolls back automatically — verify https://tracey.unil.ch/ and run
  sudo journalctl -u ${UNIT} -n 120

last 40 log lines:
\`\`\`
${log}
\`\`\`"

sent=0

if [ -n "${NOTIFY_EMAIL:-}" ] && command -v mail >/dev/null 2>&1; then
  if printf '%s\n' "$body" | mail -s "$subject" "$NOTIFY_EMAIL"; then
    sent=1
  fi
fi

if [ -n "${NOTIFY_WEBHOOK:-}" ]; then
  # Slack / Mattermost / Discord / Teams all accept a simple {"text": "..."}.
  if payload="$(printf ':rotating_light: %s\n%s' "$subject" "$body" \
        | python3 -c 'import json,sys; print(json.dumps({"text": sys.stdin.read()}))' 2>/dev/null)"; then
    :
  else
    payload="{\"text\": \":rotating_light: ${subject} (see server journal)\"}"
  fi
  if curl -fsS -m 10 -X POST -H 'Content-Type: application/json' -d "$payload" "$NOTIFY_WEBHOOK" >/dev/null; then
    sent=1
  fi
fi

if [ "$sent" -eq 0 ]; then
  echo "notify-failure: nothing sent (no working channel in $CONFIG)" >&2
  exit 1
fi
echo "notify-failure: alert sent for $UNIT"
