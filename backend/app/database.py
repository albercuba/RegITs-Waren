import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings


def _db_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                serial_number TEXT,
                asset_type TEXT,
                vendor TEXT,
                model TEXT,
                received_by TEXT,
                notes TEXT,
                image_path TEXT NOT NULL,
                raw_text TEXT
            )
            """
        )
        _ensure_column(conn, "submissions", "detected_candidates", "TEXT")
        _ensure_column(conn, "submissions", "user_corrected_serial", "TEXT")
        _ensure_column(conn, "submissions", "image_paths", "TEXT")
        _ensure_column(conn, "submissions", "location", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                smtp_host TEXT NOT NULL,
                smtp_port INTEGER NOT NULL,
                smtp_username TEXT,
                smtp_password_encrypted TEXT,
                sender_email TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                use_tls INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "email_settings", "locations", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS serial_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                regex TEXT NOT NULL,
                vendor TEXT,
                base_score INTEGER NOT NULL DEFAULT 10,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_debug (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                image_path TEXT NOT NULL,
                raw_text TEXT,
                normalized_text TEXT,
                barcodes TEXT,
                candidates TEXT,
                best_guess_serial TEXT,
                confidence_score INTEGER,
                fields TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
