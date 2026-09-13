from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import HTTPException

from config_loader import game_messages
from db import db, utc_now
from schemas.bounty import BountyListResponse, BountyPublic


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


def _payload_dict(row: sqlite3.Row) -> dict:
    return json.loads(row["payload_json"] or "{}")


def _notify_bounty(payload: dict) -> bool:
    return not bool(payload.get("in_person"))


def _row_to_public(row: sqlite3.Row, issuer_handle: str, worker_handle: str) -> BountyPublic:
    payload = _payload_dict(row)
    worker_id = row["worker_id"]
    return BountyPublic(
        id=row["id"],
        issuer_id=row["issuer_id"],
        issuer_handle=issuer_handle,
        worker_id=int(worker_id) if worker_id is not None else None,
        worker_handle=worker_handle,
        city=row["city"],
        title=row["title"],
        body=row["body"] or "",
        price_credits=row["price_credits"],
        status=row["status"],
        in_person=bool(payload.get("in_person")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_row(conn: sqlite3.Connection, bounty_id: str) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, issuer_id, worker_id, city, title, body, price_credits, escrow_credits,
               status, payload_json, created_at, updated_at
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
    title: str,
    body: str,
    price_credits: int,
    city: str,
    in_person: bool,
) -> BountyPublic:
    bounty_id = f"bty_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    payload = json.dumps({"in_person": in_person})

    with db() as conn:
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
                id, issuer_id, worker_id, city, title, body, price_credits, escrow_credits,
                status, payload_json, created_at, updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (
                bounty_id,
                issuer_id,
                city,
                title.strip(),
                body.strip(),
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
            SELECT id, issuer_id, worker_id, city, title, body, price_credits, escrow_credits,
                   status, payload_json, created_at, updated_at
            FROM bounties
            WHERE status = 'open' AND city = ? AND issuer_id != ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (city, player_id),
        ).fetchall()
        issued_rows = conn.execute(
            """
            SELECT id, issuer_id, worker_id, city, title, body, price_credits, escrow_credits,
                   status, payload_json, created_at, updated_at
            FROM bounties
            WHERE issuer_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (player_id,),
        ).fetchall()
        taken_rows = conn.execute(
            """
            SELECT id, issuer_id, worker_id, city, title, body, price_credits, escrow_credits,
                   status, payload_json, created_at, updated_at
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
        payload = _payload_dict(row)
        if _notify_bounty(payload):
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
        payload = _payload_dict(row)
        if _notify_bounty(payload):
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
        payload = _payload_dict(row)
        if _notify_bounty(payload):
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
