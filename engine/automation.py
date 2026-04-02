import psutil
import time
import threading
from datetime import datetime
import platform

# Context Awareness
try:
    if platform.system() == "Windows":
        import win32gui
        import win32api
        import win32con
        CONTEXT_AWARENESS_AVAILABLE = True
    else:
        CONTEXT_AWARENESS_AVAILABLE = False
except ImportError:
    CONTEXT_AWARENESS_AVAILABLE = False
    print("[Sia Proactive Engine]: pywin32 not available. Context awareness (fullscreen detection) disabled.")

class SiaProactiveEngine:
    def __init__(self, speak_function, show_toast_function=None):
        self.speak = speak_function
        self.show_toast = show_toast_function
        self.last_battery_alert = 0
        self.last_break_alert = time.time()
        self.has_greeted_morning = False
        self.is_running = True

    def is_fullscreen_app_active(self):
        """Checks if the active window is full-screen."""
        if not CONTEXT_AWARENESS_AVAILABLE:
            return False
            
        try:
            hwnd = win32gui.GetForegroundWindow()
            rect = win32gui.GetWindowRect(hwnd)
            
            # Screen dimensions
            screen_x = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_y = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            # If active window takes up the whole screen, it's likely a game/movie
            if width >= screen_x and height >= screen_y:
                # We skip checking taskbar classes etc. to be safe
                # Don't interrupt if it's fullscreen
                # Exception: Desktop is technically not full screen app for interrupting, it's progman
                class_name = win32gui.GetClassName(hwnd)
                if class_name in ['Progman', 'WorkerW']:
                    return False
                return True
        except Exception:
            pass
        return False
        
    def _notify(self, message, priority="Gentle"):
        """Handles context-aware notification sending."""
        is_busy = self.is_fullscreen_app_active()
        
        # Show toast no matter what, as it's non-intrusive
        if self.show_toast:
            self.show_toast(message)
            
        if is_busy and priority != "Critical":
            # Don't speak if watching movie/playing game, unless Critical
            print(f"[Proactive Engine - Muted due to FullScreen]: {message}")
            return
            
        if self.speak:
            self.speak(message)

    def check_system_health(self):
        while self.is_running:
            current_time = time.time()
            now = datetime.now()
            
            # 1. First Boot Morning Greeting (Dynamic)
            if 8 <= now.hour <= 11 and not self.has_greeted_morning:
                self.has_greeted_morning = True
                self._notify("Good Morning Amar, aaj ka mausam achha lag raha hai, aur main system scan complete kar chuki hoon. Let's conquer the day!", priority="Gentle")
                time.sleep(5)  # Pause to avoid overlap

            # 2. Battery Check
            try:
                battery = psutil.sensors_battery()
                if battery:
                    percent = battery.percent
                    plugged = battery.power_plugged

                    # Critical Alert
                    if percent <= 10 and not plugged:
                        if current_time - self.last_battery_alert > 300: # Every 5 minutes for 10%
                            self._notify("Sir, Dhyan dijiye! Battery 10 percent se kam hai. System kisi bhi waqt band ho sakta hai, turant charger connect karein!", priority="Critical")
                            self.last_battery_alert = current_time
                    # Gentle Alert
                    elif percent <= 20 and not plugged:
                        if current_time - self.last_battery_alert > 900: # Every 15 mins for 20%
                            self._notify("Sir, aapki battery 20 percent se kam hai. Behtar hoga agar aap charger connect kar dein taaki kaam na ruke.", priority="Gentle")
                            self.last_battery_alert = current_time
            except Exception as e:
                print(f"[Proactive Engine Error]: Battery status check failed: {e}")

            # 3. Posture / Water Break
            # Hourly Time Update
            if now.minute == 0 and now.second < 30:
                if current_time - self.last_break_alert >= 3500: # Ensure we don't repeat in same minute
                    self._notify(f"Sir, abhi {now.hour} baj gaye hain. Thodi der break le lijiye, stretch kijiye, aur paani pi lijiye.", priority="Gentle")
                    self.last_break_alert = current_time

            # 4. CPU Temperature (Placeholder - psutil temperature sensors often don't work reliably on Windows)
            # Yahan hum thermal limits bhi check kar sakte hain if hwmon is mapped
            
            # Check every 30 seconds
            time.sleep(30)

    def start(self):
        monitor_thread = threading.Thread(target=self.check_system_health, daemon=True)
        monitor_thread.start()
        print("[Sia Proactive Engine]: Proactive Monitor started successfully.")
