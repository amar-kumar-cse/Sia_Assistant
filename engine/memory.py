"""
engine/memory.py — SQLite Persistent Memory & Semantic Fact Engine for Sia Assistant
Features:
  - Persistent SQLite storage with WAL mode & thread safety
  - Structured User Facts & Knowledge Extraction
  - Forget Mechanism ("forget this / mat yaad rakhna")
  - Context Summarization & History Budgeting
  - Full backward compatibility with module-level helper APIs
"""

import contextlib
import datetime
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "memory.db")
_db_lock = threading.RLock()
_memory_cache_lock = threading.RLock()
_memory_cache: Dict[str, Any] = {
    "personal": {"name": "Amar Kumar", "work": "Nowic Studio"},
    "files": {"resume_path": os.path.join(_BASE_DIR, "assets", "resume.pdf")},
    "user_preferences": {"voice_speed": "1.0"},
}


def _now() -> str:
    return datetime.datetime.now().isoformat()


@contextlib.contextmanager
def _get_db(db_path: Optional[str] = None):
    """Context manager returning a sqlite3 connection with Row factory and busy timeout."""
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _init_db(db_path: Optional[str] = None):
    """Initialize database tables and PRAGMAs."""
    with _db_lock, _get_db(db_path) as conn:
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")

        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                user_message TEXT NOT NULL,
                sia_response TEXT NOT NULL,
                emotion     TEXT DEFAULT 'default',
                intent_type TEXT DEFAULT 'chat',
                latency_ms  REAL DEFAULT 0,
                session_id  TEXT DEFAULT ''
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
            CREATE TABLE IF NOT EXISTS user_facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_key    TEXT UNIQUE,
                category    TEXT DEFAULT 'general',
                fact        TEXT NOT NULL,
                confidence  REAL DEFAULT 1.0,
                source      TEXT DEFAULT 'explicit',
                active      INTEGER DEFAULT 1,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
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

        c.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_event (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type   TEXT NOT NULL,
                ts           TEXT NOT NULL,
                session_id   TEXT,
                metric_value REAL,
                payload_json TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task        TEXT NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)

        # Schema migrations for existing SQLite databases
        try:
            cursor = c.execute("PRAGMA table_info(user_facts)")
            uf_cols = [r[1] for r in cursor.fetchall()]
            if "category" not in uf_cols and uf_cols:
                c.execute("ALTER TABLE user_facts ADD COLUMN category TEXT DEFAULT 'general'")
            if "source" not in uf_cols and uf_cols:
                c.execute("ALTER TABLE user_facts ADD COLUMN source TEXT DEFAULT 'explicit'")

            cursor = c.execute("PRAGMA table_info(todos)")
            td_cols = [r[1] for r in cursor.fetchall()]
            if "updated_at" not in td_cols and td_cols:
                c.execute("ALTER TABLE todos ADD COLUMN updated_at TEXT DEFAULT ''")
        except Exception as e:
            print(f"[Memory Migration Error]: {e}")

        conn.commit()




_init_db()


# ── SiaMemory Instance Class ──────────────────────────────────────────

class SiaMemory:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _DB_PATH
        _init_db(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Conversations ─────────────────────────────────────────
    def save_conversation(
        self,
        user_msg: str,
        response: str,
        emotion: str = "default",
        intent_type: str = "chat",
        latency_ms: float = 0.0,
        session_id: str = "",
    ):
        with _db_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations "
                "(timestamp, user_message, sia_response, emotion, intent_type, latency_ms, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (_now(), user_msg, response, emotion, intent_type, latency_ms, session_id),
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        with _db_lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT user_message, sia_response FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"user_message": r[0], "sia_response": r[1]} for r in reversed(rows)]

    # ── User Profile ──────────────────────────────────────────
    def set_profile(self, key: str, value: str):
        with _db_lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, str(value), _now()),
            )
            conn.commit()

    def get_profile(self, key: str) -> Optional[str]:
        with _db_lock, self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    # ── User Facts & Memory ──────────────────────────────────
    def save_fact(
        self,
        fact: str,
        fact_key: Optional[str] = None,
        category: str = "general",
        confidence: float = 1.0,
        source: str = "user",
    ) -> bool:
        key = fact_key or f"fact_{int(datetime.datetime.now().timestamp() * 1000)}"
        now = _now()
        with _db_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO user_facts (fact_key, category, fact, confidence, source, active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(fact_key) DO UPDATE SET "
                "fact=excluded.fact, confidence=excluded.confidence, updated_at=excluded.updated_at, active=1",
                (key, category, fact, confidence, source, now, now),
            )
            conn.commit()
        return True

    def get_facts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with _db_lock, self._connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT fact_key, category, fact, confidence, source FROM user_facts WHERE active=1 AND category=? ORDER BY id ASC",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT fact_key, category, fact, confidence, source FROM user_facts WHERE active=1 ORDER BY id ASC"
                ).fetchall()
        return [dict(r) for r in rows]

    def forget_fact(self, query: str) -> int:
        """Forget/Deactivate facts matching query keyword."""
        q = f"%{query.strip()}%"
        with _db_lock, self._connect() as conn:
            cursor = conn.execute(
                "UPDATE user_facts SET active=0, updated_at=? WHERE (fact LIKE ? OR fact_key LIKE ? OR category LIKE ?) AND active=1",
                (_now(), q, q, q),
            )
            count = cursor.rowcount
            conn.commit()
        return count

    # ── Context & Rolling Summarization ──────────────────────
    def get_summarized_context(self, history_limit: int = 10) -> str:
        facts = self.get_facts()
        history = self.get_recent_history(limit=history_limit)

        parts = []
        if facts:
            parts.append("USER FACTS & PREFERENCES:")
            for f in facts:
                parts.append(f"- [{f.get('category', 'general').upper()}] {f.get('fact')}")

        if history:
            parts.append("\nRECENT CONVERSATION HISTORY:")
            for h in history:
                parts.append(f"User: {h.get('user_message')}\nSia: {h.get('sia_response')}")

        return "\n".join(parts)

    def save_vision(self, description: str, triggered_by: str = "auto"):
        with _db_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO vision_log (timestamp, description, triggered_by) VALUES (?, ?, ?)",
                (_now(), description, triggered_by),
            )
            conn.commit()

    def cleanup_old(self, days: int = 30):
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with _db_lock, self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM vision_log WHERE timestamp < ?", (cutoff,))
            conn.commit()


