from __future__ import annotations

import sqlite3
import uuid

from db import db, utc_now
from fastapi import HTTPException


def create_company(player_id: int, display_name: str) -> dict:
    name = display_name.strip()
    now = utc_now()
    company_id = f"co_{uuid.uuid4().hex[:10]}"
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM companies WHERE owner_player_id = ?",
            (player_id,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="你已经登记过公司")

        user = conn.execute(
            "SELECT city FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        city = user["city"]

        conn.execute(
            """
            INSERT INTO companies (id, owner_player_id, display_name, city, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (company_id, player_id, name, city, now),
        )
        conn.execute(
            "UPDATE shops SET company_id = ? WHERE player_id = ?",
            (company_id, player_id),
        )
        row = conn.execute(
            """
            SELECT id, display_name, city, owner_player_id, created_at
            FROM companies WHERE id = ?
            """,
            (company_id,),
        ).fetchone()
    assert row is not None
    return dict(row)
