from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import HTTPException

from config_loader import game_messages
from db import db, utc_now
from schemas.order import OrderListResponse, OrderPublic
from services.catalog import get_offer, item_display
from services.inventory import add_stack
from services.messages import create_message


def _order_copy(key: str, **kwargs: str) -> str:
    templates = game_messages().get("order", {})
    tpl = templates.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


def _row_to_order(row: sqlite3.Row, offer_display: str = "", item_id: str = "", item_qty: int = 0) -> OrderPublic:
    return OrderPublic(
        id=row["id"],
        buyer_id=row["buyer_id"],
        seller_kind=row["seller_kind"],
        seller_id=row["seller_id"],
        city=row["city"],
        offer_id=row["offer_id"],
        status=row["status"],
        price_credits=row["price_credits"],
        escrow_credits=row["escrow_credits"],
        display=offer_display,
        item_id=item_id,
        item_qty=item_qty,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _offer_meta(offer: dict) -> tuple[str, str, int]:
    display = offer.get("display", offer["id"])
    gives = offer.get("gives", {})
    item_id = gives.get("item_id", "")
    item_qty = int(gives.get("qty", 1))
    return display, item_id, item_qty


def _get_order_row(conn: sqlite3.Connection, order_id: str, buyer_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, buyer_id, seller_kind, seller_id, city, offer_id, status,
               price_credits, escrow_credits, payload_json, created_at, updated_at
        FROM orders WHERE id = ? AND buyer_id = ?
        """,
        (order_id, buyer_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return row


def _public_from_row(row: sqlite3.Row) -> OrderPublic:
    offer = get_offer(row["offer_id"])
    display, item_id, item_qty = _offer_meta(offer)
    return _row_to_order(row, display, item_id, item_qty)


def _add_ledger(
    conn: sqlite3.Connection,
    player_id: int,
    amount: int,
    entry_type: str,
    ref_type: str | None,
    ref_id: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (player_id, amount, entry_type, ref_type, ref_id, utc_now()),
    )


def place_order(player_id: int, offer_id: str) -> OrderPublic:
    offer = get_offer(offer_id)
    price = int(offer["price_credits"])
    seller = offer.get("seller", {})
    place = offer.get("place", {})
    display, item_id, item_qty = _offer_meta(offer)
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    payload = json.dumps({"display": display, "item_id": item_id, "item_qty": item_qty})

    with db() as conn:
        wallet = conn.execute(
            "SELECT wallet_credits FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
        if wallet is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        if int(wallet["wallet_credits"]) < price:
            raise HTTPException(status_code=400, detail="余额不足")

        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits - ? WHERE id = ?",
            (price, player_id),
        )
        _add_ledger(conn, player_id, -price, "escrow", "order", order_id)

        conn.execute(
            """
            INSERT INTO orders (
                id, buyer_id, seller_kind, seller_id, city, offer_id, status,
                price_credits, escrow_credits, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'escrowed', ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                player_id,
                seller.get("kind", "npc"),
                seller.get("id", ""),
                place.get("city", "潮灯市"),
                offer_id,
                price,
                price,
                payload,
                now,
                now,
            ),
        )

        create_message(
            conn,
            to_player_id=player_id,
            from_kind="npc",
            from_id=seller.get("id"),
            body=_order_copy("received", display=display),
            ref_type="order",
            ref_id=order_id,
        )

        ready_at = utc_now()
        conn.execute(
            """
            UPDATE orders SET status = 'ready', updated_at = ?
            WHERE id = ?
            """,
            (ready_at, order_id),
        )

        create_message(
            conn,
            to_player_id=player_id,
            from_kind="npc",
            from_id=seller.get("id"),
            body=_order_copy("ready", display=display),
            ref_type="order",
            ref_id=order_id,
        )

        _add_ledger(conn, player_id, 0, "settle", "order", order_id)

        row = _get_order_row(conn, order_id, player_id)

    return _public_from_row(row)


def list_orders(player_id: int) -> OrderListResponse:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, buyer_id, seller_kind, seller_id, city, offer_id, status,
                   price_credits, escrow_credits, payload_json, created_at, updated_at
            FROM orders
            WHERE buyer_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()
    return OrderListResponse(orders=[_public_from_row(row) for row in rows])


def get_order(player_id: int, order_id: str) -> OrderPublic:
    with db() as conn:
        row = _get_order_row(conn, order_id, player_id)
    return _public_from_row(row)


def pickup_order(player_id: int, order_id: str) -> OrderPublic:
    offer = None
    with db() as conn:
        row = _get_order_row(conn, order_id, player_id)
        if row["status"] != "ready":
            raise HTTPException(status_code=400, detail=_order_copy("pickup_blocked"))
        offer = get_offer(row["offer_id"])
        _, item_id, item_qty = _offer_meta(offer)
        add_stack(conn, player_id, item_id, item_qty)
        settled_at = utc_now()
        conn.execute(
            "UPDATE orders SET status = 'settled', updated_at = ? WHERE id = ?",
            (settled_at, order_id),
        )
        row = _get_order_row(conn, order_id, player_id)
    return _public_from_row(row)
