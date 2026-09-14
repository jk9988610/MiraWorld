from __future__ import annotations

import json
import random
import sqlite3
from datetime import UTC, datetime

from config_loader import items
from db import db, utc_now
from services.economy.config import (
    add_economy_ledger,
    max_purchases_per_group,
    min_subsidy,
    min_wage,
    welfare_grant,
)
from services.economy.market_orders import place_market_order
from services.economy.procurement import run_institution_procurement
from services.economy.production import run_institution_production
from services.l0.hub import get_hub_status, run_l0_tick


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _item_tag_map() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for item in items().get("items", []):
        result[item["id"]] = set(item.get("tags", []))
    return result


def _offer_score(offer: dict, pref: dict[str, float], tag_map: dict[str, set[str]]) -> float:
    gives = offer.get("gives", {})
    item_id = gives.get("item_id", "")
    tags = tag_map.get(item_id, set())
    score = float(pref.get("other", 0.05))
    for tag in tags:
        score += float(pref.get(tag, 0.0))
    price = max(int(offer.get("price_credits", 1)), 1)
    return score / price


def _affordable_offers(conn: sqlite3.Connection, city: str, wallet: int) -> list[dict]:
    from services.catalog import active_offers

    offers = [
        o
        for o in active_offers(city, conn=conn)
        if int(o.get("price_credits", 0)) <= wallet
        and o.get("active", True)
    ]
    return offers


def _run_payroll(conn: sqlite3.Connection, city: str) -> dict:
    floor = min_wage()
    paid_groups = 0
    total_paid = 0
    underpaid = 0
    groups = conn.execute(
        """
        SELECT id, headcount, primary_institution_id, job_type
        FROM pop_groups
        WHERE city = ? AND primary_institution_id IS NOT NULL
        """,
        (city,),
    ).fetchall()
    for group in groups:
        inst_id = group["primary_institution_id"]
        slot = conn.execute(
            """
            SELECT wage_per_capita FROM institution_slots
            WHERE institution_id = ? AND job_type = ?
            LIMIT 1
            """,
            (inst_id, group["job_type"]),
        ).fetchone()
        wage = floor
        if slot:
            wage = max(int(slot["wage_per_capita"]), floor)
        owed = wage * int(group["headcount"])
        inst = conn.execute(
            "SELECT wallet_credits FROM institutions WHERE id = ?",
            (inst_id,),
        ).fetchone()
        if inst is None:
            continue
        available = int(inst["wallet_credits"])
        pay = min(available, owed)
        if pay <= 0:
            underpaid += 1
            continue
        now = utc_now()
        conn.execute(
            "UPDATE institutions SET wallet_credits = wallet_credits - ? WHERE id = ?",
            (pay, inst_id),
        )
        conn.execute(
            "UPDATE pop_groups SET wallet_credits = wallet_credits + ?, updated_at = ? WHERE id = ?",
            (pay, now, group["id"]),
        )
        add_economy_ledger(
            conn,
            account_kind="institution",
            account_id=inst_id,
            amount=-pay,
            entry_type="payroll",
            ref_type="pop_group",
            ref_id=group["id"],
        )
        add_economy_ledger(
            conn,
            account_kind="pop_group",
            account_id=group["id"],
            amount=pay,
            entry_type="payroll",
            ref_type="institution",
            ref_id=inst_id,
        )
        paid_groups += 1
        total_paid += pay
        if pay < owed:
            underpaid += 1
    return {"paid_groups": paid_groups, "total_paid": total_paid, "underpaid": underpaid}


