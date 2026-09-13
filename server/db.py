"""SQLite access and schema for 米拉世界 / MiraWorld."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

DATABASE = Path(
    os.environ.get(
        "MIRAWORLD_DB",
        os.environ.get("MIRAWORLD_AUTH_DB", "/var/lib/miraworld/miraworld.db"),
    )
)


def _connect() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _migrate_users(conn: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "users" not in tables:
        return

    cols = _columns(conn, "users")
    if "handle" in cols and "wallet_credits" in cols:
        return

    conn.execute(
        """
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT UNIQUE COLLATE NOCASE,
            password_hash BLOB NOT NULL,
            city TEXT NOT NULL DEFAULT '潮灯市',
            wallet_credits INTEGER NOT NULL DEFAULT 0,
            bio TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    if "display_name" in cols:
        conn.execute(
            """
            INSERT INTO users_new (id, handle, email, password_hash, city, wallet_credits, bio, created_at)
            SELECT
                id,
                COALESCE(NULLIF(trim(display_name), ''), substr(email, 1, instr(email, '@') - 1)),
                email,
                password_hash,
                '潮灯市',
                300,
                '',
                created_at
            FROM users
            """
        )
    else:
        conn.execute(
            """
            INSERT INTO users_new (id, handle, email, password_hash, city, wallet_credits, bio, created_at)
            SELECT id, handle, email, password_hash, city, wallet_credits, bio, created_at
            FROM users
            """
        )
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT UNIQUE COLLATE NOCASE,
                password_hash BLOB NOT NULL,
                city TEXT NOT NULL DEFAULT '潮灯市',
                wallet_credits INTEGER NOT NULL DEFAULT 0,
                bio TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        _migrate_users(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visits (
                player_id INTEGER NOT NULL,
                city TEXT NOT NULL,
                spot_id TEXT NOT NULL DEFAULT '',
                first_at TEXT NOT NULL,
                last_at TEXT NOT NULL,
                PRIMARY KEY (player_id, city, spot_id),
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spot_loot_claims (
                player_id INTEGER NOT NULL,
                city TEXT NOT NULL,
                spot_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (player_id, city, spot_id),
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stacks (
                player_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                qty INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (player_id, item_id),
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                buyer_id INTEGER NOT NULL,
                seller_kind TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                city TEXT NOT NULL,
                offer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                price_credits INTEGER NOT NULL,
                escrow_credits INTEGER NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_player_id INTEGER NOT NULL,
                from_kind TEXT NOT NULL,
                from_id TEXT,
                body TEXT NOT NULL,
                ref_type TEXT,
                ref_id TEXT,
                read_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (to_player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                ref_type TEXT,
                ref_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shops (
                player_id INTEGER PRIMARY KEY,
                display_name TEXT NOT NULL,
                city TEXT NOT NULL DEFAULT '潮灯市',
                open INTEGER NOT NULL DEFAULT 1,
                auto_on INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        shop_cols = _columns(conn, "shops")
        if "auto_on" not in shop_cols:
            conn.execute(
                "ALTER TABLE shops ADD COLUMN auto_on INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_offers (
                id TEXT PRIMARY KEY,
                player_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                qty INTEGER NOT NULL DEFAULT 1,
                price_credits INTEGER NOT NULL,
                display TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bounties (
                id TEXT PRIMARY KEY,
                issuer_id INTEGER NOT NULL,
                worker_id INTEGER,
                city TEXT NOT NULL DEFAULT '潮灯市',
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                price_credits INTEGER NOT NULL,
                escrow_credits INTEGER NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (issuer_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (worker_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
