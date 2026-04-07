"""
Database module for Meridian API.
Handles SQLite connection pooling and schema initialization.
"""

import sqlite3
import os

from config import DB_PATH


# ============================================================
# DATABASE CONNECTION
# ============================================================
def get_db():
    """Get a new database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema. Recreates DB if corrupted."""
    try:
        conn = get_db()
        conn.execute("PRAGMA integrity_check")
        conn.close()
    except Exception:
        print(f"  DB corrompue, recréation: {DB_PATH}")
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS memos (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            company_name TEXT NOT NULL,
            quarter TEXT NOT NULL,
            title TEXT NOT NULL,
            transcript_excerpt TEXT,
            analysis TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_memos_user ON memos(user_id);
        CREATE INDEX IF NOT EXISTS idx_memos_ticker ON memos(ticker);
    """)
    conn.commit()
    conn.close()