def _run_welfare(conn: sqlite3.Connection, city: str, tick_date: str) -> dict:
    grant_amount = welfare_grant()
    fund = conn.execute(
        "SELECT balance, last_grant_date FROM city_welfare_fund WHERE city = ?",
        (city,),
    ).fetchone()
    if fund is None:
        now = utc_now()
        conn.execute(
            """
            INSERT INTO city_welfare_fund (city, balance, last_grant_date, updated_at)
            VALUES (?, 0, NULL, ?)
            """,
            (city, now),
        )
        fund = conn.execute(
            "SELECT balance, last_grant_date FROM city_welfare_fund WHERE city = ?",
            (city,),
        ).fetchone()

    granted = 0
    if fund and fund["last_grant_date"] != tick_date:
        now = utc_now()
        conn.execute(
            """
            UPDATE city_welfare_fund
            SET balance = balance + ?, last_grant_date = ?, updated_at = ?
            WHERE city = ?
            """,
            (grant_amount, tick_date, now, city),
        )
        add_economy_ledger(
            conn,
            account_kind="welfare_fund",
            account_id=city,
            amount=grant_amount,
            entry_type="grant",
            ref_type="city",
            ref_id=tick_date,
        )
        granted = grant_amount

    subsidy_rate = min_subsidy()
    subsidized = 0
    total_subsidy = 0
    groups = conn.execute(
        """
        SELECT id, headcount FROM pop_groups
        WHERE city = ? AND primary_institution_id IS NULL
        """,
        (city,),
    ).fetchall()
    for group in groups:
        owed = subsidy_rate * int(group["headcount"])
        fund_row = conn.execute(
            "SELECT balance FROM city_welfare_fund WHERE city = ?",
            (city,),
        ).fetchone()
        if fund_row is None or int(fund_row["balance"]) < owed:
            continue
        now = utc_now()
        conn.execute(
            "UPDATE city_welfare_fund SET balance = balance - ?, updated_at = ? WHERE city = ?",
            (owed, now, city),
        )
        conn.execute(
            "UPDATE pop_groups SET wallet_credits = wallet_credits + ?, updated_at = ? WHERE id = ?",
            (owed, now, group["id"]),
        )
        add_economy_ledger(
            conn,
            account_kind="welfare_fund",
            account_id=city,
            amount=-owed,
            entry_type="subsidy",
            ref_type="pop_group",
            ref_id=group["id"],
        )
        add_economy_ledger(
            conn,
            account_kind="pop_group",
            account_id=group["id"],
            amount=owed,
            entry_type="subsidy",
            ref_type="welfare_fund",
            ref_id=city,
        )
        subsidized += 1
        total_subsidy += owed

    fund_balance = conn.execute(
        "SELECT balance FROM city_welfare_fund WHERE city = ?",
        (city,),
    ).fetchone()
    return {
        "granted": granted,
        "subsidized_groups": subsidized,
        "total_subsidy": total_subsidy,
        "fund_balance": int(fund_balance["balance"]) if fund_balance else 0,
    }


def _run_purchases(conn: sqlite3.Connection, city: str, rng: random.Random) -> dict:
    tag_map = _item_tag_map()
    max_n = max_purchases_per_group()
    orders: list[dict] = []
    groups = conn.execute(
        """
        SELECT id, wallet_credits, pref_json FROM pop_groups
        WHERE city = ? AND wallet_credits > 0
        ORDER BY wallet_credits DESC
        """,
        (city,),
    ).fetchall()
    for group in groups:
        wallet = int(group["wallet_credits"])
        pref = json.loads(group["pref_json"] or "{}")
        purchases = 0
        while purchases < max_n:
            offers = _affordable_offers(conn, city, wallet)
            if not offers:
                break
            offers.sort(key=lambda o: _offer_score(o, pref, tag_map), reverse=True)
            placed = place_market_order(
                conn,
                buyer_kind="pop_group",
                buyer_group_id=group["id"],
                buyer_institution_id=None,
                offer=offers[0],
                rng=rng,
            )
            if placed is None:
                break
            orders.append(placed)
            purchases += 1
            wallet -= int(placed["price"])
    return {"orders": len(orders), "details": orders[:20]}


def run_daily_tick(city: str = "潮灯市", *, force: bool = False) -> dict:
    tick_date = _today()
    rng = random.Random(f"{city}:{tick_date}")

    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM economy_ticks WHERE city = ? AND tick_date = ?",
            (city, tick_date),
        ).fetchone()
        if existing and not force:
            return {
                "ok": False,
                "reason": "already_ran",
                "city": city,
                "tick_date": tick_date,
            }

        l0 = run_l0_tick(conn, city)
        production = run_institution_production(conn, city)
        payroll = _run_payroll(conn, city)
        welfare = _run_welfare(conn, city, tick_date)
        purchases = _run_purchases(conn, city, rng)
        procurement = run_institution_procurement(conn, city, rng)

        summary = {
            "l0": l0,
            "production": production,
            "payroll": payroll,
            "welfare": welfare,
            "purchases": {"count": purchases["orders"]},
            "procurement": {"count": procurement["orders"]},
        }
        now = utc_now()
        if existing:
            conn.execute(
                """
                UPDATE economy_ticks
                SET status = 'done', summary_json = ?, created_at = ?
                WHERE city = ? AND tick_date = ?
                """,
                (json.dumps(summary, ensure_ascii=False), now, city, tick_date),
            )
        else:
            conn.execute(
                """
                INSERT INTO economy_ticks (city, tick_date, status, summary_json, created_at)
                VALUES (?, ?, 'done', ?, ?)
                """,
                (city, tick_date, json.dumps(summary, ensure_ascii=False), now),
            )

    return {
        "ok": True,
        "city": city,
        "tick_date": tick_date,
        "summary": summary,
    }


