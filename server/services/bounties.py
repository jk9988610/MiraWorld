from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import HTTPException

from config_loader import game_messages, items
from db import db, utc_now
from schemas.bounty import (
    MAX_ACTIVE_BOUNTIES,
    MAX_BOUNTY_QTY,
    BountyListResponse,
    BountyPublic,
)


def _bounty_copy(key: str, **kwargs: str) -> str:
    templates = game_messages().get("bounty", {})
    tpl = templates.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


def _handle(conn: sqlite3.Connection, player_id: int | None) -> str:
    if player_id is None:
        return ""
    row = conn.execute("SELECT handle FROM users WHERE id = ?", (player_id,)).fetchone()
    return row["handle"] if row else str(player_id)


def _item_display(item_id: str) -> str:
    for item in items().get("items", []):
        if item["id"] == item_id:
            return item.get("display", item_id)
    raise HTTPException(status_code=400, detail="找不到这个物品")


def _title_for(kind: str, display: str, qty: int) -> str:
    prefix = "求购" if kind == "buy" else "求售"
    return f"{prefix} {display} ×{qty}"


def _row_to_public(row: sqlite3.Row, issuer_handle: str, worker_handle: str) -> BountyPublic:
    worker_id = row["worker_id"]
    kind = row["kind"] if "kind" in row.keys() and row["kind"] else "buy"
    item_id = row["item_id"] if "item_id" in row.keys() and row["item_id"] else ""
    qty = int(row["qty"]) if "qty" in row.keys() and row["qty"] is not None else 1
    item_display = row["item_display"] if "item_display" in row.keys() and row["item_display"] else row["title"]
    return BountyPublic(
        id=row["id"],
        issuer_id=row["issuer_id"],
        issuer_handle=issuer_handle,
        worker_id=int(worker_id) if worker_id is not None else None,
        worker_handle=worker_handle,
        city=row["city"],
        kind=kind,
        item_id=item_id,
        item_display=item_display,
        qty=qty,
        title=row["title"],
        price_credits=row["price_credits"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_row(conn: sqlite3.Connection, bounty_id: str) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, issuer_id, worker_id, city, kind, item_id, item_display, qty, title,
               price_credits, escrow_credits, status, payload_json, created_at, updated_at
        FROM bounties WHERE id = ?
        """,
        (bounty_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到这个委托")
    return row


def _public_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> BountyPublic:
    return _row_to_public(
        row,
        _handle(conn, row["issuer_id"]),
        _handle(conn, row["worker_id"]),
    )


def _add_ledger(
    conn: sqlite3.Connection,
    player_id: int,
    amount: int,
    entry_type: str,
    ref_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
        VALUES (?, ?, ?, 'bounty', ?, ?)
        """,
        (player_id, amount, entry_type, ref_id, utc_now()),
    )


def _notify(
    conn: sqlite3.Connection,
    *,
    to_player_id: int,
    from_kind: str,
    from_id: str | None,
    body: str,
    bounty_id: str,
) -> None:
    from services.messages import create_message

    create_message(
        conn,
        to_player_id=to_player_id,
        from_kind=from_kind,
        from_id=from_id,
        body=body,
        ref_type="bounty",
        ref_id=bounty_id,
    )


def create_bounty(
    issuer_id: int,
    kind: str,
    item_id: str,
    qty: int,
    price_credits: int,
    city: str,
) -> BountyPublic:
    if kind not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="只支持委托购买或委托出售")
    if qty < 1 or qty > MAX_BOUNTY_QTY:
        raise HTTPException(status_code=400, detail=f"数量须在 1～{MAX_BOUNTY_QTY} 之间")

    item_display = _item_display(item_id)
    title = _title_for(kind, item_display, qty)
    bounty_id = f"bty_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    payload = json.dumps({"kind": kind, "item_id": item_id, "qty": qty})

    with db() as conn:
        active = conn.execute(
            """
            SELECT COUNT(*) AS n FROM bounties
            WHERE issuer_id = ? AND status IN ('open', 'taken', 'submitted')
            """,
            (issuer_id,),
        ).fetchone()
        if active and int(active["n"]) >= MAX_ACTIVE_BOUNTIES:
            raise HTTPException(status_code=400, detail=f"最多同时有 {MAX_ACTIVE_BOUNTIES} 件委托商品")

        wallet = conn.execute(
            "SELECT wallet_credits FROM users WHERE id = ?",
            (issuer_id,),
        ).fetchone()
        if wallet is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        if int(wallet["wallet_credits"]) < price_credits:
            raise HTTPException(status_code=400, detail="余额不足")

        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits - ? WHERE id = ?",
            (price_credits, issuer_id),
        )
        _add_ledger(conn, issuer_id, -price_credits, "escrow", bounty_id)

        conn.execute(
            """
            INSERT INTO bounties (
                id, issuer_id, worker_id, city, kind, item_id, item_display, qty, title, body,
                price_credits, escrow_credits, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, '', ?, ?, 'open', ?, ?, ?)
            """,
            (
                bounty_id,
                issuer_id,
                city,
                kind,
                item_id,
                item_display,
                qty,
                title,
                price_credits,
                price_credits,
                payload,
                now,
                now,
            ),
        )
        row = _get_row(conn, bounty_id)
        return _public_from_row(conn, row)


