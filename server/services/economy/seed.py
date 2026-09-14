"""Load static JSON config and seed economy tables."""
from __future__ import annotations

import json
import sqlite3
import uuid

from config_loader import economy_institutions, economy_pop_groups
from db import utc_now
from services.economy.config import add_economy_ledger, default_pref_json


def _institution_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM institutions").fetchone()
    return int(row["c"]) if row else 0


def seed_economy(conn: sqlite3.Connection) -> None:
    if _institution_count(conn) > 0:
        return

    now = utc_now()
    inst_cfg = economy_institutions()
    pop_cfg = economy_pop_groups()
    city = "潮灯市"

    for inst in inst_cfg.get("institutions", []):
        seed_cap = int(inst.get("seed_capital", 0))
        lines_json = json.dumps(inst.get("production_lines") or [], ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO institutions (
                id, city, kind, display_name, owner_kind, owner_id, offer_id,
                wallet_credits, open, production_lines_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                inst["id"],
                inst.get("city", city),
                inst["kind"],
                inst["display_name"],
                inst["owner_kind"],
                inst["owner_id"],
                inst.get("offer_id"),
                seed_cap,
                lines_json,
                now,
            ),
        )
        if seed_cap:
            add_economy_ledger(
                conn,
                account_kind="institution",
                account_id=inst["id"],
                amount=seed_cap,
                entry_type="seed",
                ref_type="institution",
                ref_id=inst["id"],
            )
        for slot in inst.get("slots", []):
            slot_id = f"slot_{uuid.uuid4().hex[:10]}"
            conn.execute(
                """
                INSERT INTO institution_slots (
                    id, institution_id, job_type, job_display, headcount,
                    wage_per_capita, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slot_id,
                    inst["id"],
                    slot["job_type"],
                    slot["job_display"],
                    int(slot.get("headcount", 1)),
                    int(slot.get("wage_per_capita", 12)),
                    now,
                ),
            )

    headcount = int(pop_cfg.get("default_headcount", 1000))
    pref_json = default_pref_json()
    for group in pop_cfg.get("groups", []):
        conn.execute(
            """
            INSERT INTO pop_groups (
                id, city, headcount, wallet_credits, primary_institution_id,
                job_type, job_display, pref_json, created_at, updated_at
            ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                group["id"],
                city,
                headcount,
                group.get("primary_institution_id"),
                group.get("job_type"),
                group.get("job_display"),
                pref_json,
                now,
                now,
            ),
        )

    conn.execute(
        """
        INSERT INTO city_welfare_fund (city, balance, last_grant_date, updated_at)
        VALUES (?, 0, NULL, ?)
        """,
        (city, now),
    )
    add_economy_ledger(
        conn,
        account_kind="welfare_fund",
        account_id=city,
        amount=0,
        entry_type="init",
        ref_type="city",
        ref_id=city,
    )