def get_economy_status(city: str = "潮灯市") -> dict:
    with db() as conn:
        institutions = conn.execute(
            """
            SELECT id, display_name, kind, wallet_credits, open, offer_id
            FROM institutions WHERE city = ?
            ORDER BY id
            """,
            (city,),
        ).fetchall()
        groups = conn.execute(
            """
            SELECT id, headcount, wallet_credits, primary_institution_id,
                   job_type, job_display, satisfaction
            FROM pop_groups WHERE city = ?
            ORDER BY id
            """,
            (city,),
        ).fetchall()
        fund = conn.execute(
            "SELECT balance, last_grant_date FROM city_welfare_fund WHERE city = ?",
            (city,),
        ).fetchone()
        last_tick = conn.execute(
            """
            SELECT tick_date, summary_json, created_at FROM economy_ticks
            WHERE city = ? ORDER BY tick_date DESC LIMIT 1
            """,
            (city,),
        ).fetchone()
        pop_orders = conn.execute(
            """
            SELECT COUNT(*) AS c FROM orders WHERE buyer_kind = 'pop_group' AND city = ?
            """,
            (city,),
        ).fetchone()
        hub = get_hub_status(conn, city)

    employed_count = sum(1 for g in groups if g["primary_institution_id"])
    unemployed_count = len(groups) - employed_count
    employed_wallet = sum(
        int(g["wallet_credits"])
        for g in groups
        if g["primary_institution_id"]
    )
    unemployed_wallet = sum(
        int(g["wallet_credits"])
        for g in groups
        if not g["primary_institution_id"]
    )
    institution_wallet_total = sum(int(i["wallet_credits"]) for i in institutions)

    last_summary = (
        json.loads(last_tick["summary_json"] or "{}") if last_tick else {}
    )
    payroll = last_summary.get("payroll", {})
    welfare = last_summary.get("welfare", {})
    purchases = last_summary.get("purchases", {})
    production = last_summary.get("production", {})
    l0 = last_summary.get("l0", {})

    return {
        "city": city,
        "hub": hub,
        "institutions": [
            {**dict(r), "open": bool(r["open"])} for r in institutions
        ],
        "pop_groups": {
            "count": len(groups),
            "employed_count": employed_count,
            "unemployed_count": unemployed_count,
            "employed_wallet_total": employed_wallet,
            "unemployed_wallet_total": unemployed_wallet,
            "groups": [dict(r) for r in groups],
        },
        "welfare_fund": dict(fund) if fund else None,
        "last_tick": (
            {
                "tick_date": last_tick["tick_date"],
                "summary": last_summary,
                "created_at": last_tick["created_at"],
            }
            if last_tick
            else None
        ),
        "dashboard": {
            "institution_wallet_total": institution_wallet_total,
            "pop_orders_total": int(pop_orders["c"]) if pop_orders else 0,
            "last_payroll_total": int(payroll.get("total_paid", 0)),
            "last_payroll_groups": int(payroll.get("paid_groups", 0)),
            "last_payroll_underpaid": int(payroll.get("underpaid", 0)),
            "last_subsidy_total": int(welfare.get("total_subsidy", 0)),
            "last_subsidy_groups": int(welfare.get("subsidized_groups", 0)),
            "last_welfare_granted": int(welfare.get("granted", 0)),
            "last_purchases": int(purchases.get("count", 0)),
            "last_production_items": int(production.get("items", 0)),
            "last_l0_restocked": int(l0.get("restocked_units", 0)),
            "welfare_fund_balance": int(fund["balance"]) if fund else 0,
        },
        "config": {
            "min_wage": min_wage(),
            "min_subsidy": min_subsidy(),
            "welfare_grant": welfare_grant(),
        },
    }