def list_bounties(player_id: int, city: str = "潮灯市") -> BountyListResponse:
    with db() as conn:
        open_rows = conn.execute(
            """
            SELECT id, issuer_id, worker_id, city, kind, item_id, item_display, qty, title,
                   price_credits, escrow_credits, status, payload_json, created_at, updated_at
            FROM bounties
            WHERE status = 'open' AND city = ? AND issuer_id != ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (city, player_id),
        ).fetchall()
        issued_rows = conn.execute(
            """
            SELECT id, issuer_id, worker_id, city, kind, item_id, item_display, qty, title,
                   price_credits, escrow_credits, status, payload_json, created_at, updated_at
            FROM bounties
            WHERE issuer_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()
        taken_rows = conn.execute(
            """
            SELECT id, issuer_id, worker_id, city, kind, item_id, item_display, qty, title,
                   price_credits, escrow_credits, status, payload_json, created_at, updated_at
            FROM bounties
            WHERE worker_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()

        return BountyListResponse(
            open=[_public_from_row(conn, r) for r in open_rows],
            issued=[_public_from_row(conn, r) for r in issued_rows],
            taken=[_public_from_row(conn, r) for r in taken_rows],
        )


def take_bounty(worker_id: int, bounty_id: str) -> BountyPublic:
    with db() as conn:
        row = _get_row(conn, bounty_id)
        if row["status"] != "open":
            raise HTTPException(status_code=400, detail="这个委托已经被人接了")
        if row["issuer_id"] == worker_id:
            raise HTTPException(status_code=400, detail="不能接自己的委托")

        now = utc_now()
        conn.execute(
            """
            UPDATE bounties SET status = 'taken', worker_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (worker_id, now, bounty_id),
        )
        row = _get_row(conn, bounty_id)
        worker_handle = _handle(conn, worker_id)
        _notify(
            conn,
            to_player_id=row["issuer_id"],
            from_kind="player",
            from_id=str(worker_id),
            body=_bounty_copy("issuer_taken", title=row["title"], worker=worker_handle),
            bounty_id=bounty_id,
        )
        return _public_from_row(conn, row)


def submit_bounty(worker_id: int, bounty_id: str) -> BountyPublic:
    with db() as conn:
        row = _get_row(conn, bounty_id)
        if row["worker_id"] != worker_id:
            raise HTTPException(status_code=404, detail="找不到这个委托")
        if row["status"] != "taken":
            raise HTTPException(status_code=400, detail="还不能交差")

        now = utc_now()
        conn.execute(
            "UPDATE bounties SET status = 'submitted', updated_at = ? WHERE id = ?",
            (now, bounty_id),
        )
        row = _get_row(conn, bounty_id)
        worker_handle = _handle(conn, worker_id)
        _notify(
            conn,
            to_player_id=row["issuer_id"],
            from_kind="player",
            from_id=str(worker_id),
            body=_bounty_copy("issuer_submitted", title=row["title"], worker=worker_handle),
            bounty_id=bounty_id,
        )
        return _public_from_row(conn, row)


def settle_bounty(issuer_id: int, bounty_id: str) -> BountyPublic:
    with db() as conn:
        row = _get_row(conn, bounty_id)
        if row["issuer_id"] != issuer_id:
            raise HTTPException(status_code=404, detail="找不到这个委托")
        if row["status"] != "submitted":
            raise HTTPException(status_code=400, detail="还不能确认交差")
        worker_id = row["worker_id"]
        if worker_id is None:
            raise HTTPException(status_code=400, detail="还没有接单人")

        price = int(row["price_credits"])
        now = utc_now()
        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?",
            (price, worker_id),
        )
        _add_ledger(conn, int(worker_id), price, "payout", bounty_id)
        conn.execute(
            "UPDATE bounties SET status = 'settled', updated_at = ? WHERE id = ?",
            (now, bounty_id),
        )
        row = _get_row(conn, bounty_id)
        _notify(
            conn,
            to_player_id=int(worker_id),
            from_kind="system",
            from_id=None,
            body=_bounty_copy("worker_settled", title=row["title"], price=str(price)),
            bounty_id=bounty_id,
        )
        return _public_from_row(conn, row)


def cancel_bounty(issuer_id: int, bounty_id: str) -> BountyPublic:
    with db() as conn:
        row = _get_row(conn, bounty_id)
        if row["issuer_id"] != issuer_id:
            raise HTTPException(status_code=404, detail="找不到这个委托")
        if row["status"] != "open":
            raise HTTPException(status_code=400, detail="只能取消还没人接的委托")

        price = int(row["price_credits"])
        now = utc_now()
        conn.execute(
            "UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?",
            (price, issuer_id),
        )
        _add_ledger(conn, issuer_id, price, "refund", bounty_id)
        conn.execute(
            "UPDATE bounties SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (now, bounty_id),
        )
        row = _get_row(conn, bounty_id)
        return _public_from_row(conn, row)
