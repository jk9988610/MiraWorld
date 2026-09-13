#!/usr/bin/env python3
"""Remove smoke-test player accounts from production DB."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db import db  # noqa: E402

# Handles created by deploy/smoke_demo.py (single-char prefix + short suffix).
SMOKE_HANDLE_RE = re.compile(
    r"^(?:烟|店|客|班|委|接)[0-9a-zA-Z]{0,8}$"
)
SMOKE_SHOP_RE = re.compile(r"^(?:烟\d+号食堂|当班\d+号)$")


def is_test_handle(handle: str) -> bool:
    h = (handle or "").strip()
    if not h:
        return False
    return bool(SMOKE_HANDLE_RE.match(h))


def purge_test_accounts(*, dry_run: bool = False) -> dict:
    deleted: list[str] = []
    with db() as conn:
        rows = conn.execute(
            "SELECT id, handle FROM users ORDER BY id"
        ).fetchall()
        for row in rows:
            handle = row["handle"]
            if not is_test_handle(handle):
                continue
            if dry_run:
                deleted.append(handle)
                continue
            conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
            deleted.append(handle)
    return {"deleted": deleted, "count": len(deleted), "dry_run": dry_run}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Purge MiraWorld smoke-test accounts")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = purge_test_accounts(dry_run=args.dry_run)
    mode = "would delete" if args.dry_run else "deleted"
    print(f"{mode} {result['count']} account(s)", flush=True)
    for handle in result["deleted"][:50]:
        print(f"  - {handle}", flush=True)
    if result["count"] > 50:
        print(f"  ... and {result['count'] - 50} more", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
