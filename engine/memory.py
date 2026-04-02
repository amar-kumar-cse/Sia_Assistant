import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

import threading

# Adjust the import for config based on refactoring
try:
    import config
    DB_PATH = config.config.DB_PATH
except ImportError:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "memory.db")

# Thread lock for SQLite safety
_db_lock = threading.Lock()

DEFAULT_MEMORY = {
    "personal": {
        "name": "Amar",
        "location": "Roorkee",
        "college": "RIT Roorkee",
        "degree": "B.Tech CSE"
    },
    "preferences": {
        "games": "Offline Gun Shot Games",
        "interests": ["Coding", "Gaming", "Technology"]
    },
    "files": {
        "resume_path": "C:\\Users\\yadav\\OneDrive\\Documents\\Resume.pdf",
        "college_portal": "https://cyborgerp.in/"
    },
    "skills": {
        "languages": ["Python", "Java", "C++"],
        "learning": []
    },
    "routines": {
        "morning": "Wakes up, checks messages",
        "afternoon": "College classes or coding practice",
        "evening": "Gaming or working on projects",
        "night": "Late night coding or watching tutorials"
    },
    "memory_log": []
}

# In-memory cache for instant access
_memory_cache = None
_context_cache = None
_cache_timestamp = None

def _get_db() -> sqlite3.Connection:
    """Returns an active SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db() -> None:
    """Initializes the database schema (including new tables for facts & todos)."""
    with _db_lock, _get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                category TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY(category, key)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                entry TEXT
            )
        ''')
        # NEW: Dynamic user facts learned from conversation
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT UNIQUE,
                timestamp TEXT
            )
        ''')
        # NEW: To-Do list for morning briefing etc.
        conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT,
                status TEXT DEFAULT "pending",
                created_at TEXT,
                completed_at TEXT
            )
        ''')
        
        # Populate defaults if completely empty
        cursor = conn.execute("SELECT count(*) FROM kv_store")
        if cursor.fetchone()[0] == 0:
            for category, data in DEFAULT_MEMORY.items():
                if category == "memory_log":
                    continue
                for k, v in data.items():
                    conn.execute(
                        "INSERT INTO kv_store (category, key, value) VALUES (?, ?, ?)",
                        (category, k, json.dumps(v))
                    )

# Initialize DB on import
_init_db()

def load_memory() -> Dict[str, Any]:
    """Loads memory from SQLite with in-memory caching for instant access."""
    global _memory_cache, _cache_timestamp
    
    # Return cached version if available and recent (< 5 seconds old)
    if _memory_cache is not None and _cache_timestamp:
        if time.time() - _cache_timestamp < 5:
            return _memory_cache.copy()
            
    memory_dict = {cat: {} for cat in DEFAULT_MEMORY.keys() if cat != "memory_log"}
    memory_dict["memory_log"] = []
    
    try:
        with _db_lock, _get_db() as conn:
            rows = conn.execute("SELECT category, key, value FROM kv_store").fetchall()
            for row in rows:
                cat = row["category"]
                key = row["key"]
                if cat not in memory_dict:
                    memory_dict[cat] = {}
                memory_dict[cat][key] = json.loads(row["value"])
                
            logs = conn.execute("SELECT timestamp, entry FROM memory_log ORDER BY id ASC LIMIT 50").fetchall()
            for log in logs:
                memory_dict["memory_log"].append({
                    "timestamp": log["timestamp"], 
                    "entry": log["entry"]
                })
                
        # Fill missing sub-keys from default dict
        for cat, data in DEFAULT_MEMORY.items():
            if cat == "memory_log": continue
            for k, v in data.items():
                if k not in memory_dict.get(cat, {}):
                    if cat not in memory_dict: memory_dict[cat] = {}
                    memory_dict[cat][k] = v
                    
        _memory_cache = memory_dict.copy()
        _cache_timestamp = time.time()
        
        return memory_dict
    except Exception as e:
        print(f"Error loading SQLite memory: {e}")
        return DEFAULT_MEMORY.copy()

def save_memory(memory_data: Dict[str, Any]) -> bool:
    """Saves memory back to SQLite and updates cache."""
    global _memory_cache, _context_cache, _cache_timestamp
    
    try:
        with _db_lock, _get_db() as conn:
            for cat, data in memory_data.items():
                if cat == "memory_log":
                    conn.execute("DELETE FROM memory_log")
                    for log in data[-50:]:
                        conn.execute("INSERT INTO memory_log (timestamp, entry) VALUES (?, ?)", 
                                     (log.get("timestamp"), log.get("entry")))
                    continue
                    
                for k, v in data.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO kv_store (category, key, value) VALUES (?, ?, ?)",
                        (cat, k, json.dumps(v))
                    )
                    
        # Update cache
        _memory_cache = memory_data.copy()
        _context_cache = None  # Invalidate context cache
        _cache_timestamp = time.time()
        
        return True
    except Exception as e:
        print(f"Error saving SQLite memory: {e}")
        return False

def add_memory_log(entry: str) -> None:
    """Adds a timestamped log entry."""
    memory = load_memory()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memory["memory_log"].append({
        "timestamp": timestamp,
        "entry": entry
    })
    memory["memory_log"] = memory["memory_log"][-50:]
    save_memory(memory)

def get_preference(key: str) -> Optional[Any]:
    """Retrieves a specific preference."""
    memory = load_memory()
    return memory.get("preferences", {}).get(key, None)

def set_preference(key: str, value: Any) -> None:
    """Sets a specific preference."""
    memory = load_memory()
    if "preferences" not in memory:
        memory["preferences"] = {}
    memory["preferences"][key] = value
    add_memory_log(f"Updated preference: {key} = {value}")
    save_memory(memory)

def update_skill(language: str, is_learning: bool = False) -> None:
    """Adds a programming language to skills."""
    memory = load_memory()
    category = "learning" if is_learning else "languages"
    
    if language not in memory["skills"][category]:
        memory["skills"][category].append(language)
        add_memory_log(f"Added skill: {language} ({'learning' if is_learning else 'known'})")
        save_memory(memory)

def get_file_path(file_key: str) -> Optional[str]:
    """Gets a stored file path."""
    memory = load_memory()
    return memory.get("files", {}).get(file_key, None)

def update_file_path(file_key: str, path: str) -> None:
    """Updates a file path in memory."""
    memory = load_memory()
    if "files" not in memory:
        memory["files"] = {}
    memory["files"][file_key] = path
    save_memory(memory)

def get_all_memory_as_string() -> str:
    """Formats all memory + user facts as a readable string for AI context (with caching)."""
    global _context_cache, _cache_timestamp
    
    if _context_cache is not None and _cache_timestamp:
        if time.time() - _cache_timestamp < 10:
            return _context_cache
    
    memory = load_memory()
    memory_str = "=== USER CONTEXT & MEMORY ===\n\n"
    
    memory_str += "Personal Information:\n"
    for key, value in memory.get("personal", {}).items():
        memory_str += f"  - {key.title()}: {value}\n"
    
    memory_str += "\nPreferences & Interests:\n"
    for key, value in memory.get("preferences", {}).items():
        if isinstance(value, list):
            memory_str += f"  - {key.title()}: {', '.join(value)}\n"
        else:
            memory_str += f"  - {key.title()}: {value}\n"
    
    memory_str += "\nTechnical Skills:\n"
    if memory.get("skills", {}).get("languages"):
        memory_str += f"  - Known Languages: {', '.join(memory['skills']['languages'])}\n"
    if memory.get("skills", {}).get("learning"):
        memory_str += f"  - Currently Learning: {', '.join(memory['skills']['learning'])}\n"
    
    if memory.get("routines"):
        memory_str += "\nDaily Routines:\n"
        for time_of_day, activity in memory["routines"].items():
            memory_str += f"  - {time_of_day.title()}: {activity}\n"
    
    if memory.get("memory_log"):
        memory_str += "\nRecent Context:\n"
        for log in memory["memory_log"][-5:]:
            memory_str += f"  - [{log['timestamp']}] {log['entry']}\n"

    # NEW: Include dynamically learned user facts
    facts = get_recent_facts(15)
    if facts:
        memory_str += "\nThings User Has Said / Facts I've Learned:\n"
        for fact in facts:
            memory_str += f"  - {fact}\n"

    # NEW: Pending to-dos for context
    pending = list_todos(status="pending")
    if pending:
        memory_str += "\nUser's Pending Tasks (To-Do List):\n"
        for todo in pending[:5]:
            memory_str += f"  - [{todo['id']}] {todo['task']}\n"
            
    _context_cache = memory_str
    return memory_str

def preload_cache() -> None:
    """Pre-load memory into cache at startup for instant access."""
    global _memory_cache, _context_cache, _cache_timestamp
    
    _memory_cache = load_memory()
    _context_cache = get_all_memory_as_string()
    _cache_timestamp = time.time()
    print("[OK] SQLite Memory cache pre-loaded for instant access")

def clear_cache() -> None:
    """Clear memory cache (useful for debugging)."""
    global _memory_cache, _context_cache, _cache_timestamp
    
    _memory_cache = None
    _context_cache = None
    _cache_timestamp = None
    print("🔄 Memory cache cleared")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: DYNAMIC FACT LEARNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def learn_fact(fact_text: str) -> bool:
    """
    Save a dynamic fact learned from user conversation.
    Ignores duplicate facts (UNIQUE constraint).
    Example: learn_fact('User mujhe coding pasand hai kehta hai.')
    """
    global _context_cache  # Invalidate so next call gets fresh context
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _db_lock, _get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_facts (fact, timestamp) VALUES (?, ?)",
                (fact_text.strip(), timestamp)
            )
        _context_cache = None  # Force context refresh
        print(f"[Sia Memory] 💡 Learned: {fact_text}")
        return True
    except Exception as e:
        print(f"[Sia Memory] Error learning fact: {e}")
        return False


def get_recent_facts(n: int = 15) -> List[str]:
    """
    Retrieve the N most recent learned facts for AI context.
    Returns a list of fact strings.
    """
    try:
        with _db_lock, _get_db() as conn:
            rows = conn.execute(
                "SELECT fact FROM user_facts ORDER BY id DESC LIMIT ?", (n,)
            ).fetchall()
        return [row["fact"] for row in rows]
    except Exception as e:
        print(f"[Sia Memory] Error getting facts: {e}")
        return []


def forget_fact(fact_text: str) -> bool:
    """Remove a specific fact from memory."""
    global _context_cache
    try:
        with _db_lock, _get_db() as conn:
            conn.execute("DELETE FROM user_facts WHERE fact = ?", (fact_text,))
        _context_cache = None
        return True
    except Exception as e:
        print(f"[Sia Memory] Error forgetting fact: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: TO-DO LIST MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def add_todo(task_text: str) -> Optional[int]:
    """
    Add a new task to the to-do list.
    Returns the new task's ID.
    """
    global _context_cache
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _db_lock, _get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO todos (task, status, created_at) VALUES (?, 'pending', ?)",
                (task_text.strip(), timestamp)
            )
        _context_cache = None
        print(f"[Sia ToDo] ✅ Added: {task_text}")
        return cursor.lastrowid
    except Exception as e:
        print(f"[Sia ToDo] Error adding task: {e}")
        return None


def list_todos(status: str = "pending") -> List[Dict[str, Any]]:
    """
    Retrieve tasks from the to-do list.
    status: 'pending', 'done', or 'all'
    Returns a list of dicts with id, task, status, created_at.
    """
    try:
        with _db_lock, _get_db() as conn:
            if status == "all":
                rows = conn.execute(
                    "SELECT id, task, status, created_at FROM todos ORDER BY id DESC LIMIT 20"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, task, status, created_at FROM todos WHERE status = ? ORDER BY id DESC LIMIT 15",
                    (status,)
                ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[Sia ToDo] Error listing tasks: {e}")
        return []


def complete_todo(task_id: int) -> bool:
    """
    Mark a task as done by its ID.
    Returns True if updated successfully.
    """
    global _context_cache
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _db_lock, _get_db() as conn:
            conn.execute(
                "UPDATE todos SET status = 'done', completed_at = ? WHERE id = ?",
                (timestamp, task_id)
            )
        _context_cache = None
        print(f"[Sia ToDo] 🎉 Completed task #{task_id}")
        return True
    except Exception as e:
        print(f"[Sia ToDo] Error completing task: {e}")
        return False


def delete_todo(task_id: int) -> bool:
    """Permanently remove a task from the list."""
    global _context_cache
    try:
        with _db_lock, _get_db() as conn:
            conn.execute("DELETE FROM todos WHERE id = ?", (task_id,))
        _context_cache = None
        return True
    except Exception as e:
        print(f"[Sia ToDo] Error deleting task: {e}")
        return False


def get_morning_briefing_data() -> Dict[str, Any]:
    """
    Returns a structured summary for morning briefing:
    - Pending todos
    - Recent learned facts
    - Time-aware greeting
    """
    now = datetime.now()
    hour = now.hour
    date_str = now.strftime("%A, %d %B %Y")
    
    todos = list_todos(status="pending")
    facts = get_recent_facts(5)
    
    return {
        "date": date_str,
        "hour": hour,
        "pending_todos": todos,
        "recent_facts": facts,
        "todo_count": len(todos)
    }
