from __future__ import annotations

import json
import sqlite3
import uuid

from config_loader import items, l1_recipes
from db import db, utc_now
from fastapi import HTTPException
from services.capital.institution import ensure_player_shop_institution, institution_id_for_player
from services.economy.production import get_institution_inventory
from services.l0.hub import get_hub_status


TECH_SELLABLE_TAGS = {"device", "medical", "tech", "software", "deploy"}
DEFAULT_LINES = [{"recipe_id": "recipe_smart_terminal_v1", "enabled": True}]


def _player_institution(conn: sqlite3.Connection, player_id: int) -> sqlite3.Row | None:
    inst_id = institution_id_for_player(player_id)
    return conn.execute(
        """
        SELECT id, city, kind, display_name, wallet_credits, open,
               production_lines_json, company_id, owner_kind, owner_id
        FROM institutions WHERE id = ?
        """,
        (inst_id,),
    ).fetchone()


def _require_shop_and_company(conn: sqlite3.Connection, player_id: int) -> tuple[sqlite3.Row, sqlite3.Row]:
    shop = conn.execute(
        "SELECT display_name, city, open, company_id FROM shops WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if shop is None:
        raise HTTPException(status_code=400, detail="还没有店，先申请开店")
    if not shop["company_id"]:
        raise HTTPException(status_code=400, detail="请先登记公司")
    company = conn.execute(
        "SELECT id, wallet_credits FROM companies WHERE owner_player_id = ?",
        (player_id,),
    ).fetchone()
    if company is None:
        raise HTTPException(status_code=400, detail="请先登记公司")
    return shop, company


def _item_display(item_id: str) -> str:
    for item in items().get("items", []):
        if item["id"] == item_id:
            return item.get("display", item_id)
    return item_id


def _validate_tech_item(item_id: str) -> dict:
    for item in items().get("items", []):
        if item["id"] == item_id:
            tags = set(item.get("tags", []))
            if tags & TECH_SELLABLE_TAGS:
                return item
            raise HTTPException(status_code=400, detail="只能挂高新成品")
    raise HTTPException(status_code=404, detail="找不到这个物品")


def _available_recipes(kind: str) -> list[dict]:
    result: list[dict] = []
    for recipe in l1_recipes().get("recipes", []):
        allowed = recipe.get("allowed_kinds", [])
        if allowed and kind not in allowed:
            continue
        result.append(
            {
                "id": recipe["id"],
                "display": recipe.get("display", recipe["id"]),
                "inputs": recipe.get("inputs", []),
                "outputs": recipe.get("outputs", []),
                "daily_batches": recipe.get("daily_batches", 1),
            }
        )
    return result


def _parse_lines(raw: str | None) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def get_production_status(player_id: int) -> dict:
    with db() as conn:
        shop = conn.execute(
            "SELECT display_name, city, open, company_id FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        company = conn.execute(
            """
            SELECT id, display_name, wallet_credits FROM companies
            WHERE owner_player_id = ?
            """,
            (player_id,),
        ).fetchone()
        inst = _player_institution(conn, player_id)
        if inst is None and shop:
            ensure_player_shop_institution(
                conn,
                player_id=player_id,
                display_name=shop["display_name"],
                city=shop["city"],
                company_id=shop["company_id"],
            )
            inst = _player_institution(conn, player_id)

        hub = get_hub_status(conn, shop["city"] if shop else "潮灯市") if shop else None
        inventory: dict[str, int] = {}
        lines: list[dict] = []
        offers: list[dict] = []
        if inst:
            inventory = get_institution_inventory(conn, inst["id"])
            lines = _parse_lines(inst["production_lines_json"])
            offer_rows = conn.execute(
                """
                SELECT id, item_id, qty, price_credits, display, active, created_at
                FROM institution_offers
                WHERE player_id = ?
                ORDER BY created_at DESC
                """,
                (player_id,),
            ).fetchall()
            offers = [
                {
                    **dict(row),
                    "active": bool(row["active"]),
                    "item_display": _item_display(row["item_id"]),
                    "stock": inventory.get(row["item_id"], 0),
                }
                for row in offer_rows
            ]

        kind = inst["kind"] if inst else "player_shop"
        recipes = _available_recipes(kind) if inst else []

    return {
        "has_shop": shop is not None,
        "has_company": company is not None,
        "company_wallet": int(company["wallet_credits"]) if company else 0,
        "shop_open": bool(shop["open"]) if shop else False,
        "institution": (
            {
                "id": inst["id"],
                "display_name": inst["display_name"],
                "kind": inst["kind"],
                "wallet_credits": int(inst["wallet_credits"]),
                "production_ready": inst["kind"] == "device_plant",
            }
            if inst
            else None
        ),
        "hub": hub,
        "inventory": [
            {"item_id": k, "display": _item_display(k), "qty": v}
            for k, v in sorted(inventory.items())
        ],
        "production_lines": lines,
        "available_recipes": recipes,
        "offers": offers,
    }


def setup_device_plant(player_id: int) -> dict:
    with db() as conn:
        shop, _company = _require_shop_and_company(conn, player_id)
        inst_id = ensure_player_shop_institution(
            conn,
            player_id=player_id,
            display_name=shop["display_name"],
            city=shop["city"],
            company_id=shop["company_id"],
        )
        lines_json = json.dumps(DEFAULT_LINES, ensure_ascii=False)
        conn.execute(
            """
            UPDATE institutions
            SET kind = 'device_plant', production_lines_json = ?
            WHERE id = ?
            """,
            (lines_json, inst_id),
        )
    return get_production_status(player_id)


def update_production_lines(player_id: int, lines: list[dict]) -> dict:
    with db() as conn:
        inst = _player_institution(conn, player_id)
        if inst is None or inst["kind"] != "device_plant":
            raise HTTPException(status_code=400, detail="请先开通设备厂生产")
        allowed_ids = {r["id"] for r in _available_recipes(inst["kind"])}
        cleaned: list[dict] = []
        for line in lines:
            recipe_id = line.get("recipe_id", "")
            if recipe_id not in allowed_ids:
                raise HTTPException(status_code=400, detail=f"不可用配方：{recipe_id}")
            cleaned.append(
                {
                    "recipe_id": recipe_id,
                    "enabled": bool(line.get("enabled", True)),
                }
            )
        conn.execute(
            "UPDATE institutions SET production_lines_json = ? WHERE id = ?",
            (json.dumps(cleaned, ensure_ascii=False), inst["id"]),
        )
    return get_production_status(player_id)


def transfer_to_institution(player_id: int, source: str, amount: int) -> dict:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="金额须大于 0")
    if source not in {"company", "player"}:
        raise HTTPException(status_code=400, detail="source 须为 company 或 player")

    now = utc_now()
    with db() as conn:
        shop, company = _require_shop_and_company(conn, player_id)
        inst = _player_institution(conn, player_id)
        if inst is None:
            inst_id = ensure_player_shop_institution(
                conn,
                player_id=player_id,
                display_name=shop["display_name"],
                city=shop["city"],
                company_id=shop["company_id"],
            )
        else:
            inst_id = inst["id"]

        if source == "company":
            if int(company["wallet_credits"]) < amount:
                raise HTTPException(status_code=400, detail="公司账上点数不足")
            conn.execute(
                "UPDATE companies SET wallet_credits = wallet_credits - ? WHERE id = ?",
                (amount, company["id"]),
            )
        else:
            wallet = conn.execute(
                "SELECT wallet_credits FROM users WHERE id = ?",
                (player_id,),
            ).fetchone()
            if wallet is None or int(wallet["wallet_credits"]) < amount:
                raise HTTPException(status_code=400, detail="个人钱包点数不足")
            conn.execute(
                "UPDATE users SET wallet_credits = wallet_credits - ? WHERE id = ?",
                (amount, player_id),
            )
            conn.execute(
                """
                INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
                VALUES (?, ?, 'institution_deposit', 'institution', ?, ?)
                """,
                (player_id, -amount, inst_id, now),
            )

        conn.execute(
            "UPDATE institutions SET wallet_credits = wallet_credits + ? WHERE id = ?",
            (amount, inst_id),
        )

    status = get_production_status(player_id)
    return {
        "ok": True,
        "amount": amount,
        "source": source,
        "institution_wallet": status["institution"]["wallet_credits"] if status["institution"] else 0,
        "company_wallet": status["company_wallet"],
    }


