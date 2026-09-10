#!/usr/bin/env bash
# Run on the Ubuntu server (admin). Pulls MiraWorld build from GitHub Release and enables Nginx.
set -euo pipefail

DIST_URL="${DIST_URL:-https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/miraworld-dist.tar.gz}"
SITE_ROOT=/var/www/miraworld

sudo mkdir -p "$SITE_ROOT"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx curl

curl -fsSL -o /tmp/miraworld-dist.tar.gz "$DIST_URL"

sudo tee /etc/nginx/sites-available/miraworld >/dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/miraworld;
    index index.html;
    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }
}
EOF

sudo ln -sfn /etc/nginx/sites-available/miraworld /etc/nginx/sites-enabled/miraworld
sudo rm -f /etc/nginx/sites-enabled/default
sudo find "$SITE_ROOT" -mindepth 1 -delete
sudo tar -xzf /tmp/miraworld-dist.tar.gz -C "$SITE_ROOT"
sudo chown -R www-data:www-data "$SITE_ROOT"
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "OK http://$(curl -fsS ifconfig.me)/"
