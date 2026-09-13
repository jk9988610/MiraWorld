from __future__ import annotations

from config_loader import welcome, world
from db import db, utc_now


def _find_spot(city_name: str, spot_id: str) -> dict | None:
    for city in world().get("cities", []):
        if city.get("city") == city_name:
            for spot in city.get("explore_spots", []):
                if spot.get("id") == spot_id:
                    return spot
    return None


def visit_message(city: str, spot_id: str | None, first_visit: bool) -> str:
    w = welcome()
    if not spot_id:
        if first_visit:
            return w.get("city_first_visit") or w.get("onboarding_message", "")
        return w.get("city_revisit", f"你又回到{city}。")

    spot = _find_spot(city, spot_id)
    name = spot.get("name", spot_id) if spot else spot_id
    if first_visit:
        if spot and spot.get("first_visit"):
            return spot["first_visit"]
        return f"你第一次到「{name}」。"
    if spot and spot.get("revisit"):
        return spot["revisit"]
    return f"你又来过「{name}」。"


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
    first_visit = existing is None
    return {
        "city": city,
        "spot_id": spot_id,
        "first_visit": first_visit,
        "visited_at": now,
        "message": visit_message(city, spot_id, first_visit),
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
