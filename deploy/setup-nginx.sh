#!/usr/bin/env bash
# Run on the server (Ubuntu) as a user with sudo.
set -euo pipefail

SITE_ROOT=/var/www/miraworld
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_SRC="${1:-$SCRIPT_DIR/nginx-miraworld.conf}"

sudo mkdir -p "$SITE_ROOT"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx

sudo cp "$CONF_SRC" /etc/nginx/sites-available/miraworld
sudo ln -sfn /etc/nginx/sites-available/miraworld /etc/nginx/sites-enabled/miraworld
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx

echo "Nginx ready. Upload dist to $SITE_ROOT"
