from __future__ import annotations

import json

from config_loader import economy_institutions, economy_pop_groups, utopia_economy
from db import utc_now


def utopia_config() -> dict:
    return utopia_economy()


def min_wage() -> int:
    cfg = utopia_config()
    return int(cfg.get("min_wage_per_capita_per_day", 12))


def min_subsidy() -> int:
    cfg = utopia_config()
    return int(cfg.get("min_living_subsidy_per_capita_per_day", 8))


def welfare_grant() -> int:
    cfg = utopia_config()
    return int(cfg.get("city_welfare_grant_per_day", 120000))


def max_purchases_per_group() -> int:
    cfg = utopia_config()
    return int(cfg.get("max_purchases_per_group_per_tick", 5))


def default_pref_json() -> str:
    pref = economy_pop_groups().get("default_pref", {})
    return json.dumps(pref, ensure_ascii=False)


def add_economy_ledger(
    conn,
    *,
    account_kind: str,
    account_id: str,
    amount: int,
    entry_type: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO economy_ledger (
            account_kind, account_id, amount, type, ref_type, ref_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (account_kind, account_id, amount, entry_type, ref_type, ref_id, utc_now()),
    )
