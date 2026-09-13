from __future__ import annotations

import sqlite3
import uuid

from fastapi import HTTPException

from config_loader import items
from db import db, utc_now
from schemas.shop import (
    MarketResponse,
    MarketShopPublic,
    PlayerOfferPublic,
    ShopMeResponse,
    ShopPublic,
)

SHOP_REGISTRATION_FEE = 100
SELLABLE_TAGS = {"food", "consumable"}


def _player_offer_row(row: sqlite3.Row) -> PlayerOfferPublic:
    return PlayerOfferPublic(
        id=row["id"],
        player_id=row["player_id"],
        item_id=row["item_id"],
        qty=row["qty"],
        price_credits=row["price_credits"],
        display=row["display"],
        active=bool(row["active"]),
        created_at=row["created_at"],
    )


def _shop_row(row: sqlite3.Row, handle: str) -> ShopPublic:
    return ShopPublic(
        player_id=row["player_id"],
        handle=handle,
        display_name=row["display_name"],
        city=row["city"],
        open=bool(row["open"]),
        auto_on=bool(row["auto_on"]) if "auto_on" in row.keys() else False,
        created_at=row["created_at"],
    )


def _validate_sellable_item(item_id: str) -> dict:
    for item in items().get("items", []):
        if item["id"] == item_id:
            tags = set(item.get("tags", []))
            if tags & SELLABLE_TAGS:
                return item
            raise HTTPException(status_code=400, detail="这个物还不能挂单，先选食物类")
    raise HTTPException(status_code=400, detail="找不到这个物品")


