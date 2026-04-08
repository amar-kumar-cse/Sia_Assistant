"""
Advanced Actions Module
Optimized system integration for Amar's workflow
Enhanced with Vision, OS Automation, Web Search, RAG,
Long-Term Memory, Smart Macros, and WhatsApp Integration
"""

import webbrowser
import os
import subprocess
import platform
from . import memory
import urllib.parse
from .logger import get_logger
from typing import Optional, Dict, List, Any
from .action_handler import action_handler

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORIGINAL ACTIONS (preserved)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def open_url(url: str) -> str:
    """Open URL in default browser."""
    try:
        webbrowser.open(url)
        return f"✅ Opening {url}..."
    except Exception as e:
        return f"❌ Failed to open URL: {e}"

def open_file(filepath: str) -> str:
    """Open file with system default application."""
    if not os.path.exists(filepath):
        return f"❌ File not found: {filepath}"
    
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':
            subprocess.run(['open', filepath])
        else:
            subprocess.run(['xdg-open', filepath])
        
        return f"✅ Opened: {os.path.basename(filepath)}"
    except Exception as e:
        return f"❌ Error opening file: {e}"

def open_resume() -> str:
    """Open Amar's professional resume/CV."""
    resume_path = memory.get_file_path("resume_path")
    
    if resume_path and os.path.exists(resume_path):
        return open_file(resume_path)
    
    user_home = os.path.expanduser("~")
    possible_locations = [
        os.path.join(user_home, "OneDrive", "Documents", "Resume.pdf"),
        os.path.join(user_home, "Documents", "Resume.pdf"),
        os.path.join(user_home, "Desktop", "Resume.pdf"),
        os.path.join(user_home, "OneDrive", "Desktop", "Resume.pdf"),
        os.path.join(user_home, "Downloads", "Resume.pdf"),
        os.path.join(user_home, "OneDrive", "Documents", "Resume.docx"),
        os.path.join(user_home, "Documents", "Resume.docx"),
        os.path.join(user_home, "Desktop", "Resume.docx"),
    ]
    
    for path in possible_locations:
        if os.path.exists(path):
            memory.update_file_path("resume_path", path)
            return open_file(path)
    
    return "❌ Resume not found! Please update path in memory.json → files → resume_path"

def open_college_portal() -> str:
    """Open RIT Roorkee college portal (CyborgERP)."""
    portal_url = memory.get_file_path("college_portal")
    if not portal_url:
        portal_url = "https://cyborgerp.in/"
        memory.update_file_path("college_portal", portal_url)
    return open_url(portal_url)

