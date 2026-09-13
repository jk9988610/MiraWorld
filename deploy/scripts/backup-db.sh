#!/usr/bin/env bash
# Daily SQLite backup for MiraWorld production DB.
# Installed to /var/lib/miraworld/scripts/backup-db.sh by deploy/backup_db.py
set -euo pipefail

DB="${MIRAWORLD_DB:-/var/lib/miraworld/miraworld.db}"
BACKUP_DIR="${MIRAWORLD_BACKUP_DIR:-/var/lib/miraworld/backups}"
KEEP_DAYS="${MIRAWORLD_BACKUP_KEEP_DAYS:-7}"

if [[ ! -f "$DB" ]]; then
  echo "backup-db: missing database $DB" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%d-%H%M%S)"
dest="$BACKUP_DIR/miraworld-${stamp}.db"

# Online backup via sqlite3 .backup (safe while API is running)
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" ".backup '$dest'"
else
  cp -a "$DB" "$dest"
fi

chown www-data:www-data "$dest" 2>/dev/null || true
chmod 640 "$dest" 2>/dev/null || true

find "$BACKUP_DIR" -name 'miraworld-*.db' -type f -mtime +"$KEEP_DAYS" -delete

echo "backup-db: wrote $dest (keep ${KEEP_DAYS}d)"