def get_shop(player_id: int) -> ShopPublic | None:
    with db() as conn:
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if row is None:
            return None
        user = conn.execute(
            "SELECT handle FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
    handle = user["handle"] if user else str(player_id)
    return _shop_row(row, handle)


def apply_shop(player_id: int, display_name: str) -> ShopPublic:
    now = utc_now()
    with db() as conn:
        existing = conn.execute(
            "SELECT player_id FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="你已经开过店了")

        wallet = conn.execute(
            "SELECT wallet_credits, handle FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
        if wallet is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        if int(wallet["wallet_credits"]) < SHOP_REGISTRATION_FEE:
            raise HTTPException(
                status_code=400,
                detail=f"登记费 {SHOP_REGISTRATION_FEE} 点不足",
            )

        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits - ? WHERE id = ?",
            (SHOP_REGISTRATION_FEE, player_id),
        )
        conn.execute(
            """
            INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
            VALUES (?, ?, 'shop_fee', 'shop', ?, ?)
            """,
            (player_id, -SHOP_REGISTRATION_FEE, str(player_id), now),
        )
        conn.execute(
            """
            INSERT INTO shops (player_id, display_name, city, open, created_at, company_id)
            VALUES (?, ?, '潮灯市', 1, ?, (
                SELECT id FROM companies WHERE owner_player_id = ? LIMIT 1
            ))
            """,
            (player_id, display_name.strip(), now, player_id),
        )
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
    assert row is not None
    return _shop_row(row, wallet["handle"])


def set_shop_open(player_id: int, open_: bool) -> ShopPublic:
    with db() as conn:
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="还没有店，先申请开店")
        conn.execute(
            "UPDATE shops SET open = ? WHERE player_id = ?",
            (1 if open_ else 0, player_id),
        )
        user = conn.execute("SELECT handle FROM users WHERE id = ?", (player_id,)).fetchone()
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
    assert row is not None
    return _shop_row(row, user["handle"] if user else str(player_id))


def set_shop_auto(player_id: int, auto_on: bool) -> ShopPublic:
    with db() as conn:
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="还没有店，先申请开店")
        conn.execute(
            "UPDATE shops SET auto_on = ? WHERE player_id = ?",
            (1 if auto_on else 0, player_id),
        )
        user = conn.execute("SELECT handle FROM users WHERE id = ?", (player_id,)).fetchone()
        row = conn.execute(
            "SELECT player_id, display_name, city, open, auto_on, created_at FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
    assert row is not None
    return _shop_row(row, user["handle"] if user else str(player_id))


def shop_auto_on(conn: sqlite3.Connection, seller_id: int) -> bool:
    row = conn.execute(
        "SELECT auto_on FROM shops WHERE player_id = ?",
        (seller_id,),
    ).fetchone()
    return bool(row and row["auto_on"])


def list_my_offers(player_id: int) -> list[PlayerOfferPublic]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, player_id, item_id, qty, price_credits, display, active, created_at
            FROM player_offers
            WHERE player_id = ?
            ORDER BY created_at DESC
            """,
            (player_id,),
        ).fetchall()
    return [_player_offer_row(row) for row in rows]


def create_player_offer(
    player_id: int,
    item_id: str,
    display: str,
    price_credits: int,
    qty: int,
) -> PlayerOfferPublic:
    _validate_sellable_item(item_id)
    shop = get_shop(player_id)
    if shop is None:
        raise HTTPException(status_code=400, detail="还没有店，先申请开店")

    offer_id = f"poffer_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO player_offers (id, player_id, item_id, qty, price_credits, display, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (offer_id, player_id, item_id, qty, price_credits, display.strip(), now),
        )
        row = conn.execute(
            """
            SELECT id, player_id, item_id, qty, price_credits, display, active, created_at
            FROM player_offers WHERE id = ?
            """,
            (offer_id,),
        ).fetchone()
    assert row is not None
    return _player_offer_row(row)


def set_offer_active(player_id: int, offer_id: str, active: bool) -> PlayerOfferPublic:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, player_id, item_id, qty, price_credits, display, active, created_at
            FROM player_offers WHERE id = ? AND player_id = ?
            """,
            (offer_id, player_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="找不到这个挂单")
        conn.execute(
            "UPDATE player_offers SET active = ? WHERE id = ?",
            (1 if active else 0, offer_id),
        )
        row = conn.execute(
            """
            SELECT id, player_id, item_id, qty, price_credits, display, active, created_at
            FROM player_offers WHERE id = ?
            """,
            (offer_id,),
        ).fetchone()
    assert row is not None
    return _player_offer_row(row)


def get_player_offer_row(offer_id: str) -> sqlite3.Row | None:
    with db() as conn:
        return conn.execute(
            """
            SELECT o.id, o.player_id, o.item_id, o.qty, o.price_credits, o.display, o.active, o.created_at,
                   s.display_name, s.city, s.open, u.handle
            FROM player_offers o
            JOIN shops s ON s.player_id = o.player_id
            JOIN users u ON u.id = o.player_id
            WHERE o.id = ? AND o.active = 1 AND s.open = 1
            """,
            (offer_id,),
        ).fetchone()


def player_offer_as_catalog(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "seller": {
            "kind": "player",
            "id": str(row["player_id"]),
            "display": row["display_name"],
        },
        "place": {"city": row["city"]},
        "gives": {"item_id": row["item_id"], "qty": row["qty"]},
        "price_credits": row["price_credits"],
        "display": row["display"],
        "active": True,
    }


def get_my_shop_payload(player_id: int) -> ShopMeResponse:
    shop = get_shop(player_id)
    offers = list_my_offers(player_id)
    return ShopMeResponse(
        shop=shop,
        registration_fee=SHOP_REGISTRATION_FEE,
        offers=offers,
    )


def list_market(city: str = "潮灯市") -> MarketResponse:
    with db() as conn:
        shops = conn.execute(
            """
            SELECT s.player_id, s.display_name, s.city, u.handle
            FROM shops s
            JOIN users u ON u.id = s.player_id
            WHERE s.city = ? AND s.open = 1
            ORDER BY s.created_at ASC
            """,
            (city,),
        ).fetchall()
        result: list[MarketShopPublic] = []
        for shop in shops:
            offers = conn.execute(
                """
                SELECT id, player_id, item_id, qty, price_credits, display, active, created_at
                FROM player_offers
                WHERE player_id = ? AND active = 1
                ORDER BY created_at DESC
                """,
                (shop["player_id"],),
            ).fetchall()
            if not offers:
                continue
            result.append(
                MarketShopPublic(
                    player_id=shop["player_id"],
                    handle=shop["handle"],
                    display_name=shop["display_name"],
                    city=shop["city"],
                    offers=[_player_offer_row(o) for o in offers],
                )
            )
    return MarketResponse(shops=result)


def active_player_offers_catalog() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT o.id, o.player_id, o.item_id, o.qty, o.price_credits, o.display, o.active, o.created_at,
                   s.display_name, s.city, s.open, u.handle
            FROM player_offers o
            JOIN shops s ON s.player_id = o.player_id
            JOIN users u ON u.id = o.player_id
            WHERE o.active = 1 AND s.open = 1
            ORDER BY o.created_at DESC
            """
        ).fetchall()
    return [player_offer_as_catalog(row) for row in rows]


def seller_display(seller_kind: str, seller_id: str) -> str:
    if seller_kind == "player":
        from services.players import get_player_by_id

        try:
            player = get_player_by_id(int(seller_id))
            shop = get_shop(player.id)
            if shop:
                return shop.display_name
            return player.handle
        except (ValueError, HTTPException):
            return seller_id
    from config_loader import game_messages

    npc_map = game_messages().get("npc_from_display", {})
    return npc_map.get(seller_id, seller_id)
