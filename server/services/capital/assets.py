from __future__ import annotations

import sqlite3

from config_loader import capitalist_economy, items


def _stack_unit_value(tags: set[str], cfg: dict) -> int:
    table = cfg.get("stack_unit_value", {})
    for tag in ("food", "consumable", "material", "tool"):
        if tag in tags:
            return int(table.get(tag, table.get("default", 3)))
    return int(table.get("default", 3))


def _item_tags() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for item in items().get("items", []):
        out[item["id"]] = set(item.get("tags", []))
    return out


def player_total_assets(conn: sqlite3.Connection, player_id: int) -> dict:
    cfg = capitalist_economy()
    wallet_row = conn.execute(
        "SELECT wallet_credits FROM users WHERE id = ?",
        (player_id,),
    ).fetchone()
    wallet = int(wallet_row["wallet_credits"]) if wallet_row else 0

    shop_row = conn.execute(
        "SELECT player_id FROM shops WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    shop_value = int(cfg.get("shop_asset_value", 100)) if shop_row else 0

    tag_map = _item_tags()
    stack_rows = conn.execute(
        "SELECT item_id, qty FROM stacks WHERE player_id = ? AND qty > 0",
        (player_id,),
    ).fetchall()
    inventory_value = 0
    for row in stack_rows:
        tags = tag_map.get(row["item_id"], set())
        unit = _stack_unit_value(tags, cfg)
        inventory_value += unit * int(row["qty"])

    total = wallet + shop_value + inventory_value
    return {
        "wallet_credits": wallet,
        "shop_value": shop_value,
        "inventory_value": inventory_value,
        "total": total,
    }
