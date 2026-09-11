#!/usr/bin/env bash
# Deploy MiraWorld at http://<ip>/miraworld/ — keeps bykc homepage at /
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

# Remove domain-only site if present (ignore domain for now)
sudo rm -f /etc/nginx/sites-enabled/miraworld

# Move stray backups out of sites-enabled
shopt -s nullglob
for f in /etc/nginx/sites-enabled/*.bak* /etc/nginx/sites-enabled/*~; do
  sudo mv "$f" "$BACKUP_DIR/"
done
shopt -u nullglob

DEFAULT_SITE=""
for f in /etc/nginx/sites-enabled/bykc /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/*; do
  base=$(basename "$f")
  case "$base" in
    miraworld|*.bak*|*.bak|*.old|*~) continue ;;
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

# Ensure bykc/default includes miraworld snippet (replace old redirect include if any)
sudo python3 - <<PY
from pathlib import Path
p = Path("$DEFAULT_SITE").resolve()
text = p.read_text(encoding="utf-8")
wanted = "include /etc/nginx/snippets/miraworld.conf;"
old_redir = "include /etc/nginx/snippets/miraworld-ip-redirect.conf;"
changed = False
if old_redir in text:
    text = text.replace(old_redir, wanted)
    changed = True
if wanted not in text:
    idx = text.rfind("}")
    if idx < 0:
        raise SystemExit("cannot find closing brace")
    text = text[:idx] + "    " + wanted + "\n" + text[idx:]
    changed = True
if changed:
    Path("$BACKUP_DIR").mkdir(parents=True, exist_ok=True)
    bak = Path("$BACKUP_DIR") / (p.name + ".ipfix.bak")
    bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(text, encoding="utf-8")
    print("patched", p)
else:
    print("include already present", p)
PY

sudo find "$SITE_ROOT" -mindepth 1 -delete
sudo tar -xzf /tmp/miraworld-dist.tar.gz -C "$SITE_ROOT"
sudo chown -R www-data:www-data "$SITE_ROOT"
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "bykc:      http://$(curl -fsS ifconfig.me)/"
echo "MiraWorld: http://$(curl -fsS ifconfig.me)/miraworld/"
