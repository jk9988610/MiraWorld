#!/usr/bin/env bash
# Daily economy tick for 潮灯市 (called from cron).
set -euo pipefail

ENV_FILE="/etc/miraworld/auth.env"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

SECRET="${MIRAWORLD_TICK_SECRET:-dev-tick-secret}"
CITY="${MIRAWORLD_ECONOMY_CITY:-潮灯市}"

curl -sf -X POST \
  "http://127.0.0.1/miraworld/api/economy/tick?city=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${CITY}'))")" \
  -H "X-Tick-Secret: ${SECRET}" \
  -H "Accept: application/json"

echo
