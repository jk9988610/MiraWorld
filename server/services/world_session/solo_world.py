"""Seed and tick isolated solo world instances."""
from __future__ import annotations

import json
import sqlite3
import uuid

from config_loader import economy_institutions, economy_pop_groups
from db import db, utc_now
from fastapi import HTTPException
from services.economy.config import add_economy_ledger, default_pref_json
from services.economy.tick import run_daily_tick
from services.l0.hub import ensure_hub_city
from services.world_session.constants import DEFAULT_CITY, SHARED_WORLD_ID


def _scoped_id(world_id: str, base_id: str) -> str:
    return f"{world_id}::{base_id}"


def seed_solo_world(conn: sqlite3.Connection, world_id: str) -> None:
    existing = conn.execute(
        "SELECT id FROM institutions WHERE world_id = ? LIMIT 1",
        (world_id,),
    ).fetchone()
    if existing:
        ensure_hub_city(conn, DEFAULT_CITY, world_id)
        return

    now = utc_now()
    inst_cfg = economy_institutions()
    pop_cfg = economy_pop_groups()
    headcount = int(pop_cfg.get("default_headcount", 1000))
    pref_json = default_pref_json()

    id_map: dict[str, str] = {}

    for inst in inst_cfg.get("institutions", []):
        base_id = inst["id"]
        inst_id = _scoped_id(world_id, base_id)
        id_map[base_id] = inst_id
        seed_cap = int(inst.get("seed_capital", 0))
        lines_json = json.dumps(inst.get("production_lines") or [], ensure_ascii=False)
        conn.execute(
            """
            INSERT INTO institutions (
                id, world_id, city, kind, display_name, owner_kind, owner_id, offer_id,
                wallet_credits, open, production_lines_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                inst_id,
                world_id,
                inst.get("city", DEFAULT_CITY),
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
                    inst_id,
                    slot["job_type"],
                    slot["job_display"],
                    int(slot.get("headcount", 1)),
                    int(slot.get("wage_per_capita", 12)),
                    now,
                ),
            )

    for group in pop_cfg.get("groups", []):
        base_gid = group["id"]
        primary = group.get("primary_institution_id")
        primary_scoped = id_map.get(primary) if primary else None
        conn.execute(
            """
            INSERT INTO pop_groups (
                id, world_id, city, headcount, wallet_credits, primary_institution_id,
                job_type, job_display, pref_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                _scoped_id(world_id, base_gid),
                world_id,
                DEFAULT_CITY,
                headcount,
                primary_scoped,
                group.get("job_type"),
                group.get("job_display"),
                pref_json,
                now,
                now,
            ),
        )

    conn.execute(
        """
        INSERT INTO city_welfare_fund (world_id, city, balance, last_grant_date, updated_at)
        VALUES (?, ?, 0, NULL, ?)
        ON CONFLICT(world_id, city) DO NOTHING
        """,
        (world_id, DEFAULT_CITY, now),
    )
    ensure_hub_city(conn, DEFAULT_CITY, world_id)


def solo_world_stats(conn: sqlite3.Connection, world_id: str) -> dict:
    pop = conn.execute(
        "SELECT COUNT(*) AS c FROM pop_groups WHERE world_id = ?",
        (world_id,),
    ).fetchone()
    inst = conn.execute(
        "SELECT COUNT(*) AS c FROM institutions WHERE world_id = ?",
        (world_id,),
    ).fetchone()
    return {
        "pop_groups": int(pop["c"]) if pop else 0,
        "institutions": int(inst["c"]) if inst else 0,
    }


def get_solo_status(player_id: int) -> dict:
    with db() as conn:
        sess = conn.execute(
            """
            SELECT s.id, s.scope, s.world_id, s.world_day, s.speed, s.display_name, s.ironman
            FROM player_sessions ps
            JOIN world_saves s ON s.id = ps.active_save_id
            WHERE ps.player_id = ?
            """,
            (player_id,),
        ).fetchone()
        if sess is None or sess["scope"] != "solo":
            raise HTTPException(status_code=400, detail="当前不是单人模式")
        stats = solo_world_stats(conn, sess["world_id"])
    return {
        "world_id": sess["world_id"],
        "world_day": int(sess["world_day"]),
        "speed": sess["speed"],
        "display_name": sess["display_name"],
        "ironman": bool(sess["ironman"]),
        **stats,
    }


def advance_solo_tick(player_id: int) -> dict:
    with db() as conn:
        sess = conn.execute(
            """
            SELECT s.id, s.scope, s.world_id, s.world_day, s.speed
            FROM player_sessions ps
            JOIN world_saves s ON s.id = ps.active_save_id
            WHERE ps.player_id = ?
            """,
            (player_id,),
        ).fetchone()
        if sess is None or sess["scope"] != "solo":
            raise HTTPException(status_code=400, detail="当前不是单人模式")
        if sess["speed"] == "pause":
            raise HTTPException(status_code=400, detail="暂停中，无法推进 tick")

        world_day = int(sess["world_day"])
        tick_date = f"solo-vday-{world_day}"
        result = run_daily_tick(
            DEFAULT_CITY,
            world_id=sess["world_id"],
            force=True,
            tick_date=tick_date,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("reason", "tick failed"))

        new_day = world_day + 1
        now = utc_now()
        conn.execute(
            "UPDATE world_saves SET world_day = ?, last_played_at = ? WHERE id = ?",
            (new_day, now, sess["id"]),
        )
        stats = solo_world_stats(conn, sess["world_id"])

    return {
        "ok": True,
        "world_day": new_day,
        "tick": result,
        **stats,
    }


def active_world_id(conn: sqlite3.Connection, player_id: int) -> str:
    row = conn.execute(
        """
        SELECT s.world_id, s.scope FROM player_sessions ps
        JOIN world_saves s ON s.id = ps.active_save_id
        WHERE ps.player_id = ?
        """,
        (player_id,),
    ).fetchone()
    if row is None:
        return SHARED_WORLD_ID
    return row["world_id"] if row["scope"] == "solo" else SHARED_WORLD_ID
