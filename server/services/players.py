from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from config_loader import welcome
from db import db, utc_now
from schemas.player import PlayerPublic
from services.inventory import stack_summary


def _row_to_player(row: sqlite3.Row, visit_count: int = 0, stacks: list[dict] | None = None) -> PlayerPublic:
    return PlayerPublic(
        id=row["id"],
        handle=row["handle"],
        email=row["email"],
        city=row["city"],
        wallet_credits=row["wallet_credits"],
        bio=row["bio"] or "",
        created_at=row["created_at"],
        visit_count=visit_count,
        stacks=stacks or [],
    )


def _visit_count(conn: sqlite3.Connection, player_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM visits WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    return int(row["c"]) if row else 0


def get_player_by_handle(handle: str) -> PlayerPublic:
    handle_clean = handle.strip()
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, handle, email, city, wallet_credits, bio, created_at
            FROM users WHERE handle = ? COLLATE NOCASE
            """,
            (handle_clean,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="找不到这个行者")
        return _row_to_player(row, _visit_count(conn, row["id"]))


def get_player_by_id(player_id: int) -> PlayerPublic:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, handle, email, city, wallet_credits, bio, created_at
            FROM users WHERE id = ?
            """,
            (player_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        stack_rows = conn.execute(
            """
            SELECT item_id, qty FROM stacks
            WHERE player_id = ? AND qty > 0
            ORDER BY item_id
            """,
            (player_id,),
        ).fetchall()
        from services.catalog import item_display

        stacks = [
            {
                "item_id": s["item_id"],
                "display": item_display(s["item_id"]),
                "qty": int(s["qty"]),
            }
            for s in stack_rows
        ]
        return _row_to_player(row, _visit_count(conn, player_id), stacks)


def register_player(
    handle: str,
    password: str,
    password_hasher,
    email: str | None = None,
) -> PlayerPublic:
    cfg = welcome()
    city = cfg.get("default_city", "潮灯市")
    credits = int(cfg.get("newbie_credits", 300))
    created_at = utc_now()
    handle_clean = handle.strip()
    email_clean = email.strip().lower() if email else None

    try:
        with db() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (handle, email, password_hash, city, wallet_credits, bio, created_at)
                VALUES (?, ?, ?, ?, ?, '', ?)
                """,
                (
                    handle_clean,
                    email_clean,
                    password_hasher(password),
                    city,
                    credits,
                    created_at,
                ),
            )
            player_id = int(cur.lastrowid)
            row = conn.execute(
                """
                SELECT id, handle, email, city, wallet_credits, bio, created_at
                FROM users WHERE id = ?
                """,
                (player_id,),
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        msg = str(exc).lower()
        if "handle" in msg:
            raise HTTPException(status_code=409, detail="该名字已被使用")
        if "email" in msg:
            raise HTTPException(status_code=409, detail="该邮箱已注册")
        raise HTTPException(status_code=409, detail="注册失败")

    assert row is not None
    return _row_to_player(row, 0)


def login_player(handle: str, password: str, password_verifier) -> PlayerPublic:
    handle_clean = handle.strip()
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, handle, email, city, wallet_credits, bio, created_at, password_hash
            FROM users WHERE handle = ? COLLATE NOCASE
            """,
            (handle_clean,),
        ).fetchone()
        if row is None or not password_verifier(password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="名字或密码错误")
        return _row_to_player(row, _visit_count(conn, row["id"]))


def update_bio(player_id: int, bio: str) -> PlayerPublic:
    with db() as conn:
        conn.execute("UPDATE users SET bio = ? WHERE id = ?", (bio.strip(), player_id))
    return get_player_by_id(player_id)
