"""
engine/memory.py — SQLite Persistent Memory for Sia
Bugs fixed:
  - BUG #30: Relative path → Absolute path (db file hamesha project folder mein bane)
  - BUG #31: check_same_thread=False + WAL mode → multiple threads safe concurrent access
"""

import datetime
import os
import sqlite3

# BUG #30 FIX: __file__ se absolute path nikalo — cwd pe depend mat raho
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "memory.db")


class SiaMemory:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _DB_PATH
        self._init_db()

    # ── DB Setup ──────────────────────────────────────────────
    def _init_db(self):
        with self._connect() as conn:
            c = conn.cursor()
            # WAL mode — multiple threads se safe concurrent reads/writes
            c.execute("PRAGMA journal_mode=WAL")

            c.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    sia_response TEXT NOT NULL,
                    emotion     TEXT DEFAULT 'default',
                    intent_type TEXT DEFAULT 'chat'
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS vision_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    description TEXT NOT NULL,
                    triggered_by TEXT DEFAULT 'auto'
                )
            """)
            conn.commit()

    # BUG #31 FIX: check_same_thread=False — thread-safe connections
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    # ── Conversations ─────────────────────────────────────────
    def save_conversation(
        self,
        user_msg: str,
        response: str,
        emotion: str = "default",
        intent_type: str = "chat",
    ):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations "
                "(timestamp, user_message, sia_response, emotion, intent_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (_now(), user_msg, response, emotion, intent_type),
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_message, sia_response FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        # Chronological order (oldest first)
        return [{"user_message": r[0], "sia_response": r[1]} for r in reversed(rows)]

    # ── User Profile ──────────────────────────────────────────
    def set_profile(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, _now()),
            )
            conn.commit()

    def get_profile(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    # ── Vision Log ────────────────────────────────────────────
    def save_vision(self, description: str, triggered_by: str = "auto"):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO vision_log (timestamp, description, triggered_by) VALUES (?, ?, ?)",
                (_now(), description, triggered_by),
            )
            conn.commit()

    # ── Cleanup ───────────────────────────────────────────────
    def cleanup_old(self, days: int = 30):
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM vision_log WHERE timestamp < ?", (cutoff,))
            conn.commit()


def _now() -> str:
    return datetime.datetime.now().isoformat()
