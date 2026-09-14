"""Institution-backed offers on the finished-goods market."""
from __future__ import annotations

import sqlite3

from config_loader import economy_market_offers


def institution_market_offers(conn: sqlite3.Connection, city: str | None = None) -> list[dict]:
    cfg = economy_market_offers().get("offers", [])
    result: list[dict] = []
    for offer in cfg:
        if not offer.get("active", True):
            continue
        offer_city = offer.get("place", {}).get("city")
        if city and offer_city != city:
            continue
        inst_id = offer.get("institution_id")
        if not inst_id:
            continue
        gives = offer.get("gives", {})
        item_id = gives.get("item_id", "")
        need_qty = int(gives.get("qty", 1))
        row = conn.execute(
            """
            SELECT qty FROM institution_inventory
            WHERE institution_id = ? AND item_id = ? AND qty >= ?
            """,
            (inst_id, item_id, need_qty),
        ).fetchone()
        if row is None:
            continue
        result.append(dict(offer))
    return result
