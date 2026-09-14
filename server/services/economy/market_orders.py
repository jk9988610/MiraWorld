"""Shared finished-goods market order placement."""
from __future__ import annotations

import json
import random
import sqlite3
import uuid

from db import utc_now
from services.economy.config import add_economy_ledger
from services.economy.effects import resolve_on_acquire
from services.economy.production import consume_institution_inventory
from services.economy.spotlight import add_spotlight_for_order


def credit_seller(
    conn: sqlite3.Connection,
    *,
    offer: dict,
    seller_kind: str,
    seller_id: str,
    price: int,
    order_id: str,
) -> str | None:
    institution_id = offer.get("institution_id")
    if institution_id:
        conn.execute(
            "UPDATE institutions SET wallet_credits = wallet_credits + ? WHERE id = ?",
            (price, institution_id),
        )
        add_economy_ledger(
            conn,
            account_kind="institution",
            account_id=institution_id,
            amount=price,
            entry_type="sale",
            ref_type="order",
            ref_id=order_id,
        )
        return institution_id

    if seller_kind == "npc":
        row = conn.execute(
            """
            SELECT id FROM institutions
            WHERE owner_kind = 'system' AND owner_id = ?
            LIMIT 1
            """,
            (seller_id,),
        ).fetchone()
        if row:
            institution_id = row["id"]
            conn.execute(
                "UPDATE institutions SET wallet_credits = wallet_credits + ? WHERE id = ?",
                (price, institution_id),
            )
            add_economy_ledger(
                conn,
                account_kind="institution",
                account_id=institution_id,
                amount=price,
                entry_type="sale",
                ref_type="order",
                ref_id=order_id,
            )
            return institution_id
    elif seller_kind == "player":
        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?",
            (price, int(seller_id)),
        )
        conn.execute(
            """
            INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
            VALUES (?, ?, 'sale', 'order', ?, ?)
            """,
            (int(seller_id), price, order_id, utc_now()),
        )
        row = conn.execute(
            """
            SELECT id FROM institutions
            WHERE owner_kind = 'player' AND owner_id = ?
            LIMIT 1
            """,
            (seller_id,),
        ).fetchone()
        if row:
            inst_id = row["id"]
            conn.execute(
                "UPDATE institutions SET wallet_credits = wallet_credits + ? WHERE id = ?",
                (price, inst_id),
            )
            add_economy_ledger(
                conn,
                account_kind="institution",
                account_id=inst_id,
                amount=price,
                entry_type="sale",
                ref_type="order",
                ref_id=order_id,
            )
            return inst_id
    return None


def place_market_order(
    conn: sqlite3.Connection,
    *,
    buyer_kind: str,
    buyer_group_id: str | None,
    buyer_institution_id: str | None,
    offer: dict,
    rng: random.Random,
) -> dict | None:
    price = int(offer["price_credits"])
    seller = offer.get("seller", {})
    seller_kind = seller.get("kind", "npc")
    seller_id = seller.get("id", "")
    gives = offer.get("gives", {})
    item_id = gives.get("item_id", "")
    item_qty = int(gives.get("qty", 1))
    display = offer.get("display", offer["id"])
    supply_inst = offer.get("institution_id")

    if supply_inst:
        row = conn.execute(
            """
            SELECT qty FROM institution_inventory
            WHERE institution_id = ? AND item_id = ?
            """,
            (supply_inst, item_id),
        ).fetchone()
        if row is None or int(row["qty"]) < item_qty:
            return None

    city = offer.get("place", {}).get("city", "潮灯市")
    job_display = None

    if buyer_kind == "pop_group":
        if not buyer_group_id:
            return None
        group = conn.execute(
            "SELECT wallet_credits, job_display, city FROM pop_groups WHERE id = ?",
            (buyer_group_id,),
        ).fetchone()
        if group is None or int(group["wallet_credits"]) < price:
            return None
        city = group["city"]
        job_display = group["job_display"]
    elif buyer_kind == "institution":
        if not buyer_institution_id:
            return None
        inst = conn.execute(
            "SELECT wallet_credits, city FROM institutions WHERE id = ?",
            (buyer_institution_id,),
        ).fetchone()
        if inst is None or int(inst["wallet_credits"]) < price:
            return None
        city = inst["city"]
    else:
        return None

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    now = utc_now()

    if buyer_kind == "pop_group":
        conn.execute(
            "UPDATE pop_groups SET wallet_credits = wallet_credits - ?, updated_at = ? WHERE id = ?",
            (price, now, buyer_group_id),
        )
        add_economy_ledger(
            conn,
            account_kind="pop_group",
            account_id=buyer_group_id,
            amount=-price,
            entry_type="purchase",
            ref_type="order",
            ref_id=order_id,
        )
    else:
        conn.execute(
            "UPDATE institutions SET wallet_credits = wallet_credits - ? WHERE id = ?",
            (price, buyer_institution_id),
        )
        add_economy_ledger(
            conn,
            account_kind="institution",
            account_id=buyer_institution_id,
            amount=-price,
            entry_type="purchase",
            ref_type="order",
            ref_id=order_id,
        )

    if supply_inst:
        if not consume_institution_inventory(conn, supply_inst, item_id, item_qty):
            return None

    payload = json.dumps(
        {"display": display, "item_id": item_id, "item_qty": item_qty},
        ensure_ascii=False,
    )
    conn.execute(
        """
        INSERT INTO orders (
            id, buyer_kind, buyer_id, buyer_group_id, buyer_institution_id,
            seller_kind, seller_id, city,
            offer_id, status, price_credits, escrow_credits, payload_json,
            created_at, updated_at
        ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'settled', ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            buyer_kind,
            buyer_group_id,
            buyer_institution_id,
            seller_kind,
            seller_id,
            city,
            offer["id"],
            price,
            price,
            payload,
            now,
            now,
        ),
    )

    spotlight_inst = credit_seller(
        conn,
        offer=offer,
        seller_kind=seller_kind,
        seller_id=seller_id,
        price=price,
        order_id=order_id,
    )

    resolve_on_acquire(
        conn,
        buyer_kind=buyer_kind,
        buyer_group_id=buyer_group_id,
        buyer_institution_id=buyer_institution_id,
        item_id=item_id,
        qty=item_qty,
        order_id=order_id,
    )

    if buyer_kind == "pop_group" and spotlight_inst and job_display:
        add_spotlight_for_order(
            conn,
            institution_id=spotlight_inst,
            pop_group_id=buyer_group_id,
            job_display=job_display,
            order_id=order_id,
            rng=rng,
        )

    return {"order_id": order_id, "price": price, "offer_id": offer["id"]}
