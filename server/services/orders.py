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
from services.players import get_player_by_id
from services.shops import seller_display, shop_auto_on


def _order_copy(section: str, key: str, **kwargs: str) -> str:
    templates = game_messages().get(section, {})
    if section != "order":
        tpl = templates.get(key, "")
    else:
        tpl = templates.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


def _row_to_order(row: sqlite3.Row, offer_display: str = "", item_id: str = "", item_qty: int = 0) -> OrderPublic:
    keys = row.keys()
    return OrderPublic(
        id=row["id"],
        buyer_kind=row["buyer_kind"] if "buyer_kind" in keys else "player",
        buyer_id=row["buyer_id"],
        buyer_group_id=row["buyer_group_id"] if "buyer_group_id" in keys else None,
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


def _payload_dict(row: sqlite3.Row) -> dict:
    return json.loads(row["payload_json"] or "{}")


def _make_payload(display: str, item_id: str, item_qty: int) -> str:
    return json.dumps(
        {
            "display": display,
            "item_id": item_id,
            "item_qty": item_qty,
        }
    )


def _notify_buyer_ready(
    conn: sqlite3.Connection,
    *,
    buyer_id: int,
    seller_kind: str,
    seller_id: str,
    display: str,
    order_id: str,
) -> None:
    if seller_kind == "npc":
        body = _order_copy("order", "ready", display=display)
        from_kind, from_id = "npc", seller_id
    else:
        body = _order_copy("player_order", "buyer_ready", display=display)
        from_kind, from_id = "player", seller_id
    create_message(
        conn,
        to_player_id=buyer_id,
        from_kind=from_kind,
        from_id=from_id,
        body=body,
        ref_type="order",
        ref_id=order_id,
    )


def _player_order_to_ready(
    conn: sqlite3.Connection,
    order_id: str,
    seller_id: int,
    row: sqlite3.Row,
) -> None:
    now = utc_now()
    conn.execute(
        "UPDATE orders SET status = 'ready', updated_at = ? WHERE id = ?",
        (now, order_id),
    )
    payload = _payload_dict(row)
    display = payload.get("display", "")
    _notify_buyer_ready(
        conn,
        buyer_id=row["buyer_id"],
        seller_kind="player",
        seller_id=str(seller_id),
        display=display,
        order_id=order_id,
    )


def _payload_meta(row: sqlite3.Row) -> tuple[str, str, int]:
    payload = json.loads(row["payload_json"] or "{}")
    display = payload.get("display", "")
    item_id = payload.get("item_id", "")
    item_qty = int(payload.get("item_qty", 0))
    return display, item_id, item_qty


def _public_from_row(row: sqlite3.Row) -> OrderPublic:
    display, item_id, item_qty = _payload_meta(row)
    if not display:
        try:
            offer = get_offer(row["offer_id"])
            display, item_id, item_qty = _offer_meta(offer)
        except HTTPException:
            pass
    return _row_to_order(row, display, item_id, item_qty)


def _get_order_row(conn: sqlite3.Connection, order_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, buyer_kind, buyer_id, buyer_group_id, seller_kind, seller_id, city, offer_id, status,
               price_credits, escrow_credits, payload_json, created_at, updated_at
        FROM orders WHERE id = ?
        """,
        (order_id,),
    ).fetchone()


def _get_buyer_order_row(conn: sqlite3.Connection, order_id: str, buyer_id: int) -> sqlite3.Row:
    row = _get_order_row(conn, order_id)
    if row is None or row["buyer_id"] != buyer_id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return row


def _get_seller_order_row(conn: sqlite3.Connection, order_id: str, seller_id: int) -> sqlite3.Row:
    row = _get_order_row(conn, order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if row["seller_kind"] != "player" or row["seller_id"] != str(seller_id):
        raise HTTPException(status_code=404, detail="订单不存在")
    return row


def _can_view_order(row: sqlite3.Row, player_id: int) -> bool:
    if row["buyer_id"] == player_id:
        return True
    return row["seller_kind"] == "player" and row["seller_id"] == str(player_id)


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
    seller_kind = seller.get("kind", "npc")
    seller_id = seller.get("id", "")
    place = offer.get("place", {})
    display, item_id, item_qty = _offer_meta(offer)

    if seller_kind == "player" and seller_id == str(player_id):
        raise HTTPException(status_code=400, detail="不能点自己店的挂单")

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    payload = _make_payload(display, item_id, item_qty)
    seller_name = seller.get("display") or seller_display(seller_kind, seller_id)

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
                id, buyer_kind, buyer_id, buyer_group_id, buyer_institution_id,
                seller_kind, seller_id, city, offer_id, status,
                price_credits, escrow_credits, payload_json, created_at, updated_at
            ) VALUES (?, 'player', ?, NULL, NULL, ?, ?, ?, ?, 'escrowed', ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                player_id,
                seller_kind,
                seller_id,
                place.get("city", "潮灯市"),
                offer_id,
                price,
                price,
                payload,
                now,
                now,
            ),
        )

        if seller_kind == "npc":
            ready_at = utc_now()
            conn.execute(
                "UPDATE orders SET status = 'ready', updated_at = ? WHERE id = ?",
                (ready_at, order_id),
            )
            _add_ledger(conn, player_id, 0, "settle", "order", order_id)
            _notify_buyer_ready(
                conn,
                buyer_id=player_id,
                seller_kind="npc",
                seller_id=seller_id,
                display=display,
                order_id=order_id,
            )
        else:
            buyer = get_player_by_id(player_id)
            create_message(
                conn,
                to_player_id=player_id,
                from_kind="player",
                from_id=seller_id,
                body=_order_copy(
                    "player_order",
                    "buyer_received",
                    display=display,
                    shop=seller_name,
                ),
                ref_type="order",
                ref_id=order_id,
            )
            create_message(
                conn,
                to_player_id=int(seller_id),
                from_kind="player",
                from_id=str(player_id),
                body=_order_copy(
                    "player_order",
                    "seller_new",
                    display=display,
                    buyer=buyer.handle,
                ),
                ref_type="order",
                ref_id=order_id,
            )
            row_after = _get_order_row(conn, order_id)
            assert row_after is not None
            if shop_auto_on(conn, int(seller_id)):
                _player_order_to_ready(conn, order_id, int(seller_id), row_after)

        row = _get_buyer_order_row(conn, order_id, player_id)

    return _public_from_row(row)


def list_orders(player_id: int) -> OrderListResponse:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, buyer_kind, buyer_id, buyer_group_id, seller_kind, seller_id, city, offer_id, status,
                   price_credits, escrow_credits, payload_json, created_at, updated_at
            FROM orders
            WHERE buyer_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()
    return OrderListResponse(orders=[_public_from_row(row) for row in rows])


def list_selling_orders(player_id: int) -> OrderListResponse:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, buyer_kind, buyer_id, buyer_group_id, seller_kind, seller_id, city, offer_id, status,
                   price_credits, escrow_credits, payload_json, created_at, updated_at
            FROM orders
            WHERE seller_kind = 'player' AND seller_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (str(player_id),),
        ).fetchall()
    return OrderListResponse(orders=[_public_from_row(row) for row in rows])


def get_order(player_id: int, order_id: str) -> OrderPublic:
    with db() as conn:
        row = _get_order_row(conn, order_id)
        if row is None or not _can_view_order(row, player_id):
            raise HTTPException(status_code=404, detail="订单不存在")
    return _public_from_row(row)


def accept_order(seller_id: int, order_id: str) -> OrderPublic:
    with db() as conn:
        row = _get_seller_order_row(conn, order_id, seller_id)
        if row["status"] != "escrowed":
            raise HTTPException(status_code=400, detail="这单已经接过了")
        display, _, _ = _payload_meta(row)
        now = utc_now()
        conn.execute(
            "UPDATE orders SET status = 'processing', updated_at = ? WHERE id = ?",
            (now, order_id),
        )
        create_message(
            conn,
            to_player_id=row["buyer_id"],
            from_kind="player",
            from_id=str(seller_id),
            body=_order_copy("player_order", "buyer_accepted", display=display),
            ref_type="order",
            ref_id=order_id,
        )
        row = _get_seller_order_row(conn, order_id, seller_id)
    return _public_from_row(row)


def mark_order_ready(seller_id: int, order_id: str) -> OrderPublic:
    with db() as conn:
        row = _get_seller_order_row(conn, order_id, seller_id)
        if row["status"] not in ("escrowed", "processing"):
            raise HTTPException(status_code=400, detail="还不能标记好了")
        display, _, _ = _payload_meta(row)
        now = utc_now()
        conn.execute(
            "UPDATE orders SET status = 'ready', updated_at = ? WHERE id = ?",
            (now, order_id),
        )
        _notify_buyer_ready(
            conn,
            buyer_id=row["buyer_id"],
            seller_kind="player",
            seller_id=str(seller_id),
            display=display,
            order_id=order_id,
        )
        row = _get_seller_order_row(conn, order_id, seller_id)
    return _public_from_row(row)


def pickup_order(player_id: int, order_id: str) -> OrderPublic:
    with db() as conn:
        row = _get_buyer_order_row(conn, order_id, player_id)
        if row["status"] != "ready":
            raise HTTPException(status_code=400, detail=_order_copy("order", "pickup_blocked"))
        display, item_id, item_qty = _payload_meta(row)
        if not item_id:
            offer = get_offer(row["offer_id"])
            _, item_id, item_qty = _offer_meta(offer)
        add_stack(conn, player_id, item_id, item_qty)
        settled_at = utc_now()
        conn.execute(
            "UPDATE orders SET status = 'settled', updated_at = ? WHERE id = ?",
            (settled_at, order_id),
        )
        if row["seller_kind"] == "player":
            seller_id = int(row["seller_id"])
            price = int(row["price_credits"])
            conn.execute(
                "UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?",
                (price, seller_id),
            )
            _add_ledger(conn, seller_id, price, "sale", "order", order_id)
        row = _get_buyer_order_row(conn, order_id, player_id)
    return _public_from_row(row)
