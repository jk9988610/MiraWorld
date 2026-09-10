#!/usr/bin/env bash
# Install nginx snippet for /miraworld/ (does not replace bykc at /).
set -euo pipefail

WEB_ROOT="${WEB_ROOT:-/var/www/html}"
SITE_ROOT="$WEB_ROOT/miraworld"
SNIPPET=/etc/nginx/snippets/miraworld.conf
CONF_SRC="${1:-$(cd "$(dirname "$0")" && pwd)/nginx-miraworld.conf}"

sudo mkdir -p "$SITE_ROOT" /etc/nginx/snippets
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
sudo cp "$CONF_SRC" "$SNIPPET"

DEFAULT_SITE=""
for f in /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/*; do
  if [ -f "$f" ] || [ -L "$f" ]; then
    DEFAULT_SITE="$f"
    break
  fi
done

if [ -n "$DEFAULT_SITE" ] && ! grep -q 'snippets/miraworld.conf' "$DEFAULT_SITE"; then
  sudo cp "$DEFAULT_SITE" "${DEFAULT_SITE}.bak.miraworld"
  sudo python3 - <<PY
from pathlib import Path
p = Path("$DEFAULT_SITE")
text = p.read_text(encoding="utf-8")
inc = "    include /etc/nginx/snippets/miraworld.conf;\n"
if "snippets/miraworld.conf" not in text:
    idx = text.rfind("}")
    if idx < 0:
        raise SystemExit("cannot find closing brace")
    p.write_text(text[:idx] + inc + text[idx:], encoding="utf-8")
PY
fi

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "Nginx ready for $SITE_ROOT (URL /miraworld/)"
