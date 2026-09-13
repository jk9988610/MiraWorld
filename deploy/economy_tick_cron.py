#!/usr/bin/env python3
"""Install economy daily tick cron on production server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy as d

SCRIPT_LOCAL = Path(__file__).resolve().parent / "scripts" / "economy-tick.sh"
REMOTE_SCRIPT = "/var/lib/miraworld/scripts/economy-tick.sh"
CRON_FILE = "/etc/cron.d/miraworld-economy-tick"
CRON_LINE = "5 0 * * * root /var/lib/miraworld/scripts/economy-tick.sh >> /var/log/miraworld-economy-tick.log 2>&1\n"


def upload_script(client) -> None:
    if not SCRIPT_LOCAL.is_file():
        raise RuntimeError(f"Missing {SCRIPT_LOCAL}")
    sftp = client.open_sftp()
    try:
        remote_tmp = "/tmp/miraworld-economy-tick.sh"
        sftp.put(str(SCRIPT_LOCAL), remote_tmp)
    finally:
        sftp.close()
    d.run(
        client,
        f"""
set -e
sudo mkdir -p /var/lib/miraworld/scripts
sudo install -m 755 {remote_tmp} {REMOTE_SCRIPT}
sudo rm -f {remote_tmp}
""",
    )


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


def run_tick(client) -> None:
    upload_script(client)
    d.run(client, f"sudo bash {REMOTE_SCRIPT}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MiraWorld economy tick cron on production")
    parser.add_argument(
        "--install-cron",
        action="store_true",
        help="Install /etc/cron.d/miraworld-economy-tick (00:05 UTC daily)",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run economy tick script once on server",
    )
    args = parser.parse_args()

    print(f"连接 {d.USER}@{d.HOST} ...", flush=True)
    client = d.connect()
    try:
        if args.install_cron:
            install_cron(client)
        if args.run_once or not args.install_cron:
            run_tick(client)
        print("Economy tick cron done.", flush=True)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
