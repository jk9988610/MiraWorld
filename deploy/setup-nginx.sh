#!/usr/bin/env bash
# Enable /miraworld/ on the IP (bykc) site by including a snippet.
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

# Snippet files are not auto-loaded; patch bykc/default to include it.
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
    marker = "server_name _;"
    insert = marker + "\n\n    " + wanted
    if marker in text:
        text = text.replace(marker, insert, 1)
        changed = True
    else:
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

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "Nginx ready: /miraworld/  root=$SITE_ROOT"