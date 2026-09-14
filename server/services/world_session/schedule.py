from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from db import db, utc_now

DEFAULT_WORK_WINDOWS = [{"dow": [1, 2, 3, 4, 5], "start": "09:00", "end": "18:00"}]


def _parse_json_list(raw: str | None) -> list:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def ensure_schedule(conn, player_id: int) -> None:
    row = conn.execute(
        "SELECT player_id FROM player_schedules WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if row:
        return
    conn.execute(
        """
        INSERT INTO player_schedules (
            player_id, timezone, work_windows_json, holidays_json,
            focus_override, focus_override_until, notify_sound
        ) VALUES (?, 'Asia/Shanghai', ?, '[]', NULL, NULL, 1)
        """,
        (player_id, json.dumps(DEFAULT_WORK_WINDOWS, ensure_ascii=False)),
    )


def get_schedule(player_id: int) -> dict:
    with db() as conn:
        ensure_schedule(conn, player_id)
        row = conn.execute(
            """
            SELECT timezone, work_windows_json, holidays_json, notify_sound,
                   focus_override, focus_override_until
            FROM player_schedules WHERE player_id = ?
            """,
            (player_id,),
        ).fetchone()
    assert row is not None
    return {
        "timezone": row["timezone"],
        "work_windows": _parse_json_list(row["work_windows_json"]),
        "holidays": _parse_json_list(row["holidays_json"]),
        "notify_sound": bool(row["notify_sound"]),
        "_focus_override": row["focus_override"],
        "_focus_override_until": row["focus_override_until"],
    }


def update_schedule(player_id: int, body: dict) -> dict:
    windows = body.get("work_windows") or DEFAULT_WORK_WINDOWS
    holidays = body.get("holidays") or []
    timezone = body.get("timezone") or "Asia/Shanghai"
    notify_sound = 1 if body.get("notify_sound", True) else 0
    with db() as conn:
        ensure_schedule(conn, player_id)
        conn.execute(
            """
            UPDATE player_schedules
            SET timezone = ?, work_windows_json = ?, holidays_json = ?, notify_sound = ?
            WHERE player_id = ?
            """,
            (
                timezone,
                json.dumps(windows, ensure_ascii=False),
                json.dumps(holidays, ensure_ascii=False),
                notify_sound,
                player_id,
            ),
        )
    return get_schedule(player_id)


def _time_minutes(t: str) -> int:
    parts = t.strip().split(":")
    h = int(parts[0]) if parts else 0
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m


def _is_holiday(local_date: datetime.date, holidays: list) -> bool:
    iso = local_date.isoformat()
    for h in holidays:
        if isinstance(h, str) and h == iso:
            return True
    return False


def in_work_window(player_id: int, at: datetime | None = None) -> bool:
    sched = get_schedule(player_id)
    tz = ZoneInfo(sched["timezone"])
    now = at.astimezone(tz) if at else datetime.now(tz)
    if _is_holiday(now.date(), sched["holidays"]):
        return False
    dow = now.isoweekday()
    minutes = now.hour * 60 + now.minute
    for window in sched["work_windows"]:
        if not isinstance(window, dict):
            continue
        days = window.get("dow") or []
        if dow not in days:
            continue
        start = _time_minutes(window.get("start", "09:00"))
        end = _time_minutes(window.get("end", "18:00"))
        if start <= minutes < end:
            return True
    return False


def get_focus(player_id: int) -> dict:
    sched = get_schedule(player_id)
    working = in_work_window(player_id)
    override = sched.get("_focus_override")
    override_until = sched.get("_focus_override_until")
    if override in {"company", "personal"}:
        if override_until:
            try:
                until = datetime.fromisoformat(override_until)
                if until.tzinfo is None:
                    until = until.replace(tzinfo=ZoneInfo("UTC"))
                if datetime.now(ZoneInfo("UTC")) < until.astimezone(ZoneInfo("UTC")):
                    return {
                        "focus": override,
                        "source": "override",
                        "in_work_window": working,
                        "override_until": override_until,
                    }
            except ValueError:
                pass
        else:
            return {
                "focus": override,
                "source": "override",
                "in_work_window": working,
                "override_until": None,
            }
    focus = "company" if working else "personal"
    return {
        "focus": focus,
        "source": "schedule",
        "in_work_window": working,
        "override_until": None,
    }


def set_focus_override(player_id: int, focus: str) -> dict:
    with db() as conn:
        ensure_schedule(conn, player_id)
        conn.execute(
            """
            UPDATE player_schedules
            SET focus_override = ?, focus_override_until = NULL
            WHERE player_id = ?
            """,
            (focus, player_id),
        )
    return get_focus(player_id)


def enforce_auto_off_if_off_hours(player_id: int) -> bool:
    """Turn off auto_on outside work window. Returns True if changed."""
    if in_work_window(player_id):
        return False
    with db() as conn:
        row = conn.execute(
            "SELECT auto_on FROM shops WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if row is None or not row["auto_on"]:
            return False
        conn.execute(
            "UPDATE shops SET auto_on = 0 WHERE player_id = ?",
            (player_id,),
        )
    return True
