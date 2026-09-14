"""Shared multiplayer game clock and real-time scheduler."""
from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from db import db, utc_now
from services.economy.tick import run_daily_tick
from services.world_session.constants import DEFAULT_CITY, SHARED_WORLD_ID

# Real seconds per game day, intentionally close to Victoria-style speed controls.
SPEED_SECONDS: dict[str, float] = {
    "slow": 30.0,
    "mid": 12.0,
    "fast": 6.0,
    "fastest": 3.0,
}
DEFAULT_SPEED = "mid"
_CLOCK_DAY = "multi_clock_day"
_CLOCK_LAST_REAL = "multi_clock_last_real"
_CLOCK_SPEED = "multi_clock_speed"
_CLOCK_INIT = "multi_clock_initialized"


def _parse_time(value: str | None) -> float:
    try:
        return datetime.fromisoformat(value or "").timestamp()
    except (TypeError, ValueError, OverflowError):
        return time.time()


def _ensure_clock(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    day_row = conn.execute("SELECT value FROM app_meta WHERE key = ?", (_CLOCK_DAY,)).fetchone()
    if day_row is not None:
        # Multiplayer speed is server-controlled and permanently fixed at mid speed.
        conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_SPEED, DEFAULT_SPEED))
        return
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM economy_ticks WHERE city = ? AND world_id = ?",
        (DEFAULT_CITY, SHARED_WORLD_ID),
    ).fetchone()
    day = max(1, int(count["c"]) + 1)
    now = utc_now()
    conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_DAY, str(day)))
    conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_LAST_REAL, now))
    conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_SPEED, DEFAULT_SPEED))
    conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_INIT, "1"))


def get_multi_clock() -> dict:
    with db() as conn:
        _ensure_clock(conn)
        rows = conn.execute(
            "SELECT key, value FROM app_meta WHERE key IN (?, ?, ?)",
            (_CLOCK_DAY, _CLOCK_LAST_REAL, _CLOCK_SPEED),
        ).fetchall()
    values = {row["key"]: row["value"] for row in rows}
    speed = values.get(_CLOCK_SPEED, DEFAULT_SPEED)
    return {
        "world_day": int(values.get(_CLOCK_DAY, "1")),
        "speed": speed if speed in SPEED_SECONDS else DEFAULT_SPEED,
        "last_real": values.get(_CLOCK_LAST_REAL),
    }


def advance_due_day() -> bool:
    """Claim and execute at most one due shared-world day."""
    with db() as conn:
        _ensure_clock(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        values = {
            row["key"]: row["value"]
            for row in conn.execute(
                "SELECT key, value FROM app_meta WHERE key IN (?, ?, ?)",
                (_CLOCK_DAY, _CLOCK_LAST_REAL, _CLOCK_SPEED),
            ).fetchall()
        }
        speed = values.get(_CLOCK_SPEED, DEFAULT_SPEED)
        interval = SPEED_SECONDS.get(speed)
        if interval is None:
            return False
        now = time.time()
        last = _parse_time(values.get(_CLOCK_LAST_REAL))
        if now - last < interval:
            return False
        day = int(values.get(_CLOCK_DAY, "1"))
        # Claim the day before running the potentially expensive economic tick.
        conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_DAY, str(day + 1)))
        conn.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (_CLOCK_LAST_REAL, utc_now()))

    run_daily_tick(
        DEFAULT_CITY,
        world_id=SHARED_WORLD_ID,
        force=False,
        tick_date=f"game-day-{day:06d}",
    )
    return True


def scheduler_loop(stop: threading.Event) -> None:
    while not stop.wait(1.0):
        try:
            advance_due_day()
        except Exception:
            # The API must remain available if one tick fails; the next poll retries.
            continue


def start_scheduler() -> threading.Event:
    stop = threading.Event()
    thread = threading.Thread(target=scheduler_loop, args=(stop,), name="miraworld-multi-clock", daemon=True)
    thread.start()
    return stop
