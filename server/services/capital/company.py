from __future__ import annotations

import sqlite3
import uuid

from db import db, utc_now
from fastapi import HTTPException
from services.capital.institution import ensure_player_shop_institution, list_company_institutions


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
            INSERT INTO companies (
                id, owner_player_id, display_name, city, wallet_credits, created_at
            ) VALUES (?, ?, ?, ?, 0, ?)
            """,
            (company_id, player_id, name, city, now),
        )
        conn.execute(
            "UPDATE shops SET company_id = ? WHERE player_id = ?",
            (company_id, player_id),
        )
        shop = conn.execute(
            "SELECT display_name, city FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if shop:
            ensure_player_shop_institution(
                conn,
                player_id=player_id,
                display_name=shop["display_name"],
                city=shop["city"],
                company_id=company_id,
            )
        conn.execute(
            "UPDATE institutions SET company_id = ? WHERE owner_kind = 'player' AND owner_id = ?",
            (company_id, str(player_id)),
        )
        row = conn.execute(
            """
            SELECT id, display_name, city, owner_player_id, wallet_credits, created_at
            FROM companies WHERE id = ?
            """,
            (company_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def transfer_company_funds(player_id: int, direction: str, amount: int) -> dict:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="金额须大于 0")
    if direction not in {"to_company", "to_player"}:
        raise HTTPException(status_code=400, detail="direction 须为 to_company 或 to_player")

    now = utc_now()
    with db() as conn:
        company = conn.execute(
            """
            SELECT id, wallet_credits FROM companies WHERE owner_player_id = ?
            """,
            (player_id,),
        ).fetchone()
        if company is None:
            raise HTTPException(status_code=400, detail="请先登记公司")

        wallet = conn.execute(
            "SELECT wallet_credits FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
        if wallet is None:
            raise HTTPException(status_code=401, detail="用户不存在")

        player_bal = int(wallet["wallet_credits"])
        company_bal = int(company["wallet_credits"])

        if direction == "to_company":
            if player_bal < amount:
                raise HTTPException(status_code=400, detail="个人钱包点数不足")
            conn.execute(
                "UPDATE users SET wallet_credits = wallet_credits - ? WHERE id = ?",
                (amount, player_id),
            )
            conn.execute(
                "UPDATE companies SET wallet_credits = wallet_credits + ? WHERE id = ?",
                (amount, company["id"]),
            )
            conn.execute(
                """
                INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
                VALUES (?, ?, 'company_deposit', 'company', ?, ?)
                """,
                (player_id, -amount, company["id"], now),
            )
        else:
            if company_bal < amount:
                raise HTTPException(status_code=400, detail="公司账上点数不足")
            conn.execute(
                "UPDATE companies SET wallet_credits = wallet_credits - ? WHERE id = ?",
                (amount, company["id"]),
            )
            conn.execute(
                "UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?",
                (amount, player_id),
            )
            conn.execute(
                """
                INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
                VALUES (?, ?, 'company_withdraw', 'company', ?, ?)
                """,
                (player_id, amount, company["id"], now),
            )

        player_after = conn.execute(
            "SELECT wallet_credits FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()
        company_after = conn.execute(
            "SELECT wallet_credits FROM companies WHERE id = ?",
            (company["id"],),
        ).fetchone()

    return {
        "ok": True,
        "direction": direction,
        "amount": amount,
        "wallet_credits": int(player_after["wallet_credits"]),
        "company_wallet": int(company_after["wallet_credits"]),
    }


def get_company_detail(conn: sqlite3.Connection, player_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT id, display_name, city, owner_player_id, wallet_credits, created_at
        FROM companies WHERE owner_player_id = ?
        """,
        (player_id,),
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["institutions"] = list_company_institutions(conn, row["id"])
    return data
