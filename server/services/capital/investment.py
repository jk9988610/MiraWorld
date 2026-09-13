from __future__ import annotations

import random
import sqlite3
from datetime import UTC, datetime

from config_loader import capitalist_economy
from db import db, utc_now
from fastapi import HTTPException
from services.capital.assets import player_total_assets


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _investment_amount(asset_total: int, player_id: int, grant_date: str) -> tuple[int, float]:
    cfg = capitalist_economy()
    base = int(cfg.get("daily_investment_base", 200000))
    pct_min = float(cfg.get("daily_investment_asset_pct_min", 0.05))
    pct_max = float(cfg.get("daily_investment_asset_pct_max", 0.10))
    rng = random.Random(f"invest:{player_id}:{grant_date}")
    pct = pct_min + rng.random() * (pct_max - pct_min)
    bonus = int(asset_total * pct)
    return base + bonus, pct


def get_capital_status(player_id: int) -> dict:
    cfg = capitalist_economy()
    grant_date = _today()
    with db() as conn:
        assets = player_total_assets(conn, player_id)
        company = conn.execute(
            """
            SELECT id, display_name, city, owner_player_id, created_at
            FROM companies WHERE owner_player_id = ?
            """,
            (player_id,),
        ).fetchone()
        last = conn.execute(
            """
            SELECT grant_date, amount, asset_total, asset_pct, created_at
            FROM player_daily_grants
            WHERE player_id = ?
            ORDER BY grant_date DESC LIMIT 1
            """,
            (player_id,),
        ).fetchone()
        claimed_today = conn.execute(
            """
            SELECT 1 FROM player_daily_grants
            WHERE player_id = ? AND grant_date = ?
            """,
            (player_id, grant_date),
        ).fetchone()
        shop = conn.execute(
            "SELECT 1 FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()

    return {
        "assets": assets,
        "company": dict(company) if company else None,
        "has_shop": shop is not None,
        "last_grant": dict(last) if last else None,
        "can_claim_today": claimed_today is None,
        "config": {
            "daily_investment_base": int(cfg.get("daily_investment_base", 200000)),
            "asset_pct_min": float(cfg.get("daily_investment_asset_pct_min", 0.05)),
            "asset_pct_max": float(cfg.get("daily_investment_asset_pct_max", 0.10)),
        },
    }


def claim_daily_investment(player_id: int) -> dict:
    grant_date = _today()
    now = utc_now()
    with db() as conn:
        existing = conn.execute(
            """
            SELECT 1 FROM player_daily_grants
            WHERE player_id = ? AND grant_date = ?
            """,
            (player_id, grant_date),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="今日日投已领取")

        assets = player_total_assets(conn, player_id)
        amount, pct = _investment_amount(assets["total"], player_id, grant_date)
        conn.execute(
            """
            UPDATE users SET wallet_credits = wallet_credits + ? WHERE id = ?
            """,
            (amount, player_id),
        )
        conn.execute(
            """
            INSERT INTO player_daily_grants (
                player_id, grant_date, amount, asset_total, asset_pct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (player_id, grant_date, amount, assets["total"], pct, now),
        )
        conn.execute(
            """
            INSERT INTO ledger_entries (player_id, amount, type, ref_type, ref_id, created_at)
            VALUES (?, ?, 'daily_investment', 'grant', ?, ?)
            """,
            (player_id, amount, grant_date, now),
        )
        wallet = conn.execute(
            "SELECT wallet_credits FROM users WHERE id = ?",
            (player_id,),
        ).fetchone()

    grant = {
        "grant_date": grant_date,
        "amount": amount,
        "asset_total": assets["total"],
        "asset_pct": pct,
        "created_at": now,
    }
    return {
        "ok": True,
        "grant": grant,
        "wallet_credits": int(wallet["wallet_credits"]) if wallet else 0,
    }
