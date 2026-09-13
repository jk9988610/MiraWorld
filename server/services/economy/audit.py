from __future__ import annotations

import json
import sqlite3

from db import db
from services.economy.config import min_subsidy, min_wage


def _check_spotlight(conn: sqlite3.Connection, city: str) -> dict:
    issues: list[str] = []
    rows = conn.execute(
        """
        SELECT se.display_name, se.job_display, se.institution_id, se.pop_group_id
        FROM spotlight_entries se
        JOIN institutions i ON i.id = se.institution_id
        WHERE i.city = ?
        """,
        (city,),
    ).fetchall()
    for row in rows:
        name = row["display_name"]
        job = row["job_display"]
        if name.endswith("先生") or name.endswith("女士"):
            issues.append(f"legacy honorific name: {name}")
        if not name.endswith(job):
            issues.append(f"display_name must be surname+job: {name!r} / {job!r}")
        slot = conn.execute(
            """
            SELECT 1 FROM institution_slots
            WHERE institution_id = ? AND job_display = ?
            LIMIT 1
            """,
            (row["institution_id"], job),
        ).fetchone()
        if slot is None:
            issues.append(f"spotlight job without slot: {job} @ {row['institution_id']}")
        group = conn.execute(
            "SELECT job_display FROM pop_groups WHERE id = ?",
            (row["pop_group_id"],),
        ).fetchone()
        if group is None or group["job_display"] != job:
            issues.append(f"spotlight job mismatch group: {row['pop_group_id']}")
    return {"ok": not issues, "count": len(rows), "issues": issues[:20]}


def _check_wallets(conn: sqlite3.Connection, city: str, last_summary: dict) -> dict:
    issues: list[str] = []
    groups = conn.execute(
        """
        SELECT id, headcount, wallet_credits, primary_institution_id
        FROM pop_groups WHERE city = ?
        """,
        (city,),
    ).fetchall()
    employed = [g for g in groups if g["primary_institution_id"]]
    unemployed = [g for g in groups if not g["primary_institution_id"]]
    wage_floor = min_wage()
    subsidy_rate = min_subsidy()

    payroll = last_summary.get("payroll", {})
    welfare = last_summary.get("welfare", {})

    if employed and int(payroll.get("total_paid", 0)) <= 0:
        issues.append("employed groups exist but last tick paid no payroll")
    if unemployed and int(welfare.get("total_subsidy", 0)) <= 0:
        issues.append("unemployed groups exist but last tick paid no subsidy")

    expected_payroll = wage_floor * sum(int(g["headcount"]) for g in employed)
    actual_payroll = int(payroll.get("total_paid", 0))
    if employed and actual_payroll < expected_payroll:
        if int(payroll.get("underpaid", 0)) == 0:
            issues.append(
                f"payroll below floor: got {actual_payroll}, expected {expected_payroll}"
            )

    expected_subsidy = subsidy_rate * sum(int(g["headcount"]) for g in unemployed)
    actual_subsidy = int(welfare.get("total_subsidy", 0))
    if unemployed and actual_subsidy < expected_subsidy:
        issues.append(
            f"subsidy below floor: got {actual_subsidy}, expected {expected_subsidy}"
        )

    return {
        "ok": not issues,
        "employed_groups": len(employed),
        "unemployed_groups": len(unemployed),
        "employed_wallet_total": sum(int(g["wallet_credits"]) for g in employed),
        "unemployed_wallet_total": sum(int(g["wallet_credits"]) for g in unemployed),
        "last_payroll_total": actual_payroll,
        "expected_payroll_floor": expected_payroll,
        "last_subsidy_total": actual_subsidy,
        "expected_subsidy_floor": expected_subsidy,
        "min_wage": wage_floor,
        "min_subsidy": subsidy_rate,
        "issues": issues,
    }


def _check_ledger(conn: sqlite3.Connection, city: str) -> dict:
    count = conn.execute("SELECT COUNT(*) AS c FROM economy_ledger").fetchone()
    recent = conn.execute(
        """
        SELECT account_kind, account_id, amount, type, created_at
        FROM economy_ledger
        ORDER BY id DESC LIMIT 5
        """
    ).fetchall()
    tick = conn.execute(
        """
        SELECT tick_date, created_at FROM economy_ticks
        WHERE city = ? ORDER BY tick_date DESC LIMIT 1
        """,
        (city,),
    ).fetchone()
    return {
        "ok": int(count["c"]) > 0,
        "entry_count": int(count["c"]),
        "last_tick_date": tick["tick_date"] if tick else None,
        "last_tick_at": tick["created_at"] if tick else None,
        "recent": [dict(r) for r in recent],
    }


def audit_economy(city: str = "潮灯市") -> dict:
    with db() as conn:
        last_tick = conn.execute(
            """
            SELECT tick_date, summary_json FROM economy_ticks
            WHERE city = ? ORDER BY tick_date DESC LIMIT 1
            """,
            (city,),
        ).fetchone()
        last_summary = (
            json.loads(last_tick["summary_json"] or "{}") if last_tick else {}
        )
        spotlight = _check_spotlight(conn, city)
        wallets = _check_wallets(conn, city, last_summary)
        ledger = _check_ledger(conn, city)

    checks = {
        "spotlight": spotlight,
        "wallets": wallets,
        "ledger": ledger,
        "has_last_tick": bool(last_tick),
    }
    ok = (
        spotlight["ok"]
        and wallets["ok"]
        and ledger["ok"]
        and bool(last_tick)
    )
    return {"ok": ok, "city": city, "checks": checks}
