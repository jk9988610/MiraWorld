#!/usr/bin/env python3
"""Purge smoke-test accounts on production server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy as d

AUTH_ROOT = "/opt/miraworld-auth"
DB_PATH = "/var/lib/miraworld/miraworld.db"


def purge(client, *, dry_run: bool = False) -> None:
    flag = "--dry-run" if dry_run else ""
    cmd = f"""
set -e
sudo -u www-data env MIRAWORLD_DB={DB_PATH} {AUTH_ROOT}/venv/bin/python3 {AUTH_ROOT}/scripts/purge_test_accounts.py {flag}
"""
    out = d.run(client, cmd)
    print(out, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge smoke-test player accounts on production")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"连接 {d.USER}@{d.HOST} ...", flush=True)
    client = d.connect()
    try:
        purge(client, dry_run=args.dry_run)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
