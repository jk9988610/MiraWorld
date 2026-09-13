from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from config_loader import game_messages
from db import db, utc_now
from schemas.message import MessageListResponse, MessagePublic
from services.players import get_player_by_handle, get_player_by_id
from services.shops import seller_display


def _from_display(from_kind: str, from_id: str | None) -> str:
    if not from_id:
        return ""
    if from_kind == "player":
        try:
            player = get_player_by_id(int(from_id))
            return player.handle
        except (ValueError, HTTPException):
            return from_id
    npc_map = game_messages().get("npc_from_display", {})
    return npc_map.get(from_id, from_id)


def _row_to_message(row: sqlite3.Row) -> MessagePublic:
    return MessagePublic(
        id=row["id"],
        from_kind=row["from_kind"],
        from_id=row["from_id"],
        from_display=_from_display(row["from_kind"], row["from_id"]),
        body=row["body"],
        ref_type=row["ref_type"],
        ref_id=row["ref_id"],
        read_at=row["read_at"],
        created_at=row["created_at"],
    )


def create_message(
    conn: sqlite3.Connection,
    *,
    to_player_id: int,
    from_kind: str,
    from_id: str | None,
    body: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO messages (to_player_id, from_kind, from_id, body, ref_type, ref_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (to_player_id, from_kind, from_id, body, ref_type, ref_id, utc_now()),
    )
    return int(cur.lastrowid)


def send_player_message(
    from_player_id: int,
    to_handle: str,
    body: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
) -> MessagePublic:
    if to_handle.strip().lower() == get_player_by_id(from_player_id).handle.lower():
        raise HTTPException(status_code=400, detail="不能给自己发往来")
    recipient = get_player_by_handle(to_handle.strip())
    with db() as conn:
        msg_id = create_message(
            conn,
            to_player_id=recipient.id,
            from_kind="player",
            from_id=str(from_player_id),
            body=body.strip(),
            ref_type=ref_type,
            ref_id=ref_id,
        )
        row = conn.execute(
            """
            SELECT id, from_kind, from_id, body, ref_type, ref_id, read_at, created_at
            FROM messages WHERE id = ?
            """,
            (msg_id,),
        ).fetchone()
    assert row is not None
    return _row_to_message(row)


def list_messages(player_id: int) -> MessageListResponse:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT id, from_kind, from_id, body, ref_type, ref_id, read_at, created_at
            FROM messages
            WHERE to_player_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (player_id,),
        ).fetchall()
    return MessageListResponse(messages=[_row_to_message(row) for row in rows])


def unread_count(player_id: int) -> int:
    with db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM messages
            WHERE to_player_id = ? AND read_at IS NULL
            """,
            (player_id,),
        ).fetchone()
    return int(row["c"]) if row else 0


def mark_read(player_id: int, message_id: int) -> MessagePublic:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, from_kind, from_id, body, ref_type, ref_id, read_at, created_at
            FROM messages
            WHERE id = ? AND to_player_id = ?
            """,
            (message_id, player_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="通知不存在")
        if row["read_at"] is None:
            now = utc_now()
            conn.execute(
                "UPDATE messages SET read_at = ? WHERE id = ?",
                (now, message_id),
            )
            row = conn.execute(
                """
                SELECT id, from_kind, from_id, body, ref_type, ref_id, read_at, created_at
                FROM messages WHERE id = ?
                """,
                (message_id,),
            ).fetchone()
    assert row is not None
    return _row_to_message(row)
