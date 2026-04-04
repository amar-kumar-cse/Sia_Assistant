"""
Sia Proactive Engine — System Health Monitor
Watches battery, CPU, RAM, and reminds Amar to take breaks.
"""

import psutil
import time
import threading
from datetime import datetime
import platform

# Win32 context awareness (fullscreen detection)
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
    print("[Sia Proactive Engine]: pywin32 not available. Fullscreen detection disabled.")


class SiaProactiveEngine:
    def __init__(self, speak_function, show_toast_function=None):
        self.speak = speak_function
        self.show_toast = show_toast_function

        # ── Alert timestamps & flags ──────────────────────────────────
        self.last_battery_alert = 0
        self.last_break_alert = time.time()
        self.last_cpu_alert = 0
        self.last_ram_alert = 0
        self.last_temp_alert = 0

        # CPU sustained-high tracking
        self._cpu_high_since: float = 0.0      # timestamp when CPU first crossed 85%
        self._cpu_alerted: bool = False         # did we already alert this episode?

        # Morning greeting
        self.has_greeted_morning = False

        self.is_running = True
        self._monitor_thread = None

    # ─────────────────────────────────────────────────────────────────
    #  FULLSCREEN DETECTION
    # ─────────────────────────────────────────────────────────────────

    def is_fullscreen_app_active(self) -> bool:
        """Return True if the foreground window occupies the entire screen."""
        if not CONTEXT_AWARENESS_AVAILABLE:
            return False
        try:
            hwnd = win32gui.GetForegroundWindow()
            rect = win32gui.GetWindowRect(hwnd)
            sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            if (rect[2] - rect[0]) >= sw and (rect[3] - rect[1]) >= sh:
                class_name = win32gui.GetClassName(hwnd)
                if class_name in ("Progman", "WorkerW"):
                    return False
                return True
        except Exception:
            pass
        return False

    # ─────────────────────────────────────────────────────────────────
    #  NOTIFICATION DISPATCHER
    # ─────────────────────────────────────────────────────────────────

    def _notify(self, message: str, priority: str = "Gentle"):
        """Context-aware notification: mute during fullscreen unless Critical."""
        # Always show toast (non-intrusive)
        if self.show_toast:
            self.show_toast(message)

        # Don't interrupt fullscreen apps (games/movies) unless critical
        if self.is_fullscreen_app_active() and priority != "Critical":
            print(f"[Proactive Engine - Muted (fullscreen)]: {message}")
            return

        if self.speak:
            self.speak(message)

    # ─────────────────────────────────────────────────────────────────
    #  BATTERY CHECK
    # ─────────────────────────────────────────────────────────────────

    def _check_battery(self, now: float):
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return
            percent = battery.percent
            plugged = battery.power_plugged

            if percent <= 10 and not plugged:
                if now - self.last_battery_alert > 300:   # every 5 min
                    self._notify(
                        "Arre Hero! Battery sirf 10% bachi hai aur charger nahi lagi! "
                        "Abhi laga do warna system band ho jayega! 🔋",
                        priority="Critical"
                    )
                    self.last_battery_alert = now

            elif percent <= 20 and not plugged:
                if now - self.last_battery_alert > 900:   # every 15 min
                    self._notify(
                        "Hero, battery 20% se kam hai yaar. "
                        "Charger lagao please, kaam ruka nahi chahiye! 🔌"
                    )
                    self.last_battery_alert = now

        except Exception as e:
            print(f"[Proactive Engine]: Battery check error: {e}")

    # ─────────────────────────────────────────────────────────────────
    #  CPU USAGE CHECK  ← NEW
    # ─────────────────────────────────────────────────────────────────

    def _check_cpu(self, now: float):
        """
        Alert if CPU stays above 85% for more than 90 seconds.
        Reset alert flag once CPU drops below 60%.
        """
        try:
            cpu = psutil.cpu_percent(interval=None)   # non-blocking (uses last sample)

            if cpu >= 85:
                if self._cpu_high_since == 0.0:
                    self._cpu_high_since = now          # start the timer

                elapsed = now - self._cpu_high_since
                if elapsed >= 90 and not self._cpu_alerted:
                    if now - self.last_cpu_alert > 600:  # max once per 10 min
                        self._notify(
                            f"Bhai, PC ka CPU {int(cpu)}% pe chal raha hai! 🔥 "
                            "Koi heavy process chal raha lagta hai — "
                            "Task Manager check karo ya thoda break lo!",
                            priority="Gentle"
                        )
                        self.last_cpu_alert = now
                    self._cpu_alerted = True

            elif cpu < 60:
                # CPU cooled down — reset tracking
                self._cpu_high_since = 0.0
                self._cpu_alerted = False

        except Exception as e:
            print(f"[Proactive Engine]: CPU check error: {e}")

    # ─────────────────────────────────────────────────────────────────
    #  RAM USAGE CHECK  ← NEW
    # ─────────────────────────────────────────────────────────────────

    def _check_ram(self, now: float):
        """Alert if RAM usage is above 90%."""
        try:
            ram = psutil.virtual_memory()
            if ram.percent >= 90:
                if now - self.last_ram_alert > 1200:   # max once per 20 min
                    used_gb = ram.used / (1024 ** 3)
                    total_gb = ram.total / (1024 ** 3)
                    self._notify(
                        f"Hero, RAM {int(ram.percent)}% full hai "
                        f"({used_gb:.1f}/{total_gb:.1f} GB)! 💾 "
                        "Browser ke extra tabs band karo ya koi bhari app close karo yaar.",
                        priority="Gentle"
                    )
                    self.last_ram_alert = now
        except Exception as e:
            print(f"[Proactive Engine]: RAM check error: {e}")

    # ─────────────────────────────────────────────────────────────────
    #  CPU TEMPERATURE CHECK  ← NEW
    # ─────────────────────────────────────────────────────────────────

    def _check_temperature(self, now: float):
        """Alert if CPU temperature is dangerously high (>90°C)."""
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return   # not available on most Windows setups

            for sensor_name, readings in temps.items():
                for reading in readings:
                    if reading.current and reading.current >= 90:
                        if now - self.last_temp_alert > 600:
                            self._notify(
                                f"Arre Hero, CPU temperature {int(reading.current)}°C hai! 🌡️ "
                                "Laptop ko kisi hard surface pe mat rakho. "
                                "Cooling pad use karo ya thoda band karo!",
                                priority="Critical"
                            )
                            self.last_temp_alert = now
                        return
        except Exception:
            pass   # sensors_temperatures() may not work on all Windows configs

    # ─────────────────────────────────────────────────────────────────
    #  BREAK / WATER REMINDER
    # ─────────────────────────────────────────────────────────────────

    def _check_break(self, now: datetime, current_time: float):
        """Remind Amar to take a break every hour (on the hour)."""
        if now.minute == 0 and now.second < 30:
            if current_time - self.last_break_alert >= 3500:
                self._notify(
                    f"Hero, {now.hour} baj gaye! ⏰ "
                    "Thoda break lo, stretch karo, paani piyo. "
                    "Self-care bhi important hai yaar! 💧"
                )
                self.last_break_alert = current_time

    # ─────────────────────────────────────────────────────────────────
    #  MORNING GREETING
    # ─────────────────────────────────────────────────────────────────

    def _check_morning_greeting(self, now: datetime):
        if 8 <= now.hour <= 11 and not self.has_greeted_morning:
            self.has_greeted_morning = True
            self._notify(
                "Good Morning Amar! ☀️ "
                "Main system scan complete kar chuki hoon. "
                "Aaj bhi kuch kamaal karte hain! 🚀",
                priority="Gentle"
            )

    # ─────────────────────────────────────────────────────────────────
    #  MAIN MONITOR LOOP
    # ─────────────────────────────────────────────────────────────────

    def check_system_health(self):
        """Background loop that checks everything every 30 seconds."""
        # Prime the CPU percentage sampler (first call always returns 0)
        psutil.cpu_percent(interval=None)

        while self.is_running:
            try:
                current_time = time.time()
                now = datetime.now()

                self._check_morning_greeting(now)
                self._check_battery(current_time)
                self._check_cpu(current_time)
                self._check_ram(current_time)
                self._check_temperature(current_time)
                self._check_break(now, current_time)

            except Exception as e:
                print(f"[Proactive Engine]: Unexpected error in monitor loop: {e}")

            time.sleep(30)

    def stop(self):
        self.is_running = False

    def start(self):
        self._monitor_thread = threading.Thread(
            target=self.check_system_health, daemon=True
        )
        self._monitor_thread.start()
        print("[Sia Proactive Engine]: Proactive Monitor started.")