# Default global instance
_memory_instance = SiaMemory()


# ── Module-Level API Helper Functions for Legacy Compatibility ──────────

def load_memory() -> Dict[str, Any]:
    """Returns an isolated deep copy of in-memory JSON cache dict."""
    import copy
    with _memory_cache_lock:
        return copy.deepcopy(_memory_cache)


def save_memory(data: Dict[str, Any]):
    """Saves to in-memory JSON cache dict."""
    import copy
    with _memory_cache_lock:
        global _memory_cache
        _memory_cache = copy.deepcopy(data)


def add_user_fact(key: str, value: str, confidence: float = 1.0, source: str = "explicit") -> bool:
    return _memory_instance.save_fact(fact=value, fact_key=key, confidence=confidence, source=source)


def learn_fact(fact: str, fact_key: Optional[str] = None, category: str = "general", confidence: float = 1.0, source: str = "user") -> bool:
    return _memory_instance.save_fact(fact=fact, fact_key=fact_key, category=category, confidence=confidence, source=source)


def reinforce_fact(key: str) -> bool:
    with _db_lock, _get_db() as conn:
        conn.execute("UPDATE user_facts SET confidence = MIN(1.0, confidence + 0.1), updated_at=? WHERE fact_key=? OR fact LIKE ?", (_now(), key, f"%{key}%"))
        conn.commit()
    return True


def get_user_fact(key: str) -> Optional[Dict[str, Any]]:
    with _db_lock, _get_db() as conn:
        row = conn.execute("SELECT fact_key, category, fact, confidence, source FROM user_facts WHERE (fact_key=? OR fact LIKE ?) AND active=1", (key, f"%{key}%")).fetchone()
    return dict(row) if row else None


def get_facts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    return _memory_instance.get_facts(category=category)



def set_preference(key: str, value: str):
    _memory_instance.set_profile(key, value)
    with _memory_cache_lock:
        _memory_cache.setdefault("user_preferences", {})[key] = value


def get_preference(key: str) -> Optional[str]:
    val = _memory_instance.get_profile(key)
    if val is not None:
        return val
    with _memory_cache_lock:
        return _memory_cache.get("user_preferences", {}).get(key)


def log_telemetry(event_type: str, data: Dict[str, Any]) -> bool:
    with _db_lock, _get_db() as conn:
        conn.execute(
            "INSERT INTO telemetry_event (event_type, ts, session_id, metric_value, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                event_type,
                _now(),
                data.get("session_id", ""),
                data.get("metric_value", 0.0),
                json.dumps(data),
            ),
        )
        conn.commit()
    return True


def save_conversation(session_id: str, user_msg: str, response: str, emotion: str = "default", intent_type: str = "chat", latency_ms: float = 0):
    _memory_instance.save_conversation(user_msg, response, emotion, intent_type, latency_ms, session_id)
    return True


def get_context_for_prompt() -> str:
    return _memory_instance.get_summarized_context()


def get_weekly_stats() -> Dict[str, Any]:
    with _db_lock, _get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt, AVG(latency_ms) as avg_lat FROM conversations").fetchone()
        count = row["cnt"] if row else 0
        avg_lat = row["avg_lat"] if row and row["avg_lat"] is not None else 0.0
    return {"conversations_count": count, "avg_latency_ms": avg_lat, "status": "ok"}


def add_todo(task: str) -> bool:
    with _db_lock, _get_db() as conn:
        now = _now()
        conn.execute("INSERT INTO todos (task, status, created_at, updated_at) VALUES (?, 'done', ?, ?)", (task, now, now))
        conn.commit()
    return True


def _get_default_resume_path() -> str:
    """Dynamic resolution of default resume file path."""
    return os.path.join(_BASE_DIR, "assets", "resume.pdf")


def forget_fact(query: str) -> int:
    return _memory_instance.forget_fact(query)



def prune_memory() -> Dict[str, int]:
    with _db_lock, _get_db() as conn:
        c1 = conn.execute("UPDATE user_facts SET active=0 WHERE confidence < 0.3 AND active=1").rowcount
        c2 = conn.execute("DELETE FROM todos WHERE status='done'").rowcount
        conn.commit()
    return {"facts": c1, "todos": c2}


def cleanup_retention_policy(days: int = 30):
    """Purge historical conversation logs and vision logs older than retention limit."""
    _memory_instance.cleanup_old(days=days)
    return True


def extract_and_save_facts(user_msg: str, sia_response: str) -> bool:
    """Extract structured facts (names, preferences, routine) from dialogue and persist to SQLite user_facts."""
    if not user_msg:
        return False
    u = user_msg.lower()
    if "mera naam" in u or "my name is" in u:
        name = user_msg.split("is")[-1] if "is" in user_msg else user_msg.split("naam")[-1]
        learn_fact(fact=f"User's name is {name.strip()}", fact_key="user_name", category="personal")
    elif "mujhe" in u and "pasand" in u:
        learn_fact(fact=user_msg.strip(), category="preference")
    elif "i work at" in u or "main kaam karta hoon" in u:
        learn_fact(fact=user_msg.strip(), category="work")
    return True


