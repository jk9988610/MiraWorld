from __future__ import annotations

import sqlite3
import uuid

from db import utc_now


DEFAULT_SLOTS_BY_KIND: dict[str, list[dict]] = {
    "device_plant": [
        {
            "job_type": "engineer",
            "job_display": "工程师",
            "headcount": 2,
            "wage_per_capita": 14,
        },
        {
            "job_type": "qc",
            "job_display": "QC",
            "headcount": 1,
            "wage_per_capita": 12,
        },
    ],
}


def institution_id_for_player(player_id: int) -> str:
    return f"inst_player_{player_id}"


def _active_world_id(conn: sqlite3.Connection, player_id: int) -> str:
    from services.world_session.solo_world import active_world_id

    return active_world_id(conn, player_id)


def list_institution_slots(conn: sqlite3.Connection, institution_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT job_type, job_display, headcount, wage_per_capita
        FROM institution_slots
        WHERE institution_id = ?
        ORDER BY job_type
        """,
        (institution_id,),
    ).fetchall()
    return [
        {
            "job_type": row["job_type"],
            "job_display": row["job_display"],
            "headcount": int(row["headcount"]),
            "wage_per_capita": int(row["wage_per_capita"]),
            "employed_groups": 0,
        }
        for row in rows
    ]


def institution_staff_headcount(conn: sqlite3.Connection, institution_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(headcount), 0) AS n
        FROM institution_slots
        WHERE institution_id = ?
        """,
        (institution_id,),
    ).fetchone()
    return int(row["n"]) if row else 0


def ensure_institution_staff(
    conn: sqlite3.Connection,
    *,
    institution_id: str,
    kind: str,
    city: str,
    world_id: str,
) -> list[dict]:
    templates = DEFAULT_SLOTS_BY_KIND.get(kind, [])
    if not templates:
        return list_institution_slots(conn, institution_id)

    now = utc_now()
    existing = conn.execute(
        "SELECT 1 FROM institution_slots WHERE institution_id = ? LIMIT 1",
        (institution_id,),
    ).fetchone()
    if existing is None:
        for slot in templates:
            conn.execute(
                """
                INSERT INTO institution_slots (
                    id, institution_id, job_type, job_display, headcount,
                    wage_per_capita, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"slot_{uuid.uuid4().hex[:10]}",
                    institution_id,
                    slot["job_type"],
                    slot["job_display"],
                    int(slot["headcount"]),
                    int(slot["wage_per_capita"]),
                    now,
                ),
            )

    slots = list_institution_slots(conn, institution_id)
    for slot in slots:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM pop_groups
            WHERE primary_institution_id = ? AND job_type = ?
            """,
            (institution_id, slot["job_type"]),
        ).fetchone()
        slot["employed_groups"] = int(row["n"]) if row else 0
    return slots


def ensure_player_shop_institution(
    conn: sqlite3.Connection,
    *,
    player_id: int,
    display_name: str,
    city: str = "潮灯市",
    company_id: str | None = None,
    world_id: str | None = None,
) -> str:
    inst_id = institution_id_for_player(player_id)
    now = utc_now()
    world_id = world_id or _active_world_id(conn, player_id)
    existing = conn.execute(
        "SELECT id, company_id FROM institutions WHERE id = ?",
        (inst_id,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO institutions (
                id, world_id, city, kind, display_name, owner_kind, owner_id,
                offer_id, wallet_credits, open, company_id, production_lines_json, created_at
            ) VALUES (?, ?, ?, 'player_shop', ?, 'player', ?, NULL, 0, 1, ?, '[]', ?)
            """,
            (
                inst_id,
                world_id,
                city,
                display_name.strip(),
                str(player_id),
                company_id,
                now,
            ),
        )
        return inst_id

    conn.execute(
        """
        UPDATE institutions
        SET world_id = ?,
            display_name = CASE WHEN ? != '' THEN ? ELSE display_name END,
            company_id = CASE WHEN ? IS NOT NULL AND company_id IS NULL THEN ? ELSE company_id END
        WHERE id = ?
        """,
        (
            world_id,
            display_name.strip(),
            display_name.strip(),
            company_id,
            company_id,
            inst_id,
        ),
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
