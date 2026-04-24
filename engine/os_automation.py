"""
OS Automation Module for Sia - PC Control & System Management
Makes Sia a real assistant that can control your computer.
Windows-focused with cross-platform fallbacks.
"""

import os
import sys
import subprocess
import platform
import shutil
import getpass
import ctypes
import time
import tempfile
import webbrowser
import urllib.parse
from typing import Optional, Union
from .logger import get_logger

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  APP LAUNCHER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Common Windows apps and their executable paths/commands
APP_REGISTRY = {
    # Editors
    "vscode": ["code"],
    "vs code": ["code"],
    "visual studio code": ["code"],
    "notepad": ["notepad.exe"],
    "notepad++": ["notepad++"],
    "pycharm": ["pycharm"],
    "sublime": ["subl"],
    
    # Browsers
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
    "firefox": [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    "edge": ["msedge"],
    "brave": [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"],
    
    # System
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "task manager": ["taskmgr.exe"],
    "settings": ["ms-settings:"],
    "control panel": ["control"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    
    # Communication
    "whatsapp": [r"C:\Users\{user}\AppData\Local\WhatsApp\WhatsApp.exe"],
    "telegram": [r"C:\Users\{user}\AppData\Roaming\Telegram Desktop\Telegram.exe"],
    "discord": [r"C:\Users\{user}\AppData\Local\Discord\Update.exe --processStart Discord.exe"],
    
    # Media
    "spotify": [r"C:\Users\{user}\AppData\Roaming\Spotify\Spotify.exe"],
    "vlc": [r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"],
    
    # Dev tools
    "terminal": ["wt.exe", "cmd.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "git bash": [r"C:\Program Files\Git\git-bash.exe"],
    "postman": [r"C:\Users\{user}\AppData\Local\Postman\Postman.exe"],
}


def open_app(app_name: str) -> str:
    """
    Smart app launcher - tries multiple strategies to open an app.
    
    Args:
        app_name: Name of the application to open
    
    Returns:
        Status message
    """
    app_key = app_name.lower().strip()
    username = os.environ.get("USERNAME") or getpass.getuser() or "user"
    
    # Check registry
    if app_key in APP_REGISTRY:
        paths = APP_REGISTRY[app_key]
        for path in paths:
            path = path.replace("{user}", username)
            try:
                if path.startswith("ms-"):
                    # Windows Settings URIs
                    os.startfile(path)
                    return f"✅ {app_name} khol rahi hoon!"
                elif os.path.exists(path):
                    CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
                    subprocess.Popen([path], creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    return f"✅ {app_name} khol diya!"
                else:
                    # Try as command
                    subprocess.Popen(path.split(), 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL,
                                   creationflags=0x08000000 if os.name == 'nt' else 0)
                    return f"✅ {app_name} khol rahi hoon!"
            except Exception:
                continue
    
    # Fallback: Try start command on Windows
    if platform.system() == 'Windows':
        try:
            # Use cmd /c start to launch reliably without shell injection risks.
            result = subprocess.run(
                ["cmd", "/c", "start", "", app_name],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000,
            )
            if result.returncode == 0:
                return f"✅ {app_name} dhundh ke khol rahi hoon!"
            logger.warning(f"Failed to start app: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning("App start timed out")
        except Exception as e:
            logger.error(f"Failed to start app with subprocess: {e}")
    
    return f"❌ '{app_name}' nahi mila. Check karo agar installed hai."


# Command whitelist for security
ALLOWED_COMMANDS = {
    "shutdown", "cancel", "restart", "sleep", "lock",
    "calc", "notepad", "explorer", "taskmgr", "control",
    "ms-settings", "cmd", "powershell", "wt"
}

def _is_command_allowed(command: str) -> bool:
    """Check if a command is in the allowed whitelist."""
    cmd_lower = command.lower().strip()
    return cmd_lower in ALLOWED_COMMANDS or any(allowed in cmd_lower for allowed in ALLOWED_COMMANDS)


def set_volume(level: Union[int, str]) -> str:
    """
    Set system volume (0-100).
    Uses nircmd as fallback if pycaw isn't available.
    """
    try:
        level = int(level)
        level = max(0, min(100, level))
        
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Convert 0-100 to scalar
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"✅ Volume set to {level}%"
            
        except ImportError:
            # Fallback using PowerShell
            if platform.system() == 'Windows':
                # Use PowerShell to set volume
                ps_script = f"""
                $obj = New-Object -ComObject WScript.Shell
                1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
                1..{level // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}
                """
                subprocess.run(["powershell", "-Command", ps_script], 
                             capture_output=True, creationflags=0x08000000)
                return f"✅ Volume approximately set to {level}%"
            
    except Exception as e:
        return f"❌ Volume set nahi ho paya: {e}"


def mute_volume() -> str:
    """Mute/unmute system volume."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        from ctypes import cast, POINTER
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        current_mute = volume.GetMute()
        volume.SetMute(not current_mute, None)
        
        return "✅ Volume muted!" if not current_mute else "✅ Volume unmuted!"
        
    except ImportError:
        # Fallback
        if platform.system() == 'Windows':
            subprocess.run(["powershell", "-Command", 
                          "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                         capture_output=True, creationflags=0x08000000)
            return "✅ Mute toggled!"
    except Exception as e:
        return f"❌ Mute toggle failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FILE ORGANIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Extension-to-category mapping
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "Code": [".py", ".java", ".cpp", ".c", ".js", ".html", ".css", ".json", ".xml", ".sql", ".md"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Executables": [".exe", ".msi", ".bat", ".cmd", ".ps1"],
    "Data": [".csv", ".db", ".sqlite", ".json", ".xml"],
}


def organize_files(folder_path: Optional[str] = None) -> str:
    """
    Organize files in a folder by their type/extension.
    
    Args:
        folder_path: Path to folder to organize. Defaults to user's Downloads folder.
    
    Returns:
        Status message with count of organized files
    """
    if not folder_path:
        folder_path = os.path.join(os.path.expanduser("~"), "Downloads")
    
    if not os.path.exists(folder_path):
        return f"❌ Folder nahi mila: {folder_path}"
    
    organized_count = 0
    errors = 0
    
    try:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            
            # Skip directories
            if os.path.isdir(filepath):
                continue
            
            # Find category
            ext = os.path.splitext(filename)[1].lower()
            category = "Others"
            
            for cat, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break
            
            # Create category folder
            cat_folder = os.path.join(folder_path, category)
            os.makedirs(cat_folder, exist_ok=True)
            
            # Move file
            dest = os.path.join(cat_folder, filename)
            if not os.path.exists(dest):
                try:
                    shutil.move(filepath, dest)
                    organized_count += 1
                except Exception:
                    errors += 1
        
        return f"✅ {organized_count} files organized in {os.path.basename(folder_path)}! ({errors} errors)"
        
    except Exception as e:
        return f"❌ File organization failed: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SYSTEM INFO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_system_info() -> str:
    """Get comprehensive system information."""
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        mem = psutil.virtual_memory()
        mem_used = round(mem.used / (1024**3), 1)
        mem_total = round(mem.total / (1024**3), 1)
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_used = round(disk.used / (1024**3), 1)
        disk_total = round(disk.total / (1024**3), 1)
        
        # Battery
        battery = psutil.sensors_battery()
        battery_str = f"{battery.percent}% ({'Charging' if battery.power_plugged else 'Battery'})" if battery else "N/A"
        
        # Network
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            logger.warning(f"Failed to get network info: {e}")
            hostname = "Unknown"
            ip = "Unknown"
        
        info = f"""💻 System Info:
• CPU: {cpu_percent}% usage ({cpu_count} cores)
• RAM: {mem_used}GB / {mem_total}GB ({mem.percent}%)
• Disk: {disk_used}GB / {disk_total}GB ({disk.percent}%)  
• Battery: {battery_str}
• PC: {hostname} | IP: {ip}
• OS: {platform.system()} {platform.release()}"""
        
        return info
        
    except Exception as e:
        return f"❌ System info nahi mil paayi: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SCREENSHOT & WALLPAPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def take_screenshot_and_save() -> str:
    """Take a screenshot and save it to Desktop."""
    try:
        from PIL import ImageGrab
        
        screenshot = ImageGrab.grab()
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"Screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(desktop, filename)
        screenshot.save(filepath, "PNG")
        
        return f"✅ Screenshot saved: {filename} (Desktop pe)"
        
    except Exception as e:
        return f"❌ Screenshot failed: {e}"


def set_wallpaper(image_path: str) -> str:
    """Change desktop wallpaper (Windows)."""
    if not os.path.exists(image_path):
        return f"❌ Image nahi mili: {image_path}"
    
    try:
        if platform.system() == 'Windows':
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(image_path), 3)
            return "✅ Wallpaper change kar diya!"
        else:
            return "❌ Wallpaper change sirf Windows pe support hai"
    except Exception as e:
        return f"❌ Wallpaper change nahi hua: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SHUTDOWN / RESTART / SLEEP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def shutdown_timer(minutes: int = 0) -> str:
    """Schedule system shutdown."""
    try:
        seconds = int(minutes) * 60
        # Validate input to prevent abuse
        if seconds < 0 or seconds > 3600:  # Max 1 hour
            return "❌ Invalid shutdown time. Use 0-60 minutes."
            
        if platform.system() == 'Windows':
            if seconds == 0:
                result = subprocess.run(["shutdown", "/s", "/t", "60"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return "✅ System 1 minute mein shutdown hoga. Cancel: 'shutdown cancel'"
            else:
                result = subprocess.run(["shutdown", "/s", "/t", str(seconds)], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return f"✅ System {minutes} minutes mein shutdown hoga!"
        return "❌ Sirf Windows pe support hai"
    except subprocess.TimeoutExpired:
        return "❌ Shutdown command timed out"
    except Exception as e:
        logger.error(f"Shutdown schedule failed: {e}")
        return f"❌ Shutdown schedule fail: {e}"


def cancel_shutdown() -> str:
    """Cancel scheduled shutdown."""
    try:
        result = subprocess.run(["shutdown", "/a"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return "✅ Shutdown cancel kar diya!"
        else:
            return "❌ Shutdown cancel nahi hua"
    except subprocess.TimeoutExpired:
        return "❌ Cancel command timed out"
    except Exception as e:
        logger.error(f"Failed to cancel shutdown: {e}")
        return "❌ Shutdown cancel nahi hua"


def restart_system() -> str:
    """Restart the computer."""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(["shutdown", "/r", "/t", "60"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "✅ System 1 minute mein restart hoga!"
        return "❌ Sirf Windows pe support hai"
    except subprocess.TimeoutExpired:
        return "❌ Restart command timed out"
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        return f"❌ Restart fail: {e}"


def sleep_system() -> str:
    """Put the system to sleep."""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return "✅ System sleep mode mein ja raha hai!"
        return "❌ Sirf Windows pe support hai"
    except subprocess.TimeoutExpired:
        return "❌ Sleep command timed out"
    except Exception as e:
        logger.error(f"Sleep failed: {e}")
        return f"❌ Sleep fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EMAIL & COMMUNICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draft_email(to: str = "", subject: str = "", body: str = "") -> str:
    """
    Open default email client with pre-filled draft.
    Uses mailto: URI.
    """
    try:
        mailto_parts = []
        if subject:
            mailto_parts.append(f"subject={urllib.parse.quote(subject)}")
        if body:
            mailto_parts.append(f"body={urllib.parse.quote(body)}")
        
        mailto_url = f"mailto:{to}"
        if mailto_parts:
            mailto_url += "?" + "&".join(mailto_parts)
        
        webbrowser.open(mailto_url)
        return f"✅ Email draft khol diya for {to}!"
        
    except Exception as e:
        return f"❌ Email draft fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  RECYCLE BIN & MAINTENANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def empty_recycle_bin() -> str:
    """Empty the Windows recycle bin."""
    try:
        if platform.system() == 'Windows':
            winshell = None
            try:
                import winshell
                winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
                return "✅ Recycle Bin saaf kar diya!"
            except ImportError:
                # Fallback using PowerShell
                subprocess.run(
                    ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                    capture_output=True, creationflags=0x08000000
                )
                return "✅ Recycle Bin saaf kar diya!"
        return "❌ Sirf Windows pe support hai"
    except Exception as e:
        return f"❌ Recycle bin clear nahi hua: {e}"


def clear_temp_files() -> str:
    """Clear temporary files to free up space."""
    try:
        temp_dir = tempfile.gettempdir()
        count = 0
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                    count += 1
            except:
                pass
        
        return f"✅ {count} temp files/folders cleaned!"
        
    except Exception as e:
        return f"❌ Temp cleanup fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BRIGHTNESS CONTROL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def set_brightness(level):
    """Set screen brightness (0-100). Works on laptops."""
    try:
        level = max(0, min(100, int(level)))
        if platform.system() == 'Windows':
            subprocess.run(
                ["powershell", "-Command", 
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"],
                capture_output=True, creationflags=0x08000000
            )
            return f"✅ Brightness set to {level}%"
        return "❌ Sirf Windows laptop pe support hai"
    except Exception as e:
        return f"❌ Brightness set nahi hua: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WIFI CONTROL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_wifi_info():
    """Get current WiFi connection info."""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, creationflags=0x08000000
            )
            
            lines = result.stdout.strip().split('\n')
            info = {}
            for line in lines:
                if ':' in line:
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip()
                    if key in ['SSID', 'Signal', 'State', 'Radio type']:
                        info[key] = value
            
            if info:
                ssid = info.get('SSID', 'Unknown')
                signal = info.get('Signal', 'Unknown')
                state = info.get('State', 'Unknown')
                return f"📶 WiFi: {ssid} | Signal: {signal} | Status: {state}"
            
            return "📶 WiFi info not available"
        return "❌ Sirf Windows pe support hai"
    except Exception as e:
        return f"❌ WiFi info fail: {e}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INTELLIGENT PC SCRIPTING (AUTOMATION)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_and_run_script(prompt_text):
    """
    Intelligently generates a Python script based on user prompt,
    saves it to a temp file, executes it, and returns the result.
    Example: 'backup my desktop files to D drive'
    """
    try:
        from . import logger
        script_logger = logger.get_logger("OS_Automation_Scripting")
        from google import genai
        
        script_logger.info(f"Generating automation script for: {prompt_text}")
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
             return "❌ GEMINI_API_KEY not found in .env"
             
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 1. Ask Gemini to write only the pure Python code
        system_prompt = """You are a Python script generator for a Windows PC.
Your task is to write a Python script that accomplishes the user's request explicitly.
You MUST output ONLY valid Python code, nothing else. No markdown blocks, no explanations.
If the request requires directory paths, assume standard Windows paths like os.path.expanduser('~') or dynamic paths.
Ensure the script prints the result using standard print() so the output can be captured."""
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=system_prompt + "\n\nUser Request: " + prompt_text
        )
        code = response.text.strip()
        
        # Clean up markdown if Gemini still adds it
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines)
            code = code.strip()
            
        script_logger.debug(f"Generated Code:\n{code}")
        
        # 2. Save script to a temp file
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="sia_automation_")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # 3. Execute the script
        script_logger.info(f"Executing temporary script: {temp_path}")
        result = subprocess.run([sys.executable, temp_path], capture_output=True, text=True, timeout=30)
        
        # 4. Cleanup
        try:
            os.remove(temp_path)
        except Exception as e:
            script_logger.error(f"Failed to delete temp script {temp_path}: {e}")
            
        # 5. Return result
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                output = "Code successfully executed, returning no visible output."
            return f"✅ Automation script chala diya, result:\n{output}"
        else:
            return f"❌ Script mein error aa gaya:\n{result.stderr.strip()}"
            
    except ImportError:
        return "❌ Google Generative AI module config theek nahi hai."
    except Exception as e:
        return f"❌ Automation trigger fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW: SMART LIFESTYLE MACROS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def launch_coding_env():
    """
    Coding Environment Macro:
    Opens VS Code + Chrome with StackOverflow + YouTube (lofi music).
    The ultimate productivity setup for developers!
    """
    results = []
    CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

    # 1. Open VS Code
    try:
        subprocess.Popen(["code"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0)
        results.append("VS Code ✅")
    except Exception:
        results.append("VS Code ❌ (not in PATH)")

    # 2. Open StackOverflow in default browser
    try:
        time.sleep(0.5)
        webbrowser.open("https://stackoverflow.com")
        results.append("StackOverflow ✅")
    except Exception:
        results.append("StackOverflow ❌")

    # 3. Open lofi music for coding
    try:
        time.sleep(0.5)
        webbrowser.open("https://www.youtube.com/results?search_query=lofi+music+for+coding")
        results.append("Music ✅")
    except Exception:
        results.append("Music ❌")

    summary = " | ".join(results)
    return f"🚀 Coding Environment Ready! {summary}"


def open_work_mode():
    """
    Work Mode Macro:
    Opens Gmail + GitHub + VS Code for a productive work session.
    """
    results = []
    CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

    try:
        webbrowser.open("https://mail.google.com")
        results.append("Gmail ✅")
    except Exception:
        results.append("Gmail ❌")

    try:
        time.sleep(0.4)
        webbrowser.open("https://github.com")
        results.append("GitHub ✅")
    except Exception:
        results.append("GitHub ❌")

    try:
        time.sleep(0.4)
        subprocess.Popen(["code"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0)
        results.append("VS Code ✅")
    except Exception:
        results.append("VS Code ❌")

    summary = " | ".join(results)
    return f"💼 Work Mode ON! {summary}"


def open_whatsapp_web():
    """Open WhatsApp Web in the default browser."""
    try:
        webbrowser.open("https://web.whatsapp.com")
        return "✅ WhatsApp Web khol diya! Browser mein QR scan karo agar nahi hua auto-login."
    except Exception as e:
        return f"❌ WhatsApp Web nahi khula: {e}"


def send_whatsapp_message(contact_hint, message):
    """
    Open WhatsApp Web pre-filled with a message using wa.me link.
    Note: This works best when logged into WhatsApp Web already.
    contact_hint: phone number WITH country code (e.g., '919876543210')
                  or just open WhatsApp Web if not a number.
    """
    try:
        import re as _re
        # Check if contact_hint looks like a phone number
        digits_only = _re.sub(r'\D', '', contact_hint)
        if len(digits_only) >= 10:
            # Use wa.me for direct link
            encoded_msg = urllib.parse.quote(message)
            wa_url = f"https://wa.me/{digits_only}?text={encoded_msg}"
            webbrowser.open(wa_url)
            return f"✅ WhatsApp message ready kar diya! '{message[:40]}...' → {contact_hint}"
        else:
            # Just open WhatsApp Web
            webbrowser.open("https://web.whatsapp.com")
            return f"✅ WhatsApp Web khola. '{contact_hint}' ko manually search karo aur ye message bhejo: {message}"
    except Exception as e:
        return f"❌ WhatsApp message nahi bheja: {e}"
