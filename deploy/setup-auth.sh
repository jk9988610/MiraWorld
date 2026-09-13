#!/usr/bin/env bash
# Install or update MiraWorld auth API on the server.
set -euo pipefail

AUTH_ROOT="/opt/miraworld-auth"
AUTH_SRC="/tmp/miraworld-auth-src"
DB_DIR="/var/lib/miraworld"
ENV_FILE="/etc/miraworld/auth.env"
SERVICE="miraworld-auth.service"

sudo mkdir -p "$AUTH_ROOT" "$DB_DIR" /etc/miraworld
sudo cp -a "$AUTH_SRC/." "$AUTH_ROOT/"
sudo chown -R www-data:www-data "$AUTH_ROOT" "$DB_DIR"

if [[ ! -d "$AUTH_ROOT/venv" ]]; then
  sudo python3 -m venv "$AUTH_ROOT/venv"
fi

sudo "$AUTH_ROOT/venv/bin/pip" install -q -r "$AUTH_ROOT/requirements.txt"

if [[ ! -f "$ENV_FILE" ]]; then
  sudo tee "$ENV_FILE" >/dev/null <<'EOF'
MIRAWORLD_ENV=production
MIRAWORLD_DB=/var/lib/miraworld/miraworld.db
MIRAWORLD_JWT_SECRET=CHANGE_ME_RUN_openssl_rand_hex_32
MIRAWORLD_TICK_SECRET=CHANGE_ME_RUN_openssl_rand_hex_32
EOF
  echo "WARNING: edit $ENV_FILE and set MIRAWORLD_JWT_SECRET before relying on auth in production."
fi

sudo cp /tmp/miraworld-auth.service "/etc/systemd/system/$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

echo "Auth API: systemctl status $SERVICE"
