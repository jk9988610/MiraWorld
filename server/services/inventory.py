from __future__ import annotations

import sqlite3

from config_loader import items
from db import db
from schemas.stack import StackEntry, StackListResponse
from services.catalog import item_display


def add_stack(conn: sqlite3.Connection, player_id: int, item_id: str, qty: int) -> None:
    row = conn.execute(
        """
        SELECT qty FROM stacks WHERE player_id = ? AND item_id = ?
        """,
        (player_id, item_id),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO stacks (player_id, item_id, qty) VALUES (?, ?, ?)
            """,
            (player_id, item_id, qty),
        )
    else:
        conn.execute(
            """
            UPDATE stacks SET qty = qty + ? WHERE player_id = ? AND item_id = ?
            """,
            (qty, player_id, item_id),
        )


def list_stacks(player_id: int) -> StackListResponse:
    item_map = {item["id"]: item for item in items().get("items", [])}
    with db() as conn:
        rows = conn.execute(
            """
            SELECT item_id, qty FROM stacks
            WHERE player_id = ? AND qty > 0
            ORDER BY item_id
            """,
            (player_id,),
        ).fetchall()
    stacks: list[StackEntry] = []
    for row in rows:
        meta = item_map.get(row["item_id"], {})
        stacks.append(
            StackEntry(
                item_id=row["item_id"],
                display=meta.get("display", row["item_id"]),
                qty=int(row["qty"]),
                tags=meta.get("tags", []),
            )
        )
    return StackListResponse(stacks=stacks)


def stack_summary(player_id: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT item_id, qty FROM stacks
            WHERE player_id = ? AND qty > 0
            ORDER BY item_id
            """,
            (player_id,),
        ).fetchall()
    return [
        {"item_id": row["item_id"], "display": item_display(row["item_id"]), "qty": int(row["qty"])}
        for row in rows
    ]
