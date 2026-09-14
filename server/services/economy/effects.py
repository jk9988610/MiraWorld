"""Buy-and-use effects when market orders settle."""
from __future__ import annotations

import sqlite3

from config_loader import items
from services.economy.config import add_economy_ledger


def _item_def(item_id: str) -> dict | None:
    for item in items().get("items", []):
        if item["id"] == item_id:
            return item
    return None


def apply_pop_satisfy(
    conn: sqlite3.Connection,
    *,
    group_id: str,
    effect: dict,
    qty: int,
) -> int:
    points = int(effect.get("satisfy_points", 0)) * qty
    if points <= 0:
        return 0
    row = conn.execute(
        "SELECT satisfaction FROM pop_groups WHERE id = ?",
        (group_id,),
    ).fetchone()
    current = int(row["satisfaction"]) if row else 0
    new_val = min(100, current + points)
    conn.execute(
        """
        UPDATE pop_groups SET satisfaction = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (new_val, group_id),
    )
    add_economy_ledger(
        conn,
        account_kind="pop_group",
        account_id=group_id,
        amount=points,
        entry_type="effect_apply",
        ref_type="satisfy",
        ref_id=str(new_val),
    )
    return points


def apply_institution_deploy(
    conn: sqlite3.Connection,
    *,
    institution_id: str,
    item_id: str,
    effect: dict,
    qty: int,
    order_id: str,
) -> bool:
    required_kinds = effect.get("required_kinds") or []
    if required_kinds:
        inst = conn.execute(
            "SELECT kind FROM institutions WHERE id = ?",
            (institution_id,),
        ).fetchone()
        if inst is None or inst["kind"] not in required_kinds:
            return False
    limit = int(effect.get("stack_limit", 99))
    row = conn.execute(
        """
        SELECT qty_active FROM institution_deployments
        WHERE institution_id = ? AND item_id = ?
        """,
        (institution_id, item_id),
    ).fetchone()
    current = int(row["qty_active"]) if row else 0
    add_qty = min(qty, max(0, limit - current))
    if add_qty <= 0:
        return False
    conn.execute(
        """
        INSERT INTO institution_deployments (
            institution_id, item_id, qty_active, source_order_id, updated_at
        ) VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(institution_id, item_id) DO UPDATE SET
            qty_active = qty_active + excluded.qty_active,
            source_order_id = excluded.source_order_id,
            updated_at = excluded.updated_at
        """,
        (institution_id, item_id, add_qty, order_id),
    )
    add_economy_ledger(
        conn,
        account_kind="institution",
        account_id=institution_id,
        amount=add_qty,
        entry_type="effect_apply",
        ref_type="deploy",
        ref_id=item_id,
    )
    return True


def resolve_on_acquire(
    conn: sqlite3.Connection,
    *,
    buyer_kind: str,
    buyer_group_id: str | None,
    buyer_institution_id: str | None,
    item_id: str,
    qty: int,
    order_id: str,
) -> dict:
    meta = _item_def(item_id)
    if meta is None:
        return {"applied": False, "reason": "unknown_item"}
    on_acquire = meta.get("on_acquire") or {}
    result: dict = {"applied": False, "item_id": item_id, "qty": qty}

    if buyer_kind == "pop_group" and buyer_group_id:
        effect = on_acquire.get("pop_group")
        if not effect:
            return {**result, "reason": "no_pop_effect"}
        if effect.get("type") == "SATISFY_PREF":
            points = apply_pop_satisfy(conn, group_id=buyer_group_id, effect=effect, qty=qty)
            return {
                **result,
                "applied": points > 0,
                "type": "SATISFY_PREF",
                "points": points,
                "message": meta.get("acquire_message"),
            }

    if buyer_kind == "institution" and buyer_institution_id:
        effect = on_acquire.get("institution")
        if not effect:
            return {**result, "reason": "no_institution_effect"}
        if effect.get("type") == "DEPLOY_INST":
            ok = apply_institution_deploy(
                conn,
                institution_id=buyer_institution_id,
                item_id=item_id,
                effect=effect,
                qty=qty,
                order_id=order_id,
            )
            return {
                **result,
                "applied": ok,
                "type": "DEPLOY_INST",
                "message": meta.get("acquire_message"),
            }

    return {**result, "reason": "buyer_mismatch"}
