"""Institution production: Hub inputs -> finished items in institution inventory."""
from __future__ import annotations

import json
import sqlite3

from config_loader import l1_recipes
from services.economy.config import add_economy_ledger
from services.l0.hub import purchase_hub_resources
from services.world_session.constants import SHARED_WORLD_ID


def _recipe_map() -> dict[str, dict]:
    return {r["id"]: r for r in l1_recipes().get("recipes", [])}


def _get_lines(conn: sqlite3.Connection, institution_id: str) -> list[dict]:
    row = conn.execute(
        "SELECT production_lines_json FROM institutions WHERE id = ?",
        (institution_id,),
    ).fetchone()
    if row is None:
        return []
    raw = row["production_lines_json"] or "[]"
    return json.loads(raw)


def _add_inventory(
    conn: sqlite3.Connection,
    institution_id: str,
    item_id: str,
    qty: int,
) -> None:
    conn.execute(
        """
        INSERT INTO institution_inventory (institution_id, item_id, qty, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(institution_id, item_id) DO UPDATE SET
            qty = qty + excluded.qty,
            updated_at = excluded.updated_at
        """,
        (institution_id, item_id, qty),
    )


def get_institution_inventory(conn: sqlite3.Connection, institution_id: str) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT item_id, qty FROM institution_inventory
        WHERE institution_id = ? AND qty > 0
        """,
        (institution_id,),
    ).fetchall()
    return {row["item_id"]: int(row["qty"]) for row in rows}


def consume_institution_inventory(
    conn: sqlite3.Connection,
    institution_id: str,
    item_id: str,
    qty: int,
) -> bool:
    row = conn.execute(
        """
        SELECT qty FROM institution_inventory
        WHERE institution_id = ? AND item_id = ?
        """,
        (institution_id, item_id),
    ).fetchone()
    if row is None or int(row["qty"]) < qty:
        return False
    conn.execute(
        """
        UPDATE institution_inventory
        SET qty = qty - ?, updated_at = datetime('now')
        WHERE institution_id = ? AND item_id = ?
        """,
        (qty, institution_id, item_id),
    )
    return True


def run_institution_production(
    conn: sqlite3.Connection,
    city: str,
    world_id: str = SHARED_WORLD_ID,
) -> dict:
    recipes = _recipe_map()
    institutions = conn.execute(
        """
        SELECT id, kind, production_lines_json FROM institutions
        WHERE city = ? AND world_id = ? AND production_lines_json IS NOT NULL
          AND production_lines_json != '[]'
        """,
        (city, world_id),
    ).fetchall()
    produced_batches = 0
    produced_items = 0
    skipped = 0
    for inst in institutions:
        kind = inst["kind"]
        lines = _get_lines(conn, inst["id"])
        staff = conn.execute(
            "SELECT 1 FROM institution_slots WHERE institution_id = ? LIMIT 1",
            (inst["id"],),
        ).fetchone()
        if staff is None:
            skipped += 1
            continue
        for line in lines:
            if not line.get("enabled", True):
                continue
            recipe_id = line.get("recipe_id", "")
            recipe = recipes.get(recipe_id)
            if recipe is None:
                skipped += 1
                continue
            allowed = recipe.get("allowed_kinds", [])
            if allowed and kind not in allowed:
                skipped += 1
                continue
            daily_batches = int(
                line.get("daily_batches", recipe.get("daily_batches", 1))
            )
            for _ in range(daily_batches):
                ok, _cost, _reason = purchase_hub_resources(
                    conn,
                    city=city,
                    institution_id=inst["id"],
                    inputs=recipe.get("inputs", []),
                    world_id=world_id,
                )
                if not ok:
                    skipped += 1
                    break
                for out in recipe.get("outputs", []):
                    item_id = out["item_id"]
                    qty = int(out.get("qty", 1))
                    _add_inventory(conn, inst["id"], item_id, qty)
                    produced_items += qty
                    add_economy_ledger(
                        conn,
                        account_kind="institution",
                        account_id=inst["id"],
                        amount=qty,
                        entry_type="production",
                        ref_type="item",
                        ref_id=item_id,
                    )
                produced_batches += 1
    return {
        "batches": produced_batches,
        "items": produced_items,
        "skipped": skipped,
    }
