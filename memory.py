import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"

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
    "memory_log": []
}

# In-memory cache for instant access
_memory_cache = None
_context_cache = None  # Pre-formatted context string
_cache_timestamp = None

def load_memory():
    """Loads memory from JSON file with in-memory caching for instant access."""
    global _memory_cache, _cache_timestamp
    
    # Return cached version if available and recent (< 5 seconds old)
    if _memory_cache is not None and _cache_timestamp:
        import time
        if time.time() - _cache_timestamp < 5:
            return _memory_cache.copy()
    
    if not os.path.exists(MEMORY_FILE):
        # Create default memory file
        save_memory(DEFAULT_MEMORY)
        _memory_cache = DEFAULT_MEMORY.copy()
        import time
        _cache_timestamp = time.time()
        return DEFAULT_MEMORY
    
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all sections exist
            for key, value in DEFAULT_MEMORY.items():
                if key not in data:
                    data[key] = value
            
            # Update cache
            _memory_cache = data.copy()
            import time
            _cache_timestamp = time.time()
            
            return data
    except Exception as e:
        print(f"Error loading memory: {e}")
        return DEFAULT_MEMORY

def save_memory(memory_data):
    """Saves memory to JSON file and updates cache."""
    global _memory_cache, _context_cache, _cache_timestamp
    
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=4, ensure_ascii=False)
        
        # Update cache
        _memory_cache = memory_data.copy()
        _context_cache = None  # Invalidate context cache
        import time
        _cache_timestamp = time.time()
        
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False

def add_memory_log(entry):
    """Adds a timestamped log entry."""
    memory = load_memory()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memory["memory_log"].append({
        "timestamp": timestamp,
        "entry": entry
    })
    # Keep only last 50 entries
    memory["memory_log"] = memory["memory_log"][-50:]
    save_memory(memory)

def get_preference(key):
    """Retrieves a specific preference."""
    memory = load_memory()
    return memory.get("preferences", {}).get(key, None)

def set_preference(key, value):
    """Sets a specific preference."""
    memory = load_memory()
    if "preferences" not in memory:
        memory["preferences"] = {}
    memory["preferences"][key] = value
    add_memory_log(f"Updated preference: {key} = {value}")
    save_memory(memory)

def update_skill(language, is_learning=False):
    """Adds a programming language to skills."""
    memory = load_memory()
    category = "learning" if is_learning else "languages"
    
    if language not in memory["skills"][category]:
        memory["skills"][category].append(language)
        add_memory_log(f"Added skill: {language} ({'learning' if is_learning else 'known'})")
        save_memory(memory)

def get_all_memory_as_string():
    """Formats all memory as a readable string for AI context (with caching)."""
    global _context_cache, _cache_timestamp
    
    # Return cached context if available and recent
    if _context_cache is not None and _cache_timestamp:
        import time
        if time.time() - _cache_timestamp < 10:  # Cache for 10 seconds
            return _context_cache
    
    memory = load_memory()
    
    memory_str = "=== USER CONTEXT & MEMORY ===\n\n"
    
    # Personal Info
    memory_str += "Personal Information:\n"
    for key, value in memory.get("personal", {}).items():
        memory_str += f"  - {key.title()}: {value}\n"
    
    # Preferences
    memory_str += "\nPreferences & Interests:\n"
    for key, value in memory.get("preferences", {}).items():
        if isinstance(value, list):
            memory_str += f"  - {key.title()}: {', '.join(value)}\n"
        else:
            memory_str += f"  - {key.title()}: {value}\n"
    
    # Skills
    memory_str += "\nTechnical Skills:\n"
    if memory.get("skills", {}).get("languages"):
        memory_str += f"  - Known Languages: {', '.join(memory['skills']['languages'])}\n"
    if memory.get("skills", {}).get("learning"):
        memory_str += f"  - Currently Learning: {', '.join(memory['skills']['learning'])}\n"
    
    # Recent interactions (last 5)
    if memory.get("memory_log"):
        memory_str += "\nRecent Context:\n"
        for log in memory["memory_log"][-5:]:
            memory_str += f"  - [{log['timestamp']}] {log['entry']}\n"
    
    # Cache the result
    _context_cache = memory_str
    
    return memory_str

def get_file_path(file_key):
    """Gets a stored file path."""
    memory = load_memory()
    return memory.get("files", {}).get(file_key, None)

def update_file_path(file_key, path):
    """Updates a file path in memory."""
    memory = load_memory()
    if "files" not in memory:
        memory["files"] = {}
    memory["files"][file_key] = path
    save_memory(memory)


def preload_cache():
    """Pre-load memory into cache at startup for instant access."""
    global _memory_cache, _context_cache, _cache_timestamp
    import time
    
    _memory_cache = load_memory()
    _context_cache = get_all_memory_as_string()
    _cache_timestamp = time.time()
    
    print("[OK] Memory cache pre-loaded for instant access")


def clear_cache():
    """Clear memory cache (useful for debugging)."""
    global _memory_cache, _context_cache, _cache_timestamp
    
    _memory_cache = None
    _context_cache = None
    _cache_timestamp = None
    
    print("🔄 Memory cache cleared")
