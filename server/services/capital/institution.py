from __future__ import annotations

import sqlite3
import uuid

from db import utc_now


def institution_id_for_player(player_id: int) -> str:
    return f"inst_player_{player_id}"


def ensure_player_shop_institution(
    conn: sqlite3.Connection,
    *,
    player_id: int,
    display_name: str,
    city: str = "潮灯市",
    company_id: str | None = None,
) -> str:
    inst_id = institution_id_for_player(player_id)
    now = utc_now()
    existing = conn.execute(
        "SELECT id, company_id FROM institutions WHERE id = ?",
        (inst_id,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO institutions (
                id, city, kind, display_name, owner_kind, owner_id,
                offer_id, wallet_credits, open, company_id, production_lines_json, created_at
            ) VALUES (?, ?, 'player_shop', ?, 'player', ?, NULL, 0, 1, ?, '[]', ?)
            """,
            (
                inst_id,
                city,
                display_name.strip(),
                str(player_id),
                company_id,
                now,
            ),
        )
        return inst_id

    if company_id and not existing["company_id"]:
        conn.execute(
            "UPDATE institutions SET company_id = ?, display_name = ? WHERE id = ?",
            (company_id, display_name.strip(), inst_id),
        )
    elif display_name.strip():
        conn.execute(
            "UPDATE institutions SET display_name = ? WHERE id = ?",
            (display_name.strip(), inst_id),
        )
    return inst_id


def list_company_institutions(conn: sqlite3.Connection, company_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, display_name, kind, wallet_credits, open, owner_kind, owner_id
        FROM institutions
        WHERE company_id = ?
        ORDER BY id
        """,
        (company_id,),
    ).fetchall()
    return [{**dict(row), "open": bool(row["open"])} for row in rows]
