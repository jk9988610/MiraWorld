from __future__ import annotations

import sqlite3

from config_loader import world
from db import db, utc_now
from fastapi import HTTPException

from services.catalog import item_display
from services.inventory import add_stack
from services.item_actions import can_consume, can_use, get_item


def _find_spot(city_name: str, spot_id: str) -> dict | None:
    for city in world().get("cities", []):
        if city.get("city") == city_name:
            for spot in city.get("explore_spots", []):
                if spot.get("id") == spot_id:
                    return spot
    return None


def _loot_claimed(conn: sqlite3.Connection, player_id: int, city: str, spot_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM spot_loot_claims
        WHERE player_id = ? AND city = ? AND spot_id = ?
        """,
        (player_id, city, spot_id),
    ).fetchone()
    return row is not None


def ground_item(player_id: int, city: str, spot_id: str | None) -> dict | None:
    if not spot_id:
        return None
    spot = _find_spot(city, spot_id)
    loot = spot.get("loot") if spot else None
    if not loot:
        return None
    item_id = loot.get("item_id")
    if not item_id:
        return None
    with db() as conn:
        if loot.get("once", True) and _loot_claimed(conn, player_id, city, spot_id):
            return None
    meta = get_item(item_id)
    return {
        "spot_id": spot_id,
        "item_id": item_id,
        "display": meta.get("display", item_id),
        "qty": int(loot.get("qty", 1)),
        "tags": meta.get("tags", []),
        "available": True,
    }


def claim_spot_loot(player_id: int, city: str, spot_id: str, action: str) -> dict:
    if action not in ("put", "consume", "use"):
        raise HTTPException(status_code=400, detail="无效操作")
    spot = _find_spot(city, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="找不到这个逛点")
    loot = spot.get("loot")
    if not loot:
        raise HTTPException(status_code=400, detail="这里没有可拾取的东西")
    item_id = loot.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="这里没有可拾取的东西")
    meta = get_item(item_id)
    tags = meta.get("tags", [])
    qty = int(loot.get("qty", 1))

    if action == "consume" and not can_consume(tags):
        raise HTTPException(status_code=400, detail="这个东西不能食用")
    if action == "use" and not can_use(tags):
        raise HTTPException(status_code=400, detail="这个东西不能使用")

    with db() as conn:
        if loot.get("once", True) and _loot_claimed(conn, player_id, city, spot_id):
            raise HTTPException(status_code=400, detail="这里已经没有什么可拿的了")

        if action == "put":
            add_stack(conn, player_id, item_id, qty)
            message = f"「{meta.get('display', item_id)}」已放入背包。"
        elif action == "consume":
            message = meta.get("consume_message") or f"你吃掉了{meta.get('display', item_id)}。"
        else:
            message = meta.get("use_message") or f"你使用了{meta.get('display', item_id)}。"

        conn.execute(
            """
            INSERT INTO spot_loot_claims (player_id, city, spot_id, item_id, action, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (player_id, city, spot_id, item_id, action, utc_now()),
        )

    return {"message": message, "action": action, "item_id": item_id}