def open_code_editor() -> str:
    """Open preferred code editor."""
    editors = [
        ("VS Code", "code"),
        ("PyCharm", "pycharm"),
        ("Notepad++", "notepad++")
    ]
    
    for name, command in editors:
        try:
            subprocess.Popen([command], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            return f"✅ Opening {name}..."
        except Exception as e:
            logger.warning(f"Failed to open {name}: {e}")
            continue
    
    logger.error("No code editor found")
    return "❌ No code editor found. Install VS Code, PyCharm, or Notepad++"

def open_terminal() -> str:
    """Open terminal/command prompt."""
    try:
        if platform.system() == 'Windows':
            subprocess.Popen(['cmd'])
        else:
            subprocess.Popen(['gnome-terminal'])
        return "✅ Terminal opened"
    except Exception as e:
        logger.error(f"Failed to open terminal: {e}")
        return "❌ Failed to open terminal"

def check_battery() -> str:
    """Check battery percentage."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            plugged = "Plugged In" if battery.power_plugged else "Not Plugged"
            return f"✅ Battery is at {battery.percent}% ({plugged})"
        return "❌ Battery information not available"
    except ImportError:
        return "❌ psutil not installed. Run: pip install psutil"
    except Exception as e:
        logger.error(f"Failed to get battery info: {e}")
        return "❌ Failed to get battery info"

def lock_system() -> str:
    """Lock the computer."""
    try:
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        elif platform.system() == 'Darwin':
            subprocess.run(['pmset', 'displaysleepnow'])
        else:
            subprocess.run(['xdg-screensaver', 'lock'])
        return "✅ System locked"
    except Exception as e:
        return f"❌ Failed to lock system: {e}"

def play_music(query: str) -> str:
    """Play music on YouTube."""
    quoted_query = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={quoted_query}"
    open_url(url)
    return f"✅ Searching for '{query}' on YouTube"

def search_wikipedia(query: str) -> str:
    """Search Wikipedia for a query."""
    try:
        import wikipedia
        summary = wikipedia.summary(query, sentences=2)
        return f"📚 Wikipedia says: {summary}"
    except ImportError:
        return "❌ wikipedia not installed. Run: pip install wikipedia"
    except Exception as e:
        # Handle DisambiguationError and PageError generically
        err_name = type(e).__name__
        if 'Disambiguation' in err_name:
            return f"⚠️ There are multiple results for {query}. Please be more specific."
        elif 'PageError' in err_name:
            return f"❌ Could not find Wikipedia page for {query}."
        return f"❌ Error searching Wikipedia: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: VISION ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_vision_screen(user_text: str) -> str:
    """Handle screen analysis request."""
    try:
        from . import vision_engine
        question = user_text  # Pass the full user text as the question
        return vision_engine.analyze_screen(question)
    except Exception as e:
        return f"❌ Screen analysis failed: {e}"

def _handle_vision_webcam(user_text: str) -> str:
    """Handle webcam analysis request."""
    try:
        from . import vision_engine
        return vision_engine.analyze_webcam(user_text)
    except Exception as e:
        return f"❌ Webcam analysis failed: {e}"

def _handle_vision_error() -> str:
    """Handle error detection on screen."""
    try:
        from . import vision_engine
        return vision_engine.analyze_error_on_screen()
    except Exception as e:
        return f"❌ Error detection failed: {e}"

def _handle_vision_window(user_text: str) -> str:
    """Handle active window analysis request."""
    try:
        from . import vision_engine
        question = user_text
        return vision_engine.analyze_active_window(question)
    except Exception as e:
        return f"❌ Window analysis failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: OS AUTOMATION ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_open_app(cmd: str) -> Optional[str]:
    """Extract app name and open it."""
    try:
        from . import os_automation
        
        # Extract app name from command
        app_name = cmd
        for trigger in ["open", "kholo", "chalu karo", "start", "launch"]:
            if trigger in app_name:
                app_name = app_name.split(trigger, 1)[1].strip()
                break
        
        if app_name:
            return os_automation.open_app(app_name)
        return None
    except Exception as e:
        return f"❌ App open failed: {e}"

def _handle_generate_script(cmd: str) -> str:
    """Handle PC automation scripting request."""
    try:
        from . import os_automation
        return os_automation.generate_and_run_script(cmd)
    except Exception as e:
        return f"❌ Script automation failed: {e}"

def _handle_volume(cmd: str) -> Optional[str]:
    """Handle volume commands."""
    try:
        from . import os_automation
        
        if "mute" in cmd:
            return os_automation.mute_volume()
        
        # Extract number
        import re
        numbers = re.findall(r'\d+', cmd)
        if numbers:
            level = int(numbers[0])
            return os_automation.set_volume(level)
        
        if "up" in cmd or "badhao" in cmd:
            return os_automation.set_volume(80)
        elif "down" in cmd or "kam" in cmd:
            return os_automation.set_volume(30)
        
        return None
    except Exception as e:
        return f"❌ Volume control failed: {e}"

def _handle_system_info() -> str:
    """Get system information."""
    try:
        from . import os_automation
        return os_automation.get_system_info()
    except Exception as e:
        return f"❌ System info failed: {e}"

def _handle_organize_files(cmd: str) -> str:
    """Handle file organization."""
    try:
        from . import os_automation
        # Check if specific folder mentioned
        if "desktop" in cmd:
            folder = os.path.join(os.path.expanduser("~"), "Desktop")
        elif "download" in cmd:
            folder = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            folder = None  # Default to Downloads
        
        return os_automation.organize_files(folder)
    except Exception as e:
        return f"❌ File organization failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: WEB SEARCH ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_web_search(cmd: str) -> Optional[str]:
    """Handle web search request."""
    try:
        from . import web_search
        
        # Extract query
        query = cmd
        for trigger in ["search", "dhundho", "internet pe", "google", "search karo"]:
            if trigger in query:
                query = query.split(trigger, 1)[1].strip()
                break
        
        if query:
            return web_search.search_web(query)
        return None
    except Exception as e:
        return f"❌ Web search failed: {e}"

def _handle_news(cmd: str) -> str:
    """Handle news request."""
    try:
        from . import web_search
        
        topic = cmd
        for trigger in ["news", "khabar", "headlines"]:
            if trigger in topic:
                topic = topic.split(trigger, 1)[1].strip()
                break
        
        if not topic:
            topic = "India technology"
        
        return web_search.get_latest_news(topic)
    except Exception as e:
        return f"❌ News fetch failed: {e}"

def _handle_weather(cmd: str) -> str:
    """Handle weather request. Returns SHOW_WIDGET:WEATHER signal for desktop widget."""
    try:
        city = "Roorkee"  # Default
        for word in ["weather", "mausam"]:
            if word in cmd:
                parts = cmd.split(word, 1)[1].strip()
                if parts:
                    # Remove common words
                    for remove in ["in", "of", "ka", "ki", "ke", "mein", "dikhao", "batao", "aaj", "ka"]:
                        parts = parts.replace(remove, "").strip()
                    if parts:
                        city = parts.strip().title()
        
        # Return signal for desktop widget pop-up
        return f"SHOW_WIDGET:WEATHER:{city}"
    except Exception as e:
        return f"❌ Weather fetch failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: KNOWLEDGE BASE ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_index_files(cmd: str) -> str:
    """Handle knowledge base indexing request."""
    try:
        from . import knowledge_base
        
        # Check if specific path mentioned
        if "desktop" in cmd:
            path = os.path.join(os.path.expanduser("~"), "Desktop")
        elif "project" in cmd or "sia" in cmd:
            path = os.path.dirname(os.path.abspath(__file__))
        else:
            path = os.path.dirname(os.path.abspath(__file__))  # Default to Sia project
        
        return knowledge_base.index_project(path)
    except Exception as e:
        return f"❌ File indexing failed: {e}"

def _handle_kb_search(cmd: str) -> str:
    """Handle knowledge base search."""
    try:
        from . import knowledge_base
        
        query = cmd
        for trigger in ["dhundho", "find", "search", "code", "file"]:
            if trigger in query:
                query = query.split(trigger, 1)[1].strip()
                break
        
        result = knowledge_base.search_knowledge(query)
        if result:
            return result
        return "❌ Knowledge base mein kuch nahi mila. Pehle files index karo."
    except Exception as e:
        return f"❌ KB search failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: MOOD DETECTION & RESPONSE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MOOD_TRIGGERS: Dict[str, Dict[str, Any]] = {
    "RELAX": {
        "keywords": ["thak gaya", "thak gayi", "tired", "exhausted", "thaka hua",
                      "neend aa rahi", "sleepy", "bore ho raha", "bored", "stressed",
                      "tension", "frustrated", "thakaan"],
        "responses": [
            "Arre Hero, thak gaye? 🧡 Chill karo thodi der... Main hoon na! Ek deep breath lo... ☀️",
            "Aww, mere Hero ko rest chahiye! 🌅 Relax karo, main tumhara khayal rakhungi. Ankhen band karo 2 min ke liye... 💛",
            "Hero, itni mehnat kaafi hai! 🧡 Ab thoda break lo. Ek cup chai piyo aur relax karo! ☕",
            "Thak gaye na? Main samajh sakti hoon. 🌙 Ab bas 5 min relax karo, phir fresh feel karoge! 💛",
        ],
    },
    "ENERGIZE": {
        "keywords": ["motivation", "motivate", "uthao", "energy", "pump up",
                      "josh", "himmat", "udaas", "sad", "low feel"],
        "responses": [
            "Hero! 💪 Tu best hai! Duniya badalne wala hai tu! Chal uth, game on! 🔥",
            "Arre champ! 🌟 Teri mehnat rang layegi! Bas thoda aur push kar! Let's GO! 💪",
            "Hero, tu wo banda hai jo impossible ko possible banata hai! 🚀 Ab LFG! 🔥",
        ],
    },
    "FOCUS": {
        "keywords": ["focus", "concentrate", "dhyan", "padhai", "study mode",
                      "work mode", "productive"],
        "responses": [
            "Focus mode ON! 🎯 Hero, main sab distractions hata deti hoon. Tu bas code kar! 💻",
            "Study mode activated! 📚 Hero, tu padh, main guard pe hoon. Koi disturb nahi karega! 🛡️",
        ],
    },
}


def _handle_mood_detection(cmd: str) -> Optional[str]:
    """
    Detect user's mood from their speech and return a MOOD_CHANGE signal.
    Returns: 'MOOD_CHANGE:<MOOD>:<response text>' or None
    """
    import random as _random
    for mood, data in MOOD_TRIGGERS.items():
        for keyword in data["keywords"]:
            if keyword in cmd:
                response = _random.choice(data["responses"])
                return f"MOOD_CHANGE:{mood}:{response}"
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: LONG-TERM MEMORY & PERSONALIZATION ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_learn_fact(cmd: str) -> Optional[str]:
    """
    Extract a user fact from command like 'yaad rakho mujhe cricket pasand hai'
    and save it to permanent memory.
    """
    fact_text = cmd
    # Remove trigger words to get the actual fact content
    for trigger in ["yaad rakho ke", "yaad rakho", "remember that", "remember",
                    "note karo ke", "note karo", "note down", "save this"]:
        if trigger in fact_text:
            fact_text = fact_text.split(trigger, 1)[1].strip()
            break
    
    if fact_text:
        memory.learn_fact(f"User ne kaha: {fact_text}")
        return f"✅ Yaad kar liya Hero! '{fact_text}' — ye main hamesha yaad rakhuungi! 💜"
    return None


def _handle_todo(cmd):
    """
    Handle to-do list commands: add, list, complete.
    Returns a formatted string response.
    """
    import re as _re
    
    # Add task
    if any(kw in cmd for kw in ["todo add", "task add", "add todo", "add task",
                                  "kaam add", "list mein daalo", "list mein add"]):
        task_text = cmd
        for trigger in ["todo add", "task add", "add todo", "add task",
                        "kaam add", "list mein daalo", "list mein add"]:
            if trigger in task_text:
                task_text = task_text.split(trigger, 1)[1].strip()
                break
        if task_text:
            task_id = memory.add_todo(task_text)
            return f"✅ Todo add ho gaya Hero! Task #{task_id}: '{task_text}' 📝"
        return "❌ Task text batao — 'Todo add: mujhe Python project banana hai'"
    
    # Complete task by ID
    if any(kw in cmd for kw in ["complete task", "task done", "kaam khatam",
                                  "mark done", "complete todo"]):
        numbers = _re.findall(r'\d+', cmd)
        if numbers:
            task_id = int(numbers[0])
            if memory.complete_todo(task_id):
                return f"🎉 Task #{task_id} complete! Well done Hero! 💪"
            return f"❌ Task #{task_id} nahi mili."
        return "❌ Task ID batao — 'Task done 3'"
    
    # List tasks
    if any(kw in cmd for kw in ["todo list", "task list", "meri tasks", "pending tasks",
                                  "kya karna hai", "kaam batao", "todos dikhao"]):
        todos = memory.list_todos(status="pending")
        if not todos:
            return "🎉 Koi bhi pending task nahi hai Hero! Sab khatam! 👏"
        
        lines = ["📝 Tumhari Pending Tasks:"]
        for todo in todos:
            lines.append(f"  #{todo['id']}: {todo['task']}")
        return "\n".join(lines)
    
    return None


def _handle_morning_briefing(_cmd):
    """Trigger the morning briefing from brain module."""
    try:
        from . import brain
        return brain.morning_briefing()
    except Exception as e:
        return f"❌ Morning briefing mein error: {e}"


def _handle_coding_env():
    """Trigger the coding environment macro."""
    try:
        from . import os_automation
        return os_automation.launch_coding_env()
    except Exception as e:
        return f"❌ Coding environment shuru karne mein error: {e}"


def _handle_work_mode():
    """Trigger the work mode macro."""
    try:
        from . import os_automation
        return os_automation.open_work_mode()
    except Exception as e:
        return f"❌ Work mode shuru karne mein error: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WHATSAPP INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _handle_whatsapp(cmd: str) -> str:
    """
    Handle WhatsApp-related commands.
    Delegates to os_automation.open_whatsapp_web() for the actual browser action.
    Previously this function was called in perform_action() but never defined,
    causing an immediate NameError on any WhatsApp command.
    """
    try:
        from . import os_automation
        return os_automation.open_whatsapp_web()
    except AttributeError:
        # os_automation doesn't have open_whatsapp_web — open WhatsApp Web directly
        import webbrowser
        webbrowser.open("https://web.whatsapp.com")
        return "✅ WhatsApp Web khol diya Hero! 📱"
    except Exception as e:
        logger.error("WhatsApp action failed: %s", e)
        return f"❌ WhatsApp kholne mein problem: {e}"

# NOTE: _handle_index_files and _handle_kb_search were previously defined here
# as exact duplicates of the functions at lines 344-377 above.
# Duplicates removed — the original definitions above are the canonical ones.


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MASTER ACTION ROUTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def perform_action(command_text: str) -> Optional[str]:
    """
    Intelligent command parser using factory pattern.
    Detects intent and executes appropriate action.
    Enhanced with Vision, Automation, Search, RAG, and Mood Detection.
    """
    if not command_text or not isinstance(command_text, str):
        return None

    cmd = command_text.lower()

    # ── MOOD DETECTION (highest priority for personal touch) ──
    mood_result = _handle_mood_detection(cmd)
    if mood_result:
        return mood_result

    # ── CODE REPAIR COMMANDS ──
    try:
        from . import code_repair
        if code_repair.is_code_repair_request(command_text):
            return code_repair.repair_code(command_text)
    except Exception as e:
        logger.warning(f"Code repair check failed: {e}")

    # ── ADVANCED AUTOMATION COMMANDS (GIT & VENV) ──
    if any(kw in cmd for kw in ["git push", "commit code", "save code", "code push", "github pe push"]):
        try:
            from . import dev_tools
            return dev_tools.git_commit_push()
        except Exception as e:
            return f"❌ Git automation error: {e}"

    if any(kw in cmd for kw in ["setup project", "environment setup", "venv banao", "install requirements"]):
        try:
            from . import dev_tools
            return dev_tools.setup_python_env()
        except Exception as e:
            return f"❌ Environment setup error: {e}"

    # ── FACTORY-BASED ACTION HANDLING ──
    # Vision actions
    if any(kw in cmd for kw in [
        "screen dekho", "screen pe kya", "screen dikha", "meri screen", "screenshot",
        "desktop dekho", "desktop dekh", "desktop pe kya", "meri desktop", "desktop dikha"
    ]):
        return action_handler.execute("vision_screen", command_text)

    if any(kw in cmd for kw in ["camera", "webcam", "kya dikh raha", "mujhe dekho"]):
        return action_handler.execute("vision_webcam", command_text)

    if any(kw in cmd for kw in ["window dekho", "active window", "is window", "current window", "samne kya hai"]):
        return action_handler.execute("vision_window", command_text)

    if any(kw in cmd for kw in ["error dikha", "error fix", "bug fix", "screen pe error", "kya error", "ye kya error hai", "kya galat hai", "error batao"]):
        return action_handler.execute("vision_error", command_text)

    # OS automation actions
    if any(kw in cmd for kw in ["volume"]):
        return action_handler.execute("volume", cmd)

    if any(kw in cmd for kw in ["system info", "pc info", "laptop info", "cpu", "ram"]):
        return action_handler.execute("system_info", cmd)

    if any(kw in cmd for kw in ["files organize", "file organize", "folder organize", "saaf karo", "clean folder"]):
        return action_handler.execute("organize_files", cmd)

    if any(kw in cmd for kw in ["script", "automate karo", "backup le lo", "backup karo", "automate"]):
        return action_handler.execute("generate_script", command_text)

    # Shutdown/restart commands
    if any(kw in cmd for kw in ["shutdown", "shut down"]):
        try:
            from . import os_automation
            if "cancel" in cmd:
                return os_automation.cancel_shutdown()
            import re
            numbers = re.findall(r'\d+', cmd)
            mins = int(numbers[0]) if numbers else 0
            return os_automation.shutdown_timer(mins)
        except Exception as e:
            return f"❌ Shutdown failed: {e}"

    if "restart" in cmd or "reboot" in cmd:
        try:
            from . import os_automation
            return os_automation.restart_system()
        except Exception as e:
            return f"❌ Restart failed: {e}"

    if "sleep" in cmd and any(kw in cmd for kw in ["mode", "pc", "laptop", "system", "computer"]):
        try:
            from . import os_automation
            return os_automation.sleep_system()
        except Exception as e:
            return f"❌ Sleep failed: {e}"

    if any(kw in cmd for kw in ["brightness"]):
        try:
            from . import os_automation
            import re
            numbers = re.findall(r'\d+', cmd)
            if numbers:
                return os_automation.set_brightness(int(numbers[0]))
        except Exception as e:
            logger.warning(f"Brightness control failed: {e}")

    if any(kw in cmd for kw in ["wifi", "internet connection", "network info"]):
        try:
            from . import os_automation
            return os_automation.get_wifi_info()
        except Exception as e:
            logger.warning(f"Wifi info failed: {e}")

    if any(kw in cmd for kw in ["recycle bin", "trash", "dustbin"]):
        try:
            from . import os_automation
            return os_automation.empty_recycle_bin()
        except Exception as e:
            logger.warning(f"Recycle bin empty failed: {e}")

    if any(kw in cmd for kw in ["temp file", "temporary file", "temp clean", "temp saaf"]):
        try:
            from . import os_automation
            return os_automation.clear_temp_files()
        except Exception as e:
            logger.warning(f"Temp file cleanup failed: {e}")

    if any(kw in cmd for kw in ["email", "mail likho", "email draft"]):
        try:
            from . import dev_tools
            return dev_tools.draft_email()
        except Exception as e:
            logger.warning(f"Email draft failed: {e}")

    # Smart app opener (check after specific commands to avoid false matches)
    if any(kw in cmd for kw in ["kholo", "open ", "launch", "start ", "chalu"]):
        result = action_handler.execute("open_app", cmd)
        if result:
            return result

    # ── WEB SEARCH ACTIONS ──
    if any(kw in cmd for kw in ["weather", "mausam"]):
        return action_handler.execute("weather", cmd)

    if any(kw in cmd for kw in ["news", "khabar", "headline", "taaza khabar"]):
        return action_handler.execute("news", cmd)

    # ── KNOWLEDGE BASE ACTIONS ──
    if any(kw in cmd for kw in ["index files", "files index", "index karo", "scan files", "knowledge base"]):
        return action_handler.execute("index_files", cmd)

    if any(kw in cmd for kw in ["purana code", "old code", "mera code", "find in files", "file mein dhundho"]):
        return action_handler.execute("kb_search", cmd)

    # ── MEMORY / PERSONALIZATION ACTIONS ──
    if any(kw in cmd for kw in ["yaad rakho", "note karo", "remember", "save this", "note down"]):
        result = action_handler.execute("learn_fact", cmd)
        if result:
            return result

    # ── TO-DO LIST ACTIONS ──
    if any(kw in cmd for kw in ["todo", "task add", "task list", "meri tasks",
                                  "kaam add", "kya karna hai", "pending tasks",
                                  "todos dikhao", "kaam batao", "task done",
                                  "kaam khatam", "complete task", "mark done"]):
        result = _handle_todo(cmd)
        if result:
            return result

    # ── MORNING BRIEFING ──
    if any(kw in cmd for kw in ["morning briefing", "aaj ka plan", "good morning sia",
                                  "daily briefing", "aaj kya hai", "morning update"]):
        return _handle_morning_briefing(cmd)

    # ── PC AUTOMATION MACROS ──
    if any(kw in cmd for kw in ["coding environment", "coding setup", "development setup",
                                  "dev setup", "coding env"]):
        return _handle_coding_env()

    if any(kw in cmd for kw in ["work mode", "work setup", "kaam shuru", "office mode"]):
        return _handle_work_mode()

    if any(kw in cmd for kw in ["whatsapp karo", "whatsapp message", "whatsapp bhejo",
                                  "whatsapp pe bolo", "whatsapp open"]):
        return _handle_whatsapp(cmd)

    # ── ORIGINAL COMMANDS (preserved) ──

    # Resume/CV commands
    if any(keyword in cmd for keyword in ["resume", "cv", "biodata", "bio data"]):
        return open_resume()

    # College portal commands
    if any(keyword in cmd for keyword in ["college", "portal", "cyborg", "erp", "rit"]):
        return open_college_portal()

    # Code editor commands
    if any(keyword in cmd for keyword in ["code editor", "vscode", "vs code", "pycharm", "editor"]):
        return open_code_editor()

    # Terminal commands
    if any(keyword in cmd for keyword in ["terminal", "command prompt", "cmd", "powershell"]):
        return open_terminal()

    # Play Music
    if "play" in cmd:
        query = cmd.split("play", 1)[1].replace("music", "").replace("song", "").replace("on youtube", "").replace("on spotify", "").strip()
        if query:
            return play_music(query)

    # Battery check
    if "battery" in cmd:
        return check_battery()

    # Lock System
    if "lock" in cmd and ("system" in cmd or "pc" in cmd or "computer" in cmd or "laptop" in cmd):
        return lock_system()

    # Wikipedia Search
    if "wikipedia" in cmd or "who is" in cmd or ("what is" in cmd and "time" not in cmd):
        if "wikipedia" in cmd:
            query = cmd.split("wikipedia", 1)[1].strip()
            if query.startswith("for"): query = query[3:].strip()
        elif "who is" in cmd:
            query = cmd.split("who is", 1)[1].strip()
        else:
            query = cmd.split("what is", 1)[1].strip()

        if query:
            return search_wikipedia(query)

    # Career sites
    if "tcs" in cmd or "tata consultancy" in cmd:
        return open_url("https://www.tcs.com/careers")

    if "jp morgan" in cmd or "jpmorgan" in cmd or "j.p. morgan" in cmd:
        return open_url("https://careers.jpmorgan.com/")

    if "naukri" in cmd:
        return open_url("https://www.naukri.com")

    if "linkedin" in cmd:
        return open_url("https://www.linkedin.com")

    # Development sites
    if "github" in cmd:
        github_url = memory.get_file_path("github_profile")
        if not github_url:
            github_url = "https://github.com"
        return open_url(github_url)

    if "stackoverflow" in cmd or "stack overflow" in cmd:
        return open_url("https://stackoverflow.com")

    if "leetcode" in cmd:
        return open_url("https://leetcode.com")

    if "hackerrank" in cmd:
        return open_url("https://www.hackerrank.com")

    if "geeksforgeeks" in cmd or "gfg" in cmd:
        return open_url("https://www.geeksforgeeks.org")

    # Common sites
    if "google" in cmd:
        return open_url("https://www.google.com")

    if "youtube" in cmd:
        return open_url("https://www.youtube.com")

    if "gmail" in cmd or "mail" in cmd:
        return open_url("https://mail.google.com")

    # ── WEB SEARCH FALLBACK (for "search X" style queries) ──
    if any(kw in cmd for kw in ["search", "dhundho", "internet"]):
        result = action_handler.execute("web_search", cmd)
        if result:
            return result

    # No action matched
    return None

# Quick action shortcuts
def quick_resume():
    return open_resume()

def quick_portal():
    return open_college_portal()

def quick_tcs():
    return open_url("https://www.tcs.com/careers")

def quick_jpmorgan():
    return open_url("https://careers.jpmorgan.com/")
