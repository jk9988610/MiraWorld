from __future__ import annotations

import json
import sqlite3
import uuid

from db import db, utc_now
from fastapi import HTTPException
from services.world_session.constants import DEFAULT_CITY, SHARED_WORLD_ID
from services.world_session.schedule import ensure_schedule
from services.world_session.multi_clock import get_multi_clock


def _save_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "scope": row["scope"],
        "display_name": row["display_name"],
        "ironman": bool(row["ironman"]),
        "world_day": int(row["world_day"]),
        "speed": row["speed"],
        "last_played_at": row["last_played_at"],
        "created_at": row["created_at"],
    }


def _list_saves(conn: sqlite3.Connection, player_id: int, scope: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, scope, display_name, ironman, world_day, speed,
               last_played_at, created_at
        FROM world_saves
        WHERE player_id = ? AND scope = ?
        ORDER BY last_played_at DESC
        """,
        (player_id, scope),
    ).fetchall()
    return [_save_row(r) for r in rows]


def _last_save_id(saves: list[dict]) -> str | None:
    return saves[0]["id"] if saves else None


def _multi_world_day(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        ("multi_clock_day",),
    ).fetchone()
    if row is not None:
        return max(1, int(row["value"]))
    count = conn.execute(
        """
        SELECT COUNT(*) AS c FROM economy_ticks
        WHERE city = ? AND world_id = ?
        """,
        (DEFAULT_CITY, SHARED_WORLD_ID),
    ).fetchone()
    return max(1, int(count["c"]) + 1 if count else 1)


def get_gate_status(player_id: int, handle: str) -> dict:
    with db() as conn:
        solo = _list_saves(conn, player_id, "solo")
        multi = _list_saves(conn, player_id, "multi")
        session = conn.execute(
            """
            SELECT s.id, s.scope, s.display_name, s.ironman, s.world_day, s.speed,
                   s.last_played_at, s.created_at
            FROM player_sessions ps
            JOIN world_saves s ON s.id = ps.active_save_id
            WHERE ps.player_id = ?
            """,
            (player_id,),
        ).fetchone()
        active = _save_row(session) if session else None

    return {
        "can_continue_solo": bool(solo),
        "can_load_solo": bool(solo),
        "can_new_solo": True,
        "can_continue_multi": bool(multi),
        "can_load_multi": bool(multi),
        "can_new_multi": not bool(multi),
        "last_solo_save_id": _last_save_id(solo),
        "last_multi_save_id": _last_save_id(multi),
        "solo_saves": solo,
        "multi_saves": multi,
        "active_session": active,
    }


def get_session(player_id: int) -> dict:
    with db() as conn:
        row = conn.execute(
            """
            SELECT s.id, s.scope, s.display_name, s.ironman, s.world_day, s.speed,
                   s.last_played_at, s.created_at
            FROM player_sessions ps
            JOIN world_saves s ON s.id = ps.active_save_id
            WHERE ps.player_id = ?
            """,
            (player_id,),
        ).fetchone()
    if row is None:
        return {"active": False, "save": None}
    return {"active": True, "save": _save_row(row)}


def _activate(conn: sqlite3.Connection, player_id: int, save_id: str) -> None:
    conn.execute(
        "UPDATE world_saves SET active = 0 WHERE player_id = ?",
        (player_id,),
    )
    now = utc_now()
    conn.execute(
        """
        UPDATE world_saves
        SET active = 1, last_played_at = ?
        WHERE id = ? AND player_id = ?
        """,
        (now, save_id, player_id),
    )
    conn.execute(
        """
        INSERT INTO player_sessions (player_id, active_save_id, entered_at)
        VALUES (?, ?, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            active_save_id = excluded.active_save_id,
            entered_at = excluded.entered_at
        """,
        (player_id, save_id, now),
    )
    ensure_schedule(conn, player_id)


def _get_save(conn: sqlite3.Connection, player_id: int, save_id: str) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT id, scope, display_name, ironman, world_day, speed, player_id
        FROM world_saves WHERE id = ? AND player_id = ?
        """,
        (save_id, player_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="找不到这个存档")
    return row


def create_new_save(
    player_id: int,
    handle: str,
    scope: str,
    display_name: str = "",
    ironman: bool = False,
) -> dict:
    if scope == "multi":
        ironman = True
    name = (display_name or "").strip() or (
        f"{handle}的多人档" if scope == "multi" else f"{handle}的单人档"
    )
    save_id = f"wsave_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    world_id = SHARED_WORLD_ID if scope == "multi" else f"solo_{uuid.uuid4().hex[:10]}"
    with db() as conn:
        if scope == "multi":
            existing = conn.execute(
                "SELECT id FROM world_saves WHERE player_id = ? AND scope = 'multi'",
                (player_id,),
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="已有多人模式存档，请用继续或加载")
        world_day = _multi_world_day(conn) if scope == "multi" else 1
        conn.execute(
            """
            INSERT INTO world_saves (
                id, player_id, scope, display_name, ironman, world_id,
                world_day, speed, active, last_played_at, created_at, snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'mid', 0, ?, ?, '{}')
            """,
            (
                save_id,
                player_id,
                scope,
                name[:32],
                1 if ironman else 0,
                world_id,
                world_day,
                now,
                now,
            ),
        )
        if scope == "solo":
            seed_solo_world(conn, world_id)
        _activate(conn, player_id, save_id)
        row = conn.execute(
            """
            SELECT id, scope, display_name, ironman, world_day, speed,
                   last_played_at, created_at
            FROM world_saves WHERE id = ?
            """,
            (save_id,),
        ).fetchone()
    assert row is not None
    return _save_row(row)


def continue_save(player_id: int, scope: str) -> dict:
    with db() as conn:
        row = conn.execute(
            """
            SELECT id FROM world_saves
            WHERE player_id = ? AND scope = ?
            ORDER BY last_played_at DESC LIMIT 1
            """,
            (player_id, scope),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="没有可继续的存档")
        _activate(conn, player_id, row["id"])
        save = conn.execute(
            """
            SELECT id, scope, display_name, ironman, world_day, speed,
                   last_played_at, created_at
            FROM world_saves WHERE id = ?
            """,
            (row["id"],),
        ).fetchone()
    assert save is not None
    return _save_row(save)


def load_save(player_id: int, scope: str, save_id: str) -> dict:
    with db() as conn:
        row = _get_save(conn, player_id, save_id)
        if row["scope"] != scope:
            raise HTTPException(status_code=400, detail="存档模式不匹配")
        _activate(conn, player_id, save_id)
        save = conn.execute(
            """
            SELECT id, scope, display_name, ironman, world_day, speed,
                   last_played_at, created_at
            FROM world_saves WHERE id = ?
            """,
            (save_id,),
        ).fetchone()
    assert save is not None
    return _save_row(save)


def autosave(player_id: int) -> dict:
    with db() as conn:
        sess = conn.execute(
            "SELECT active_save_id FROM player_sessions WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if sess is None:
            return {"ok": False, "reason": "no_session"}
        save_id = sess["active_save_id"]
        save = _get_save(conn, player_id, save_id)
        world_day = (
            _multi_world_day(conn)
            if save["scope"] == "multi"
            else int(save["world_day"])
        )
        now = utc_now()
        conn.execute(
            """
            UPDATE world_saves
            SET last_played_at = ?, world_day = ?
            WHERE id = ?
            """,
            (now, world_day, save_id),
        )
    return {"ok": True, "save_id": save_id, "world_day": world_day}


def exit_session(player_id: int) -> dict:
    """Autosave and leave the active world session (back to gate)."""
    result = autosave(player_id)
    with db() as conn:
        conn.execute("DELETE FROM player_sessions WHERE player_id = ?", (player_id,))
        conn.execute(
            "UPDATE world_saves SET active = 0 WHERE player_id = ?",
            (player_id,),
        )
    return {"ok": True, "autosaved": bool(result.get("ok")), **{k: v for k, v in result.items() if k != "ok"}}


def manual_save(player_id: int) -> dict:
    with db() as conn:
        sess = conn.execute(
            "SELECT active_save_id FROM player_sessions WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if sess is None:
            raise HTTPException(status_code=400, detail="尚未进入任何模式")
        save = _get_save(conn, player_id, sess["active_save_id"])
        if save["ironman"]:
            raise HTTPException(status_code=403, detail="铁人模式不能手动存档")
        if save["scope"] != "solo":
            raise HTTPException(status_code=400, detail="仅单人非铁人可手动存档")
        now = utc_now()
        conn.execute(
            "UPDATE world_saves SET last_played_at = ? WHERE id = ?",
            (now, save["id"]),
        )
    return {"ok": True, "save_id": save["id"]}


def get_clock(player_id: int) -> dict:
    session = get_session(player_id)
    save = session.get("save")
    if not save:
        return {
            "scope": None,
            "world_day": 1,
            "speed_label": "—",
            "next_tick_hint": None,
        }
    if save["scope"] == "multi":
        clock = get_multi_clock()
        world_day = clock["world_day"]
        speed_map = {"slow": "慢", "mid": "中", "fast": "快", "fastest": "急速", "pause": "暂停"}
        speed_label = speed_map.get(clock["speed"], clock["speed"])
        hint = f"游戏速度：{speed_label} · 现实 {int({'slow': 30, 'mid': 12, 'fast': 6, 'fastest': 3}.get(clock['speed'], 12))} 秒/游戏日"
    else:
        world_day = int(save["world_day"])
        speed_map = {
            "pause": "暂停",
            "slow": "慢",
            "mid": "中",
            "fast": "快",
            "fastest": "极快",
        }
        speed_label = speed_map.get(save["speed"], save["speed"])
        hint = None
    return {
        "scope": save["scope"],
        "world_day": world_day,
        "speed_label": speed_label,
        "next_tick_hint": hint,
    }


def set_speed(player_id: int, speed: str) -> dict:
    with db() as conn:
        sess = conn.execute(
            "SELECT active_save_id FROM player_sessions WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if sess is None:
            raise HTTPException(status_code=400, detail="尚未进入任何模式")
        save = _get_save(conn, player_id, sess["active_save_id"])
        if save["scope"] == "multi":
            raise HTTPException(status_code=400, detail="多人模式速度固定为中速")
        if speed not in {"pause", "slow", "mid", "fast", "fastest"}:
            raise HTTPException(status_code=400, detail="速度无效")
        conn.execute(
            "UPDATE world_saves SET speed = ? WHERE id = ?",
            (speed, save["id"]),
        )
    return get_clock(player_id)