def create_institution_offer(
    player_id: int,
    item_id: str,
    display: str,
    price_credits: int,
    qty: int = 1,
) -> dict:
    _validate_tech_item(item_id)
    if price_credits <= 0:
        raise HTTPException(status_code=400, detail="价格须大于 0")
    if qty <= 0:
        raise HTTPException(status_code=400, detail="数量须大于 0")

    with db() as conn:
        shop, _ = _require_shop_and_company(conn, player_id)
        if not shop["open"]:
            raise HTTPException(status_code=400, detail="店未营业，请先开始营业")
        inst = _player_institution(conn, player_id)
        if inst is None or inst["kind"] != "device_plant":
            raise HTTPException(status_code=400, detail="请先开通设备厂生产")
        stock = get_institution_inventory(conn, inst["id"]).get(item_id, 0)
        if stock < qty:
            raise HTTPException(status_code=400, detail="机构成品库存不足")

        offer_id = f"ioffer_{uuid.uuid4().hex[:12]}"
        now = utc_now()
        conn.execute(
            """
            INSERT INTO institution_offers (
                id, institution_id, player_id, item_id, qty,
                price_credits, display, active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                offer_id,
                inst["id"],
                player_id,
                item_id,
                qty,
                price_credits,
                display.strip() or _item_display(item_id),
                now,
            ),
        )
        row = conn.execute(
            """
            SELECT id, item_id, qty, price_credits, display, active, created_at
            FROM institution_offers WHERE id = ?
            """,
            (offer_id,),
        ).fetchone()
    assert row is not None
    return {
        **dict(row),
        "active": bool(row["active"]),
        "item_display": _item_display(row["item_id"]),
        "stock": stock,
    }


def set_institution_offer_active(player_id: int, offer_id: str, active: bool) -> dict:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, institution_id, item_id, qty, price_credits, display, active, created_at
            FROM institution_offers
            WHERE id = ? AND player_id = ?
            """,
            (offer_id, player_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="找不到这个挂单")
        conn.execute(
            "UPDATE institution_offers SET active = ? WHERE id = ?",
            (1 if active else 0, offer_id),
        )
        stock = get_institution_inventory(conn, row["institution_id"]).get(row["item_id"], 0)
        row = conn.execute(
            """
            SELECT id, item_id, qty, price_credits, display, active, created_at
            FROM institution_offers WHERE id = ?
            """,
            (offer_id,),
        ).fetchone()
    assert row is not None
    return {
        **dict(row),
        "active": bool(row["active"]),
        "item_display": _item_display(row["item_id"]),
        "stock": stock,
    }


def active_institution_offers_catalog(conn: sqlite3.Connection, city: str | None = None) -> list[dict]:
    rows = conn.execute(
        """
        SELECT o.id, o.institution_id, o.player_id, o.item_id, o.qty,
               o.price_credits, o.display, o.active, o.created_at,
               s.display_name, s.city, s.open, u.handle
        FROM institution_offers o
        JOIN shops s ON s.player_id = o.player_id
        JOIN users u ON u.id = o.player_id
        WHERE o.active = 1 AND s.open = 1
        ORDER BY o.created_at DESC
        """
    ).fetchall()
    result: list[dict] = []
    for row in rows:
        if city and row["city"] != city:
            continue
        stock = get_institution_inventory(conn, row["institution_id"]).get(row["item_id"], 0)
        if stock < int(row["qty"]):
            continue
        result.append(
            {
                "id": row["id"],
                "institution_id": row["institution_id"],
                "seller": {
                    "kind": "player",
                    "id": str(row["player_id"]),
                    "display": row["display_name"],
                },
                "place": {"city": row["city"]},
                "gives": {"item_id": row["item_id"], "qty": int(row["qty"])},
                "price_credits": int(row["price_credits"]),
                "display": row["display"],
                "active": True,
            }
        )
    return result
