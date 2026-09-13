from __future__ import annotations

import json
import random
import sqlite3
import uuid

from config_loader import items, pop_spotlight_names
from db import utc_now
from services.catalog import get_offer
from services.economy.config import add_economy_ledger


SPOTLIGHT_MAX = 10


def _pick_surname(rng: random.Random) -> str:
    cfg = pop_spotlight_names()
    weights = cfg.get("surname_weights", {"single": 0.7, "compound": 0.3})
    if rng.random() < float(weights.get("compound", 0.3)):
        pool = cfg.get("compound_surnames", ["欧阳"])
    else:
        pool = cfg.get("single_surnames", ["王"])
    return rng.choice(pool) if pool else "王"


def _institution_for_seller(conn: sqlite3.Connection, seller_kind: str, seller_id: str, offer_id: str) -> str | None:
    if seller_kind == "npc":
        row = conn.execute(
            """
            SELECT id FROM institutions
            WHERE owner_kind = 'system' AND owner_id = ?
            LIMIT 1
            """,
            (seller_id,),
        ).fetchone()
        if row:
            return row["id"]
    row = conn.execute(
        "SELECT id FROM institutions WHERE offer_id = ? LIMIT 1",
        (offer_id,),
    ).fetchone()
    return row["id"] if row else None


def _trim_spotlight(conn: sqlite3.Connection, institution_id: str) -> None:
    rows = conn.execute(
        """
        SELECT id FROM spotlight_entries
        WHERE institution_id = ?
        ORDER BY id DESC
        """,
        (institution_id,),
    ).fetchall()
    if len(rows) <= SPOTLIGHT_MAX:
        return
    for row in rows[SPOTLIGHT_MAX:]:
        conn.execute("DELETE FROM spotlight_entries WHERE id = ?", (row["id"],))


def add_spotlight_for_order(
    conn: sqlite3.Connection,
    *,
    institution_id: str,
    pop_group_id: str,
    job_display: str,
    order_id: str,
    rng: random.Random | None = None,
) -> None:
    if not job_display:
        return
    group = conn.execute(
        """
        SELECT job_type, job_display, primary_institution_id
        FROM pop_groups WHERE id = ?
        """,
        (pop_group_id,),
    ).fetchone()
    if group is None:
        return
    slot_ok = conn.execute(
        """
        SELECT 1 FROM institution_slots
        WHERE institution_id = ? AND job_display = ?
        LIMIT 1
        """,
        (institution_id, job_display),
    ).fetchone()
    if slot_ok is None:
        return
    rng = rng or random.Random()
    surname = _pick_surname(rng)
    display_name = f"{surname}{job_display}"
    conn.execute(
        """
        INSERT INTO spotlight_entries (
            institution_id, display_name, job_display, pop_group_id, order_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (institution_id, display_name, job_display, pop_group_id, order_id, utc_now()),
    )
    _trim_spotlight(conn, institution_id)


def list_spotlight(conn: sqlite3.Connection, institution_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT display_name, job_display, pop_group_id, order_id, created_at
        FROM spotlight_entries
        WHERE institution_id = ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (institution_id, SPOTLIGHT_MAX),
    ).fetchall()
    return [dict(row) for row in rows]
