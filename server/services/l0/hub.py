"""L0 Hub market: inventory, pricing, institution purchases for production."""
from __future__ import annotations

import sqlite3

from config_loader import l0_facilities, l0_hub_pricing, l0_resources
from services.economy.config import add_economy_ledger


def _resource_defs() -> dict[str, dict]:
    return {r["id"]: r for r in l0_resources().get("resources", [])}


def ensure_hub_city(conn: sqlite3.Connection, city: str) -> None:
    defs = _resource_defs()
    fac = l0_facilities()
    ratio = float(fac.get("initial_inventory_ratio", 0.5))
    for resource in defs.values():
        rid = resource["id"]
        row = conn.execute(
            """
            SELECT qty FROM hub_inventory WHERE city = ? AND resource_id = ?
            """,
            (city, rid),
        ).fetchone()
        if row is not None:
            continue
        daily = 0
        for f in fac.get("facilities", []):
            if f.get("resource_id") == rid:
                daily = int(f.get("daily_output", 0))
                break
        initial = max(int(daily * ratio), 100)
        conn.execute(
            """
            INSERT INTO hub_inventory (city, resource_id, qty, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (city, rid, initial),
        )


def _guide_price(resource_id: str) -> int:
    defs = _resource_defs()
    row = defs.get(resource_id, {})
    return max(int(row.get("guide_price", 10)), 1)


def compute_price(guide: int, qty: int, daily_output: int) -> int:
    cfg = l0_hub_pricing()
    floor_r = float(cfg.get("price_floor_ratio", 0.7))
    ceil_r = float(cfg.get("price_ceiling_ratio", 1.5))
    if daily_output <= 0:
        return guide
    ratio = qty / daily_output
    if ratio < 1.0:
        markup = float(cfg.get("scarcity_markup_per_ratio", 0.2)) * (1.0 - ratio)
        price = guide * (1.0 + markup)
    else:
        discount = float(cfg.get("surplus_discount_per_ratio", 0.1)) * min(ratio - 1.0, 1.0)
        price = guide * (1.0 - discount)
    return max(int(guide * floor_r), min(int(guide * ceil_r), int(price)))


def run_l0_tick(conn: sqlite3.Connection, city: str) -> dict:
    ensure_hub_city(conn, city)
    fac = l0_facilities()
    daily_map = {
        f["resource_id"]: int(f.get("daily_output", 0))
        for f in fac.get("facilities", [])
    }
    restocked = 0
    priced = 0
    for resource_id in _resource_defs():
        daily = daily_map.get(resource_id, 0)
        if daily > 0:
            conn.execute(
                """
                UPDATE hub_inventory
                SET qty = qty + ?, updated_at = datetime('now')
                WHERE city = ? AND resource_id = ?
                """,
                (daily, city, resource_id),
            )
            restocked += daily
        row = conn.execute(
            """
            SELECT qty FROM hub_inventory WHERE city = ? AND resource_id = ?
            """,
            (city, resource_id),
        ).fetchone()
        qty = int(row["qty"]) if row else 0
        guide = _guide_price(resource_id)
        price = compute_price(guide, qty, daily)
        conn.execute(
            """
            INSERT INTO hub_prices (city, resource_id, price_credits, guide_price, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(city, resource_id) DO UPDATE SET
                price_credits = excluded.price_credits,
                guide_price = excluded.guide_price,
                updated_at = excluded.updated_at
            """,
            (city, resource_id, price, guide),
        )
        priced += 1
    return {"restocked_units": restocked, "resources_priced": priced}


def get_hub_prices(conn: sqlite3.Connection, city: str) -> dict[str, int]:
    ensure_hub_city(conn, city)
    rows = conn.execute(
        """
        SELECT resource_id, price_credits FROM hub_prices WHERE city = ?
        """,
        (city,),
    ).fetchall()
    return {row["resource_id"]: int(row["price_credits"]) for row in rows}


def get_hub_status(conn: sqlite3.Connection, city: str) -> dict:
    ensure_hub_city(conn, city)
    prices = get_hub_prices(conn, city)
    inventory = conn.execute(
        """
        SELECT resource_id, qty FROM hub_inventory WHERE city = ?
        ORDER BY resource_id
        """,
        (city,),
    ).fetchall()
    defs = _resource_defs()
    resources = []
    for row in inventory:
        rid = row["resource_id"]
        meta = defs.get(rid, {})
        resources.append(
            {
                "resource_id": rid,
                "display": meta.get("display", rid),
                "qty": int(row["qty"]),
                "price_credits": prices.get(rid, _guide_price(rid)),
                "guide_price": _guide_price(rid),
            }
        )
    return {"city": city, "resources": resources}


def purchase_hub_resources(
    conn: sqlite3.Connection,
    *,
    city: str,
    institution_id: str,
    inputs: list[dict],
) -> tuple[bool, int, str]:
    """Debit institution wallet, hub inventory; return (ok, total_cost, reason)."""
    prices = get_hub_prices(conn, city)
    total = 0
    for inp in inputs:
        rid = inp["resource"]
        qty = int(inp["qty"])
        price = prices.get(rid, _guide_price(rid))
        total += price * qty

    inst = conn.execute(
        "SELECT wallet_credits FROM institutions WHERE id = ?",
        (institution_id,),
    ).fetchone()
    if inst is None:
        return False, 0, "institution_missing"
    if int(inst["wallet_credits"]) < total:
        return False, total, "insufficient_wallet"

    for inp in inputs:
        rid = inp["resource"]
        qty = int(inp["qty"])
        row = conn.execute(
            """
            SELECT qty FROM hub_inventory WHERE city = ? AND resource_id = ?
            """,
            (city, rid),
        ).fetchone()
        available = int(row["qty"]) if row else 0
        if available < qty:
            return False, total, f"hub_shortage:{rid}"

    conn.execute(
        "UPDATE institutions SET wallet_credits = wallet_credits - ? WHERE id = ?",
        (total, institution_id),
    )
    add_economy_ledger(
        conn,
        account_kind="institution",
        account_id=institution_id,
        amount=-total,
        entry_type="hub_purchase",
        ref_type="hub",
        ref_id=city,
    )
    for inp in inputs:
        rid = inp["resource"]
        qty = int(inp["qty"])
        unit = prices.get(rid, _guide_price(rid))
        conn.execute(
            """
            UPDATE hub_inventory
            SET qty = qty - ?, updated_at = datetime('now')
            WHERE city = ? AND resource_id = ?
            """,
            (qty, city, rid),
        )
        add_economy_ledger(
            conn,
            account_kind="hub",
            account_id=f"{city}:{rid}",
            amount=unit * qty,
            entry_type="hub_sale",
            ref_type="institution",
            ref_id=institution_id,
        )
    return True, total, "ok"
