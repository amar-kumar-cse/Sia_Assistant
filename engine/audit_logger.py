"""
Audit Logger for Sia Assistant System Control & Actions.
Logs executed commands, permissions, timestamp, and results to SQLite memory database.
"""

import sqlite3
import datetime
import threading
import os
from typing import List, Dict, Any, Optional
from .logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "memory.db")
_audit_lock = threading.RLock()


def _now() -> str:
    return datetime.datetime.now().isoformat()


def _init_audit_table():
    with _audit_lock:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    risk_level  TEXT DEFAULT 'ALLOW',
                    status      TEXT DEFAULT 'SUCCESS',
                    details     TEXT DEFAULT '',
                    user_confirmed INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()


_init_audit_table()


def log_action(
    action_name: str,
    risk_level: str = "ALLOW",
    status: str = "SUCCESS",
    details: str = "",
    user_confirmed: bool = False
) -> bool:
    """Log an executed system action into audit trail."""
    with _audit_lock:
        try:
            conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10.0)
            try:
                conn.execute(
                    "INSERT INTO audit_logs (timestamp, action_name, risk_level, status, details, user_confirmed) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (_now(), action_name, risk_level, status, details, 1 if user_confirmed else 0)
                )
                conn.commit()
                logger.info(f"📜 Audit logged: [{risk_level}] {action_name} -> {status}")
                return True
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            return False


def get_recent_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent action audit log history."""
    with _audit_lock:
        try:
            conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10.0)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT timestamp, action_name, risk_level, status, details, user_confirmed "
                    "FROM audit_logs ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
            return []
