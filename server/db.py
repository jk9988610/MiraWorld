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
                kind TEXT NOT NULL DEFAULT 'buy',
                item_id TEXT NOT NULL DEFAULT '',
                item_display TEXT NOT NULL DEFAULT '',
                qty INTEGER NOT NULL DEFAULT 1,
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
        bounty_cols = _columns(conn, "bounties")
        if "kind" not in bounty_cols:
            conn.execute("ALTER TABLE bounties ADD COLUMN kind TEXT NOT NULL DEFAULT 'buy'")
        if "item_id" not in bounty_cols:
            conn.execute("ALTER TABLE bounties ADD COLUMN item_id TEXT NOT NULL DEFAULT ''")
        if "item_display" not in bounty_cols:
            conn.execute("ALTER TABLE bounties ADD COLUMN item_display TEXT NOT NULL DEFAULT ''")
        if "qty" not in bounty_cols:
            conn.execute("ALTER TABLE bounties ADD COLUMN qty INTEGER NOT NULL DEFAULT 1")

        _migrate_orders_v20(conn)
        _create_economy_tables(conn)
        _run_v20_p3_migrations(conn)
        _create_v21_capital_tables(conn)
        _seed_economy_if_empty(conn)


def _migrate_orders_v20(conn: sqlite3.Connection) -> None:
    cols = _columns(conn, "orders")
    if "buyer_kind" in cols:
        return
    conn.execute(
        """
        CREATE TABLE orders_v20 (
            id TEXT PRIMARY KEY,
            buyer_kind TEXT NOT NULL DEFAULT 'player',
            buyer_id INTEGER,
            buyer_group_id TEXT,
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
        INSERT INTO orders_v20 (
            id, buyer_kind, buyer_id, buyer_group_id, seller_kind, seller_id, city,
            offer_id, status, price_credits, escrow_credits, payload_json,
            created_at, updated_at
        )
        SELECT
            id, 'player', buyer_id, NULL, seller_kind, seller_id, city,
            offer_id, status, price_credits, escrow_credits, payload_json,
            created_at, updated_at
        FROM orders
        """
    )
    conn.execute("DROP TABLE orders")
    conn.execute("ALTER TABLE orders_v20 RENAME TO orders")


def _create_economy_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS institutions (
            id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            kind TEXT NOT NULL,
            display_name TEXT NOT NULL,
            owner_kind TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            offer_id TEXT,
            wallet_credits INTEGER NOT NULL DEFAULT 0,
            open INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS institution_slots (
            id TEXT PRIMARY KEY,
            institution_id TEXT NOT NULL,
            job_type TEXT NOT NULL,
            job_display TEXT NOT NULL,
            headcount INTEGER NOT NULL DEFAULT 1,
            wage_per_capita INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pop_groups (
            id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            headcount INTEGER NOT NULL DEFAULT 1000,
            wallet_credits INTEGER NOT NULL DEFAULT 0,
            primary_institution_id TEXT,
            job_type TEXT,
            job_display TEXT,
            pref_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (primary_institution_id) REFERENCES institutions(id) ON DELETE SET NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS city_welfare_fund (
            city TEXT PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            last_grant_date TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS economy_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_kind TEXT NOT NULL,
            account_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            ref_type TEXT,
            ref_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS spotlight_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institution_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            job_display TEXT NOT NULL,
            pop_group_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE,
            FOREIGN KEY (pop_group_id) REFERENCES pop_groups(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS economy_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            tick_date TEXT NOT NULL,
            status TEXT NOT NULL,
            summary_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE (city, tick_date)
        )
        """
    )


def _ensure_app_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def _meta_done(conn: sqlite3.Connection, key: str) -> bool:
    row = conn.execute("SELECT 1 FROM app_meta WHERE key = ?", (key,)).fetchone()
    return row is not None


def _meta_set(conn: sqlite3.Connection, key: str, value: str = "1") -> None:
    conn.execute(
        "INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
        (key, value),
    )


def _run_v20_p3_migrations(conn: sqlite3.Connection) -> None:
    _ensure_app_meta(conn)
    if not _meta_done(conn, "spotlight_flush_v3"):
        conn.execute("DELETE FROM spotlight_entries")
        _meta_set(conn, "spotlight_flush_v3")
    if not _meta_done(conn, "pop_unemployed_pg09_pg10"):
        conn.execute(
            """
            UPDATE pop_groups
            SET primary_institution_id = NULL,
                job_type = NULL,
                job_display = NULL,
                updated_at = ?
            WHERE id IN ('pg_09', 'pg_10')
            """,
            (utc_now(),),
        )
        _meta_set(conn, "pop_unemployed_pg09_pg10")


def _create_v21_capital_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            owner_player_id INTEGER NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            city TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (owner_player_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS player_daily_grants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            grant_date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            asset_total INTEGER NOT NULL,
            asset_pct REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (player_id, grant_date),
            FOREIGN KEY (player_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    shop_cols = _columns(conn, "shops")
    if "company_id" not in shop_cols:
        conn.execute("ALTER TABLE shops ADD COLUMN company_id TEXT")


def _seed_economy_if_empty(conn: sqlite3.Connection) -> None:
    from services.economy.seed import seed_economy

    seed_economy(conn)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
