#!/usr/bin/env python3
"""Backup production miraworld.db via SSH; optionally install daily cron on server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy as d

SCRIPT_LOCAL = Path(__file__).resolve().parent / "scripts" / "backup-db.sh"
REMOTE_SCRIPT = "/var/lib/miraworld/scripts/backup-db.sh"
CRON_FILE = "/etc/cron.d/miraworld-db-backup"
CRON_LINE = "0 3 * * * root /var/lib/miraworld/scripts/backup-db.sh >> /var/log/miraworld-backup.log 2>&1\n"


def upload_script(client) -> None:
    if not SCRIPT_LOCAL.is_file():
        raise RuntimeError(f"Missing {SCRIPT_LOCAL}")
    sftp = client.open_sftp()
    try:
        remote_tmp = "/tmp/miraworld-backup-db.sh"
        sftp.put(str(SCRIPT_LOCAL), remote_tmp)
    finally:
        sftp.close()
    d.run(
        client,
        f"""
set -e
sudo mkdir -p /var/lib/miraworld/scripts /var/lib/miraworld/backups
sudo install -m 755 {remote_tmp} {REMOTE_SCRIPT}
sudo rm -f {remote_tmp}
""",
    )


def run_backup(client) -> None:
    d.run(client, f"sudo bash {REMOTE_SCRIPT}")


def install_cron(client) -> None:
    upload_script(client)
    d.run(
        client,
        f"""
set -e
echo '{CRON_LINE.strip()}' | sudo tee {CRON_FILE} >/dev/null
sudo chmod 644 {CRON_FILE}
""",
    )
    print(f"Cron installed: {CRON_FILE}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup MiraWorld SQLite on production server")
    parser.add_argument(
        "--install-cron",
        action="store_true",
        help="Upload backup script and install /etc/cron.d/miraworld-db-backup (03:00 UTC daily)",
    )
    args = parser.parse_args()

    print(f"连接 {d.USER}@{d.HOST} ...", flush=True)
    client = d.connect()
    try:
        if args.install_cron:
            install_cron(client)
        else:
            upload_script(client)
        run_backup(client)
        print("DB backup done.", flush=True)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
