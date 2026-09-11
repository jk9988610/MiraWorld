#!/usr/bin/env bash
# Enable /miraworld/ on the IP (bykc) site.
set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
SITE_ROOT="$WEB_ROOT/miraworld"
SNIPPET=/etc/nginx/snippets/miraworld.conf
BACKUP_DIR=/etc/nginx/backup
CONF_SRC="${1:-$(cd "$(dirname "$0")" && pwd)/nginx-miraworld.conf}"

sudo mkdir -p "$SITE_ROOT" /etc/nginx/snippets "$BACKUP_DIR"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
sudo cp "$CONF_SRC" "$SNIPPET"
sudo rm -f /etc/nginx/sites-enabled/miraworld

shopt -s nullglob
for f in /etc/nginx/sites-enabled/*.bak* /etc/nginx/sites-enabled/*~; do
  sudo mv "$f" "$BACKUP_DIR/"
done
shopt -u nullglob

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "Nginx ready: /miraworld/  root=$SITE_ROOT"
