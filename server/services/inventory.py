from __future__ import annotations

import sqlite3

from config_loader import items
from db import db
from fastapi import HTTPException
from schemas.stack import StackEntry, StackListResponse
from services.catalog import item_display
from services.item_actions import can_consume, can_use, get_item


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


def remove_stack(conn: sqlite3.Connection, player_id: int, item_id: str, qty: int = 1) -> int:
    row = conn.execute(
        "SELECT qty FROM stacks WHERE player_id = ? AND item_id = ?",
        (player_id, item_id),
    ).fetchone()
    if row is None or int(row["qty"]) < qty:
        raise HTTPException(status_code=400, detail="背包里没有足够的这个物品")
    new_qty = int(row["qty"]) - qty
    if new_qty <= 0:
        conn.execute(
            "DELETE FROM stacks WHERE player_id = ? AND item_id = ?",
            (player_id, item_id),
        )
        return 0
    conn.execute(
        "UPDATE stacks SET qty = ? WHERE player_id = ? AND item_id = ?",
        (new_qty, player_id, item_id),
    )
    return new_qty


def consume_stack_item(player_id: int, item_id: str) -> dict:
    meta = get_item(item_id)
    tags = meta.get("tags", [])
    if not can_consume(tags):
        raise HTTPException(status_code=400, detail="这个物品不能食用")
    with db() as conn:
        new_qty = remove_stack(conn, player_id, item_id, 1)
    message = meta.get("consume_message") or f"你吃掉了{meta.get('display', item_id)}。"
    return {
        "item_id": item_id,
        "display": meta.get("display", item_id),
        "qty": new_qty,
        "message": message,
    }


def use_stack_item(player_id: int, item_id: str) -> dict:
    meta = get_item(item_id)
    tags = meta.get("tags", [])
    if not can_use(tags):
        raise HTTPException(status_code=400, detail="这个物品不能使用")
    consumes = meta.get("consumes_on_use", True)
    new_qty = -1
    with db() as conn:
        if consumes:
            new_qty = remove_stack(conn, player_id, item_id, 1)
        else:
            row = conn.execute(
                "SELECT qty FROM stacks WHERE player_id = ? AND item_id = ?",
                (player_id, item_id),
            ).fetchone()
            if row is None or int(row["qty"]) < 1:
                raise HTTPException(status_code=400, detail="背包里没有这个物品")
            new_qty = int(row["qty"])
    message = meta.get("use_message") or f"你使用了{meta.get('display', item_id)}。"
    return {
        "item_id": item_id,
        "display": meta.get("display", item_id),
        "qty": new_qty,
        "message": message,
    }


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
