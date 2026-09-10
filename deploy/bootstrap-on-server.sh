#!/usr/bin/env bash
# Install MiraWorld under http://<host>/miraworld/ — keeps bykc homepage at /
set -euo pipefail

DIST_URL="${DIST_URL:-https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/miraworld-dist.tar.gz}"
WEB_ROOT="${WEB_ROOT:-/var/www/html}"
SITE_ROOT="$WEB_ROOT/miraworld"
SNIPPET=/etc/nginx/snippets/miraworld.conf
BACKUP_DIR=/etc/nginx/backup

sudo mkdir -p "$SITE_ROOT" /etc/nginx/snippets "$BACKUP_DIR"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx curl

curl -fsSL -o /tmp/miraworld-dist.tar.gz "$DIST_URL"

sudo tee "$SNIPPET" >/dev/null <<'EOF'
location = /miraworld {
    return 301 /miraworld/;
}

location ^~ /miraworld/ {
    root /var/www/html;
    index index.html;
    try_files $uri $uri.html /miraworld/index.html;
}
EOF

# Backups must NOT live in sites-enabled (nginx loads every file there).
sudo mkdir -p "$BACKUP_DIR"
shopt -s nullglob
for f in /etc/nginx/sites-enabled/*.bak* /etc/nginx/sites-enabled/*~; do
  echo "Moving stray backup out of sites-enabled: $f"
  sudo mv "$f" "$BACKUP_DIR/"
done
shopt -u nullglob

# Prefer bykc / default; skip backup-looking names
DEFAULT_SITE=""
for f in /etc/nginx/sites-enabled/bykc /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/*; do
  base=$(basename "$f")
  case "$base" in
    *.bak*|*.bak|*.old|*~) continue ;;
  esac
  if [ -f "$f" ] || [ -L "$f" ]; then
    DEFAULT_SITE="$f"
    break
  fi
done

if [ -z "$DEFAULT_SITE" ]; then
  echo "No nginx site config found under /etc/nginx/sites-enabled" >&2
  exit 1
fi

if ! grep -q 'snippets/miraworld.conf' "$DEFAULT_SITE"; then
  sudo cp "$DEFAULT_SITE" "$BACKUP_DIR/$(basename "$DEFAULT_SITE").$(date +%Y%m%d%H%M%S).bak"
  sudo python3 - <<PY
from pathlib import Path
p = Path("$DEFAULT_SITE")
# Follow symlink to real file for editing
real = Path(p).resolve()
text = real.read_text(encoding="utf-8")
inc = "    include /etc/nginx/snippets/miraworld.conf;\n"
if "snippets/miraworld.conf" in text:
    raise SystemExit(0)
idx = text.rfind("}")
if idx < 0:
    raise SystemExit("cannot find closing brace in " + str(real))
real.write_text(text[:idx] + inc + text[idx:], encoding="utf-8")
print("patched", real)
PY
fi

sudo find "$SITE_ROOT" -mindepth 1 -delete
sudo tar -xzf /tmp/miraworld-dist.tar.gz -C "$SITE_ROOT"
sudo chown -R www-data:www-data "$SITE_ROOT"
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "bykc home: http://$(curl -fsS ifconfig.me)/"
echo "MiraWorld:  http://$(curl -fsS ifconfig.me)/miraworld/"
