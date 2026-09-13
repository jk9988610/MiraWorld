from __future__ import annotations

from config_loader import welcome, world
from db import db, utc_now


def get_world_payload() -> dict:
    data = world()
    w = welcome()
    return {
        "brand": w.get("brand", {}),
        "onboarding_message": w.get("onboarding_message", ""),
        "cities": data.get("cities", []),
        "npcs": data.get("npcs", []),
        "system_shop": data.get("system_shop"),
    }


def record_visit(player_id: int, city: str, spot_id: str | None) -> dict:
    spot = spot_id or ""
    now = utc_now()
    with db() as conn:
        existing = conn.execute(
            """
            SELECT first_at FROM visits
            WHERE player_id = ? AND city = ? AND spot_id = ?
            """,
            (player_id, city, spot),
        ).fetchone()
        first = existing["first_at"] if existing else now
        conn.execute(
            """
            INSERT INTO visits (player_id, city, spot_id, first_at, last_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(player_id, city, spot_id) DO UPDATE SET last_at = excluded.last_at
            """,
            (player_id, city, spot, first, now),
        )
    return {
        "city": city,
        "spot_id": spot_id,
        "first_visit": existing is None,
        "visited_at": now,
    }


def list_visits(player_id: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT city, spot_id, first_at, last_at
            FROM visits WHERE player_id = ?
            ORDER BY last_at DESC
            """,
            (player_id,),
        ).fetchall()
    return [dict(row) for row in rows]
