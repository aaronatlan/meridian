"""
Database module for Meridian API.
Supporte PostgreSQL (production via DATABASE_URL) et SQLite (local).
"""

import os
from config import DATABASE_URL, USE_POSTGRES, DB_PATH


# ============================================================
# WRAPPER UNIFIÉ (SQLite + PostgreSQL)
# ============================================================
class DBWrapper:
    """Wrapper qui normalise l'interface entre SQLite et PostgreSQL."""

    def __init__(self, conn, is_postgres=False):
        self._conn = conn
        self._is_postgres = is_postgres

    def execute(self, sql, params=None):
        if self._is_postgres:
            import psycopg2.extras
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            sql = sql.replace('?', '%s')
            cur.execute(sql, params or ())
            return cur
        else:
            return self._conn.execute(sql, params or ())

    def executemany(self, sql, params_list):
        if self._is_postgres:
            cur = self._conn.cursor()
            sql = sql.replace('?', '%s')
            cur.executemany(sql, params_list)
        else:
            self._conn.executemany(sql, params_list)

    def executescript(self, sql):
        if self._is_postgres:
            cur = self._conn.cursor()
            for stmt in sql.split(';'):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        else:
            self._conn.executescript(sql)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ============================================================
# CONNEXION
# ============================================================
def get_db():
    """Retourne une connexion DB (PostgreSQL ou SQLite selon l'env)."""
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return DBWrapper(conn, is_postgres=True)
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return DBWrapper(conn, is_postgres=False)


# ============================================================
# INITIALISATION DU SCHÉMA
# ============================================================
def init_db():
    """Initialise le schéma de la base de données."""
    if USE_POSTGRES:
        schema = """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
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
                created_at TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_memos_user ON memos(user_id);
            CREATE INDEX IF NOT EXISTS idx_memos_ticker ON memos(ticker)
        """
    else:
        try:
            import sqlite3
            conn_test = sqlite3.connect(DB_PATH)
            conn_test.execute("PRAGMA integrity_check")
            conn_test.close()
        except Exception:
            print(f"  DB corrompue, recréation: {DB_PATH}")
            try:
                os.remove(DB_PATH)
            except OSError:
                pass
        schema = """
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
            CREATE INDEX IF NOT EXISTS idx_memos_ticker ON memos(ticker)
        """

    conn = get_db()
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"  DB: {'PostgreSQL' if USE_POSTGRES else 'SQLite'} initialisée")
