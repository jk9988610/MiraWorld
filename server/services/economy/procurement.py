"""NPC institution procurement from the finished-goods market."""
from __future__ import annotations

import random
import sqlite3

from config_loader import items
from services.economy.market_orders import place_market_order


def _item_needs_institution_deploy(item_id: str, kind: str) -> bool:
    for item in items().get("items", []):
        if item["id"] != item_id:
            continue
        effect = (item.get("on_acquire") or {}).get("institution")
        if not effect or effect.get("type") != "DEPLOY_INST":
            return False
        kinds = effect.get("required_kinds") or []
        return not kinds or kind in kinds
    return False


def _deploy_qty(conn: sqlite3.Connection, institution_id: str, item_id: str) -> int:
    row = conn.execute(
        """
        SELECT qty_active FROM institution_deployments
        WHERE institution_id = ? AND item_id = ?
        """,
        (institution_id, item_id),
    ).fetchone()
    return int(row["qty_active"]) if row else 0


def _institution_needed_items(kind: str) -> list[str]:
    result: list[str] = []
    for item in items().get("items", []):
        effect = (item.get("on_acquire") or {}).get("institution")
        if not effect or effect.get("type") != "DEPLOY_INST":
            continue
        kinds = effect.get("required_kinds") or []
        if kinds and kind not in kinds:
            continue
        result.append(item["id"])
    return result


def run_institution_procurement(
    conn: sqlite3.Connection,
    city: str,
    rng: random.Random,
) -> dict:
    from services.catalog import active_offers

    orders: list[dict] = []
    institutions = conn.execute(
        """
        SELECT id, kind, wallet_credits FROM institutions
        WHERE city = ? AND owner_kind = 'system'
        ORDER BY id
        """,
        (city,),
    ).fetchall()
    offers = active_offers(city, conn=conn)
    for inst in institutions:
        wallet = int(inst["wallet_credits"])
        if wallet <= 0:
            continue
        kind = inst["kind"]
        for item_id in _institution_needed_items(kind):
            if _deploy_qty(conn, inst["id"], item_id) >= 1:
                continue
            candidates = [
                o
                for o in offers
                if o.get("gives", {}).get("item_id") == item_id
                and int(o.get("price_credits", 0)) <= wallet
                and o.get("active", True)
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda o: int(o.get("price_credits", 0)))
            offer = candidates[0]
            placed = place_market_order(
                conn,
                buyer_kind="institution",
                buyer_group_id=None,
                buyer_institution_id=inst["id"],
                offer=offer,
                rng=rng,
            )
            if placed is None:
                continue
            orders.append(placed)
            wallet -= int(placed["price"])
    return {"orders": len(orders), "details": orders[:20]}
