"""
SIA - Floating Desktop Virtual Assistant v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Fix 1: Pure transparent floating window — no more "dabba"
✅ Fix 2: API auto-switching with live status display
✅ Fix 3: Sleek glassmorphism side panel (no vertical stack)
✅ Fix 4: Real lip-sync mouth animation (3-frame cycle)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Built for Amar — B.Tech CSE @ RIT Roorkee ❤️
"""

import sys
import os
import math
import random
import threading
import time
import traceback
import ctypes
import platform
import re
import json

from PyQt5.QtWidgets import (  # type: ignore[reportMissingImports]
    QApplication, QWidget, QLabel, QPushButton,
    QSystemTrayIcon, QMenu, QAction, QLineEdit,
    QGraphicsOpacityEffect, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSlider
)
from PyQt5.QtCore import (  # type: ignore[reportMissingImports]
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, QSize, QPoint, QPointF, QRectF
)
from PyQt5.QtGui import (  # type: ignore[reportMissingImports]
    QPixmap, QPainter, QColor, QFont, QFontDatabase, QIcon,
    QRadialGradient, QLinearGradient, QPainterPath, QPen, QBrush,
    QFontMetrics, QCursor, QRegion
)

# ── Backend imports ──────────────────────────────────────────
from engine import listen_engine, brain, voice_engine, actions, memory
from engine.automation import SiaProactiveEngine
from engine.animation_engine import AnimationEngine, AvatarState, BlendFrame   # blending engine
from engine.weather_widget import WeatherWidget
from engine.logger import get_logger

app_logger = get_logger("Sia_Desktop")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
CACHE_DIR = os.path.join(SCRIPT_DIR, "cache")

# Avatar window geometry
AVATAR_W     = 340       # avatar widget width
AVATAR_H     = 680       # avatar widget height
PANEL_W      = 112       # compact side panel width
PANEL_H      = 276       # compact side panel height
CANVAS_BOX_W = 760       # centered translucent canvas box width
CANVAS_BOX_H = 520       # centered translucent canvas box height
DOCK_W       = 170       # lower-right taskbar dock width
DOCK_H       = 62        # lower-right taskbar dock height
MARGIN       = 24        # edge margin from screen border

# Color palette
NEON_CYAN   = QColor(0, 255, 204)
NEON_PINK   = QColor(255, 60, 170)
NEON_BLUE   = QColor(50, 140, 255)
GLASS_BG    = QColor(8, 8, 22, 210)
GLASS_BORDER= QColor(0, 255, 204, 60)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BACKGROUND THREADS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WakeWordThread(QThread):
    """Seamless continuous listening thread."""
    text_recognized = pyqtSignal(str)
    status_changed  = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused  = False

    def run(self):
        from engine import listen_engine
        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue

            self.status_changed.emit("listening")
            try:
                text = listen_engine.listen()
                if text and not self.paused:
                    self.paused = True
                    self.text_recognized.emit(text)
            except Exception as e:
                app_logger.error(f"WakeWordThread error: {e}")
                time.sleep(1)

    def resume(self):
        self.paused = False

    def stop(self):
        """Gracefully stop."""
        self.running = False
        self.paused = False
        self.wait(3000)
        if self.isRunning():
            self.terminate()
            self.wait(1000)

import queue

class ThinkThread(QThread):
    response_ready = pyqtSignal(str)
    chunk_ready = pyqtSignal(str)

    def __init__(self, user_text, parent=None):
        super().__init__(parent)
        self.user_text = user_text

    def run(self):
        action_result = actions.perform_action(self.user_text)
        if action_result:
            self.chunk_ready.emit(action_result)
            self.response_ready.emit(action_result)
            return
        
        full_response = ""
        try:
            for chunk in brain.think_streaming(self.user_text):
                if chunk:
                    full_response += chunk
                    self.chunk_ready.emit(chunk)
        except Exception as e:
            app_logger.error(f"Streaming error: {e}")
            if not full_response:
                full_response = "Mujhe kuch network issue aa raha hai."
                self.chunk_ready.emit(full_response)
                
        self.response_ready.emit(full_response)

class AudioStreamThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.q = queue.Queue()
        self.running = True
        self.is_first = True

    def enqueue(self, text):
        self.q.put(text)

    def stop(self):
        self.running = False
        self.q.put("<STOP>")

    def run(self):
        while self.running:
            try:
                text = self.q.get(timeout=0.1)
                if text == "<STOP>":
                    break
                voice_engine.speak_chunk(text, self.is_first)
                self.is_first = False
            except queue.Empty:
                pass
        voice_engine.finish_streaming()


class SpeakThread(QThread):
    speaking_started  = pyqtSignal()
    speaking_finished = pyqtSignal()

    def __init__(self, text, emotion=None, parent=None):
        super().__init__(parent)
        self.text    = text
        self.emotion = emotion

    def run(self):
        self.speaking_started.emit()
        voice_engine.speak(self.text, emotion=self.emotion)
        self.speaking_finished.emit()


class ProactiveVisionThread(QThread):
    result_ready = pyqtSignal(str)

    def run(self):
        try:
            from engine import vision_engine
            prompt = (
                "You are Sia, Amar's helpful and fun AI companion. "
                "Look closely at the screen. What is Amar doing currently? (e.g. coding, watching a movie, browsing). "
                "Give exactly a 1-sentence proactive, caring, or playful Hinglish voice line acknowledging it."
            )
            result = vision_engine.analyze_screen(prompt)
            self.result_ready.emit(result)
        except Exception as e:
            app_logger.error(f"Proactive vision error: {e}")


class ApiStatusThread(QThread):
    """Polls brain.get_api_status() every 10 s and emits the result."""
    status_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        while self.running:
            try:
                status = brain.get_api_status()
                self.status_updated.emit(status)
            except Exception:
                pass
            time.sleep(10)

    def stop(self):
        self.running = False


class ToastNotification(QWidget):
    """Small fade-in/out toast used for proactive Sia nudges."""

    def __init__(self, text: str, duration_ms: int = 3600, parent=None):
        super().__init__(parent)
        self.duration_ms = max(1200, int(duration_ms))
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(
            "QLabel {"
            " background: rgba(8, 14, 26, 225);"
            " color: #E8FFFC;"
            " border: 1px solid rgba(0,255,204,0.38);"
            " border-radius: 10px;"
            " padding: 8px 10px;"
            " font-family: 'Segoe UI';"
            " font-size: 10px;"
            "}"
        )
        layout.addWidget(label)

        self.resize(280, 78)

    def show_toast(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 24
        y = screen.bottom() - self.height() - 30
        self.move(x, y)
        self.show()

        self._fade_in = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

        QTimer.singleShot(self.duration_ms, self._fade_out_and_close)

    def _fade_out_and_close(self):
        self._fade_out = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self._fade_out.setDuration(260)
        self._fade_out.setStartValue(self.opacity_effect.opacity())
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.close)
        self._fade_out.start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLASSMORPHISM SIDE PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SiaDesktop(QWidget):
    """
    Floating transparent avatar widget.
    ✅ No full-screen background
    ✅ Wallpaper visible behind her
    ✅ Draggable
    ✅ Lip-sync mouth animation
    """


    def __init__(self):
        super().__init__()

        # ── State ──
        self.current_state = "idle"
        self.bubble_text   = ""
        self.bubble_display_text = ""
        self.typewriter_index    = 0

        # ── Animation Engine (NEW: replaces manual tick/breath vars) ──
        self.anim_engine   = AnimationEngine()
        # Keep compat aliases so existing paintEvent code still works
        self.tick          = 0.0         # updated from anim_engine in _animation_tick
        self.breath_offset = 0.0

        self.character_pixmap  = None
        self.character_rect    = QRect()
        self.blink_pixmap      = None    # NEW: blink frame
        self.lip_pixmaps       = []
        self.lip_frame_index   = 0
        self.lip_tick_counter  = 0
        self.lip_tick_speed    = 2

        self.current_mood      = "DEFAULT"
        self.is_on_top         = True
        self.weather_widget_ref = None
        self._last_vision_mode = "cloud"
        self._last_vision_notice_ts = 0.0
        self._compact_overlay_ui = False

        # Drag support
        self._drag_pos = None

        # Thread refs
        self.listen_thread = None
        self.think_thread  = None
        self.speak_thread  = None
        self.vision_thread = None
        self.search_thread = None
        self.wake_thread   = None

        self._active_toasts = []

        # ── Resources ──
        self._load_character()
        self._validate_avatar_assets()

        # ── Window flags: frameless, transparent, always-on-top ──
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")

        # ── Size & position: fullscreen and centered ──
        self._set_fullscreen_center()

        # Listen for screen geometry changes (multi-monitor, resize, etc.)
        app = QApplication.instance()
        if app:
            app.primaryScreen().geometryChanged.connect(self._set_fullscreen_center)

    def _set_fullscreen_center(self):
        """Force window to fullscreen and center avatar live."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        # Optionally, force always-on-top again (sometimes lost on Windows)
        self.setWindowState(Qt.WindowActive)
        self.raise_()
        self.activateWindow()

        # ── Breathing Logic (Sine-Wave Motion) ──
        # time_counter is in seconds, frequency is radians/sec.
        self.base_y = self.y()
        self.amplitude = 4.0
        self.breath_period = 2.6
        self.frequency = (2.0 * math.pi) / self.breath_period
        self.time_counter = 0.0
        self.breathing_offset_y = 0.0
        self.breathing_offset_x = 0.0
        self.live_scale = 1.0
        self.live_shadow_scale = 1.0
        self.head_tilt_deg = 0.0
        self.parallax_strength = 0.0
        self.micro_jitter_x = 0.0
        self.micro_jitter_y = 0.0
        self._jitter_decay = 0.0
        self._next_jitter_at = time.time() + random.uniform(1.2, 2.8)
        self._breathing_last_ts = time.time()
        self.motion_mode = "auto-switch"
        self.realism_level = 78
        self.realism_slider_window = None
        self.realism_value_label = None
        self._realism_autohide_timer = QTimer(self)
        self._realism_autohide_timer.setSingleShot(True)
        self._realism_autohide_timer.timeout.connect(self._auto_close_realism_slider)
        self._motion_settings_path = os.path.join(CACHE_DIR, "motion_settings.json")
        self._tray_hint_path = os.path.join(CACHE_DIR, ".tray_hint_seen")
        self.motion_profiles = {
            "calm": {
                "amp": 3.2,
                "x_sway": 0.75,
                "scale": 0.006,
                "talk_boost": 0.35,
                "tilt": 0.55,
                "jitter": 0.45,
                "parallax": 0.7,
            },
            "expressive": {
                "amp": 5.0,
                "x_sway": 1.45,
                "scale": 0.013,
                "talk_boost": 1.1,
                "tilt": 1.05,
                "jitter": 0.9,
                "parallax": 1.7,
            },
            "auto-switch": {
                "amp": 4.2,
                "x_sway": 1.15,
                "scale": 0.010,
                "talk_boost": 0.8,
                "tilt": 0.8,
                "jitter": 0.7,
                "parallax": 1.2,
            },
        }

        self._load_motion_settings()
        
        self.breathing_loop_timer = QTimer(self)
        self.breathing_loop_timer.timeout.connect(self._breathing_loop)
        self.breathing_loop_timer.start(50) # equivalent to Tkinter .after(50, self._breathing_loop)

        # ── Win32 DWM transparency (removes remnant halo) ──
        self._apply_win32_transparency()

        # ── Status bar (small label at bottom of avatar widget) ──
        self.status_label = QLabel("💤 Say 'Sia'...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 170);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 10px;
                border: 1px solid rgba(0,255,204,0.3);
            }
        """)
        self.status_label.adjustSize()
        self._position_status_label()

        self.vision_mode_label = QLabel("📷 Vision: Cloud", self)
        self.vision_mode_label.setAlignment(Qt.AlignCenter)
        self.vision_mode_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 40, 30, 165);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                padding: 3px 8px;
                border-radius: 9px;
                border: 1px solid rgba(0,255,204,0.35);
            }
        """)
        self.vision_mode_label.adjustSize()

        self.motion_mode_label = QLabel("🎬 Motion: Auto | 78%", self)
        self.motion_mode_label.setAlignment(Qt.AlignCenter)
        self.motion_mode_label.setStyleSheet("""
            QLabel {
                background: rgba(18, 24, 42, 165);
                color: #9AFBFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                padding: 3px 8px;
                border-radius: 9px;
                border: 1px solid rgba(154,251,255,0.32);
            }
        """)
        self.motion_mode_label.adjustSize()

        self._update_motion_badge()
        self._refresh_overlay_layout_mode()
        self._position_status_label()

        # ── Side Panel & Dock (Removed for Center Overlay Mode) ──

        # ── Timers ──
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self._typewriter_tick)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animation_tick)
        self.anim_timer.start(50)   # 20 FPS

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._check_idle_fade)
        self.idle_timer.start(1000)

        self.last_active_time = time.time()
        self.opacity_effect   = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.target_opacity   = 1.0
        self.current_opacity  = 1.0

        # ── Proactive Engine ──
        self.proactive_engine = SiaProactiveEngine(
            speak_function=self._proactive_speak,
            show_toast_function=self._show_proactive_toast
        )
        self.proactive_engine.start()

        # ── 5-Minute Proactive Vision Loop ──
        self.proactive_vision_timer = QTimer(self)
        self.proactive_vision_timer.timeout.connect(self._run_proactive_vision_loop)
        self.proactive_vision_timer.start(300000)  # 5 minutes (300,000 ms)

        # ── API Status polling ──
        self.api_status_thread = ApiStatusThread()
        self.api_status_thread.status_updated.connect(self._on_api_status_updated)
        self.api_status_thread.start()

        # ── Memory preload ──
        try:
            memory.preload_cache()
        except Exception as e:
            app_logger.warning(f"Memory preload skipped: {e}")

        # ── System Tray ──
        self._create_system_tray()

        # ── Wake Word Thread ──
        self.wake_thread = WakeWordThread()
        self.wake_thread.text_recognized.connect(self._on_seamless_text)
        self.wake_thread.status_changed.connect(self._on_status_change)
        self.wake_thread.start()

        # ── Voice Interrupt Monitor (VAD) ──
        try:
            from engine.listen_engine import VoiceInterruptMonitor
            self.vad_monitor = VoiceInterruptMonitor(
                interrupt_callback=self._on_user_interrupt,
                is_speaking_fn=voice_engine.get_speaking_state,
                rms_threshold=1200,
            )
            self.vad_monitor.start()
            app_logger.info("[VAD Monitor] Voice interruption active.")
        except Exception as e:
            app_logger.warning(f"[VAD Monitor] Could not start: {e}")
            self.vad_monitor = None

        # ── Greeting ──
        hour = time.localtime().tm_hour
        if 5  <= hour < 12: g = "Good Morning Hero! ☀️ Aaj ka din amazing hoga! 💪"
        elif 12 <= hour < 17: g = "Good Afternoon Hero! 🌤️ Kuch khaaya? 😊"
        elif 17 <= hour < 21: g = "Good Evening Hero! 🌙 Kaisa raha din? ❤️"
        else:                  g = "Itni raat ko jaag rahe ho? Take care yaar! 💤"
        self._show_bubble(f"Sia ❤️: {g}")

        self.show()
        self._show_startup_self_check_toast()
        app_logger.info("✅ Sia Desktop v3.0 is LIVE!")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_overlay_layout_mode()
        self._position_status_label()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ASSETS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_character(self, emotion="IDLE"):
        """Load avatar frame for given emotion with strict v1 fallback behavior."""
        emotion_files = {
            "IDLE": ["sia_idle.png"],
            "SMILE": ["sia_happy.png", "Sia_open.png", "sia_idle.png"],
            "HAPPY": ["sia_happy.png", "Sia_open.png", "sia_idle.png"],
            "SAD": ["sia_sad.png", "sia_idle.png"],
            "CONCERNED": ["sia_sad.png", "sia_idle.png"],
            "CONFUSED": ["sia_think.png", "Sia_semi.png", "sia_idle.png"],
            "THINKING": ["sia_think.png", "Sia_semi.png", "sia_idle.png"],
            "SURPRISED": ["sia_surprise.png", "Sia_open.png", "sia_idle.png"],
            "ANGRY": ["sia_sad.png", "sia_idle.png"],
        }

        def _load_first_available(candidates):
            for fn in candidates:
                for base in [ASSETS_DIR, SCRIPT_DIR]:
                    path = os.path.join(base, fn)
                    if os.path.exists(path):
                        px = QPixmap(path)
                        if not px.isNull():
                            return px
            return None

        selected = _load_first_available(emotion_files.get(emotion.upper(), ["sia_idle.png"]))
        if selected is not None:
            self.character_pixmap = selected
        elif self.character_pixmap is None:
            self.character_pixmap = QPixmap()
            app_logger.warning("⚠️ Avatar frame missing for emotion=%s; fallback to empty pixmap", emotion)

        # Cache lip-sync frames once
        if not self.lip_pixmaps:
            lip_candidates = [
                ["sia_talk_closed.png", "sia_idle.png"],
                ["sia_talk_semi.png", "Sia_semi.png", "sia_idle.png"],
                ["sia_talk_open.png", "Sia_open.png", "sia_idle.png"],
            ]
            for candidates in lip_candidates:
                lp = _load_first_available(candidates)
                if lp is None and self.character_pixmap:
                    lp = self.character_pixmap
                self.lip_pixmaps.append(lp)
            app_logger.info(f"✅ Lip-sync frames: {len(self.lip_pixmaps)} loaded")

        # Load blink frame (NEW)
        if self.blink_pixmap is None:
            bp = _load_first_available(["sia_blink.png", "sia_idle.png"])
            self.blink_pixmap = bp if bp is not None else self.character_pixmap
            app_logger.info("✅ Blink frame loaded" if bp is not None else "⚠️  Blink frame not found, using idle")

    def _validate_avatar_assets(self):
        """Validate minimum v1 avatar frame set and log explicit missing states."""
        required = {
            "idle": ["sia_idle.png"],
            "blink": ["sia_blink.png"],
            "talk_closed": ["sia_talk_closed.png", "sia_idle.png"],
            "talk_semi": ["sia_talk_semi.png", "Sia_semi.png"],
            "talk_open": ["sia_talk_open.png", "Sia_open.png"],
            "happy": ["sia_happy.png", "Sia_open.png"],
            "sad": ["sia_sad.png", "sia_idle.png"],
            "think": ["sia_think.png", "Sia_semi.png"],
            "surprise": ["sia_surprise.png", "Sia_open.png"],
        }

        missing = []
        for state, candidates in required.items():
            found = False
            for fn in candidates:
                for base in [ASSETS_DIR, SCRIPT_DIR]:
                    if os.path.exists(os.path.join(base, fn)):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append(state)

        if missing:
            app_logger.warning("⚠️ Avatar asset gaps for states: %s (fallback mode active)", ", ".join(missing))
        else:
            app_logger.info("✅ Avatar v1 frame set validated")

    def _apply_win32_transparency(self):
        """Remove DWM halo border (Windows only)."""
        if platform.system() != "Windows":
            return
        try:
            hwnd = int(self.winId())
            try:
                import win32con  # type: ignore[reportMissingImports]
                import win32gui  # type: ignore[reportMissingImports]

                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                # Ensure WS_EX_TRANSPARENT allows clicks to directly pass through
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
                # Let PyQt5 handle the alpha channel via DWM
                win32gui.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE |
                    win32con.SWP_NOSIZE |
                    win32con.SWP_NOZORDER |
                    win32con.SWP_FRAMECHANGED
                )
                app_logger.info("✅ Win32 layered style enabled")
            except Exception as pywin_err:
                app_logger.warning(f"Win32 layered style skipped: {pywin_err}")

            class MARGINS(ctypes.Structure):
                _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int),
                             ("top",  ctypes.c_int), ("bottom", ctypes.c_int)]
            margins = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
            app_logger.info("✅ Win32 DWM transparency OK")
        except Exception as e:
            app_logger.warning(f"Win32 transparency skipped: {e}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SYSTEM TRAY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _create_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        for base in [ASSETS_DIR, SCRIPT_DIR]:
            icon_path = os.path.join(base, "sia_idle.png")
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                break
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))

        tray_menu = QMenu()
        tray_menu.addAction(QAction("👁️ Show Sia",  self, triggered=self.show))
        tray_menu.addAction(QAction("👻 Hide Sia",  self, triggered=self.hide))
        tray_menu.addSeparator()
        motion_menu = tray_menu.addMenu("🎬 Motion Style")
        motion_menu.addAction(QAction("🧘 Calm", self, triggered=lambda: self._set_motion_mode("calm")))
        motion_menu.addAction(QAction("🔥 Expressive", self, triggered=lambda: self._set_motion_mode("expressive")))
        motion_menu.addAction(QAction("⚙️ Auto Switch", self, triggered=lambda: self._set_motion_mode("auto-switch")))
        tray_menu.addAction(QAction("🎚 Realism Slider", self, triggered=self._open_realism_slider))
        tray_menu.addAction(QAction("♻ Reset Motion", self, triggered=self._reset_motion_settings))
        tray_menu.addAction(QAction("🧼 Reset All UI", self, triggered=self._reset_all_ui_settings))
        tray_menu.addSeparator()
        tray_menu.addSeparator()
        tray_menu.addAction(QAction("❌ Exit",       self, triggered=self._quit_app))

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Sia — Your AI Assistant ❤️")
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        if not os.path.exists(self._tray_hint_path):
            self.tray_icon.showMessage(
                "Sia Controls",
                "Right-click tray icon for Motion Style and Realism Slider.",
                QSystemTrayIcon.Information,
                5000
            )
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(self._tray_hint_path, "w", encoding="utf-8") as f:
                    f.write("seen")
            except Exception as e:
                app_logger.warning(f"Could not persist tray hint marker: {e}")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PAINTING — pure transparent overlay
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def paintEvent(self, event):
        """
        Draw ONLY the avatar + speech bubble on a transparent canvas.
        NO background fill → wallpaper fully visible.
        Center-Bottom Overlay Mode, Alpha-Blending support.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        center_x = w // 2

        # ── Alpha Blending using AnimationEngine ──
        bf = self.anim_engine.blend  # BlendFrame: frame_from, frame_to, alpha
        lip_map = {"idle": 0, "semi": 1, "open": 2}

        def get_pixmap(key):
            if key == "blink" and self.blink_pixmap:
                return self.blink_pixmap
            elif key in lip_map and self.lip_pixmaps:
                return self.lip_pixmaps[lip_map[key]]
            return self.character_pixmap

        pix_from = get_pixmap(bf.frame_from)
        pix_to = get_pixmap(bf.frame_to)

        # Box rect is used mostly for waveform and speech bubble relative placement now
        # We will keep a virtual box_rect for those elements near the avatar.
        base_w, base_h = 450, 600
        pulse = getattr(self.anim_engine, 'pulse_scale', 1.0)
        motion_scale = pulse * self.live_scale
        char_w = int(base_w * motion_scale)
        char_h = int(base_h * motion_scale)
        
        # Position her at the exact center of the screen
        char_x = int(center_x - char_w // 2 + self.breathing_offset_x)
        char_y = int((h - char_h) // 2 + self.breathing_offset_y)
        
        box_rect = QRectF(
            center_x - CANVAS_BOX_W / 2,
            char_y - 20, 
            CANVAS_BOX_W,
            char_h + 40
        )
        self.character_rect = QRect(char_x, char_y, char_w, char_h)

        if pix_from and not pix_from.isNull():
            scaled_from = pix_from.scaled(char_w, char_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            scaled_to = pix_to.scaled(char_w, char_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) if pix_to else scaled_from

            # Soft ground shadow
            sg = QRadialGradient(center_x + self.breathing_offset_x * 0.4, char_y + char_h - 12, char_w * 0.38 * self.live_shadow_scale)
            sg.setColorAt(0.0, QColor(0, 0, 0, 45))
            sg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(sg))
            p.setPen(Qt.NoPen)
            p.drawEllipse(
                QPointF(center_x + self.breathing_offset_x * 0.4, char_y + char_h - 6),
                char_w * 0.32 * self.live_shadow_scale, 14 * self.live_shadow_scale
            )

            # Shared transform pivot for subtle head/body tilt.
            pivot = QPointF(char_x + char_w / 2, char_y + char_h * 0.58)

            # Speaking depth pass: faint rear layer to fake torso parallax.
            if self.current_state == "speaking" and self.parallax_strength > 0.05:
                rear_w = int(char_w * 1.01)
                rear_h = int(char_h * 1.01)
                rear_x = int(char_x - (rear_w - char_w) / 2 - self.parallax_strength)
                rear_y = int(char_y - (rear_h - char_h) / 2 + 1.2)
                rear_map = pix_from.scaled(rear_w, rear_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                p.save()
                p.translate(pivot)
                p.rotate(self.head_tilt_deg * 0.35)
                p.translate(-pivot)
                p.setOpacity(0.12)
                p.drawPixmap(rear_x, rear_y, rear_map)
                p.restore()

            # Draw Base Frame (frame_from)
            opacity_from = (255 - bf.alpha) / 255.0
            if opacity_from > 0:
                p.save()
                p.translate(pivot)
                p.rotate(self.head_tilt_deg)
                p.translate(-pivot)
                p.setOpacity(opacity_from)
                p.drawPixmap(char_x, char_y, scaled_from)
                p.restore()

            # Draw Target Frame (frame_to)
            opacity_to = bf.alpha / 255.0
            if opacity_to > 0:
                p.save()
                p.translate(pivot)
                p.rotate(self.head_tilt_deg)
                p.translate(-pivot)
                p.setOpacity(opacity_to)
                p.drawPixmap(char_x, char_y, scaled_to)
                p.restore()

            p.setOpacity(1.0)

        # ── Speech Bubble ──
        if self.bubble_display_text:
            self._draw_speech_bubble(p, w, h, box_rect)

        # ── Waveform ──
        if self.current_state in ("speaking", "listening"):
            self._draw_waveform(p, w, h, box_rect)

        p.end()

    def _draw_memory_box(self, p, box_rect):
        """Central transparent canvas that visually anchors the avatar state."""
        glow_rect = QRectF(box_rect.adjusted(-14, -14, 14, 14))
        glow = QRadialGradient(box_rect.center(), box_rect.width() * 0.62)
        glow.setColorAt(0.0, QColor(0, 255, 204, 28))
        glow.setColorAt(0.5, QColor(50, 140, 255, 16))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawRoundedRect(glow_rect, 34, 34)

        bg_grad = QLinearGradient(box_rect.topLeft(), box_rect.bottomRight())
        bg_grad.setColorAt(0.0, QColor(8, 8, 20, 78))
        bg_grad.setColorAt(1.0, QColor(5, 5, 14, 42))

        path = QPainterPath()
        path.addRoundedRect(box_rect, 30, 30)
        p.setBrush(QBrush(bg_grad))
        p.setPen(QPen(QColor(255, 255, 255, 36), 1.2))
        p.drawPath(path)

        inner = QRectF(box_rect.adjusted(6, 6, -6, -6))
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner, 26, 26)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 255, 204, 30), 1.0))
        p.drawPath(inner_path)

    def _draw_speech_bubble(self, p, w, h, box_rect):
        """Neon glassmorphism speech bubble above avatar head."""
        font = QFont("Segoe UI", 12)
        font.setWeight(QFont.Normal)
        p.setFont(font)
        fm   = QFontMetrics(font)
        text = self.bubble_display_text
        pad  = 16
        max_w = max(180, min(520, int(box_rect.width() - 56)))

        # Word-wrap
        words = text.split()
        lines, current = [], ""
        for word in words:
            test = f"{current} {word}".strip() if current else word
            if fm.horizontalAdvance(test) > max_w - pad * 2:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        if not lines:
            return

        lh       = fm.height() + 3
        text_h   = lh * len(lines)
        text_w   = max(fm.horizontalAdvance(l) for l in lines)
        bub_w    = min(text_w + pad * 2, max_w)
        bub_h    = text_h + pad * 2

        bub_x = max(8, int(box_rect.center().x() - bub_w / 2))
        bub_y = max(8, int(box_rect.top() + 24))

        if hasattr(self, 'character_rect') and not self.character_rect.isEmpty():
            # Place to her left
            bub_x = max(8, int(self.character_rect.left() - bub_w - 20))
            # If no space on left, move to right
            if bub_x <= 8:
                bub_x = min(w - bub_w - 8, int(self.character_rect.right() + 20))
            
            # Align Y roughly with the top portion of her head
            bub_y = int(self.character_rect.top() + self.character_rect.height() * 0.1)

        is_speaking = self.current_state == "speaking"
        pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.tick * 4)) if is_speaking else 0.4

        bubble_rect = QRectF(bub_x, bub_y, bub_w, bub_h)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 14, 14)

        # Outer glow
        gp = QPainterPath()
        gp.addRoundedRect(QRectF(bub_x - 8, bub_y - 8, bub_w + 16, bub_h + 16), 20, 20)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 255, 255, int(30 * pulse)))  # Cyan glow
        p.drawPath(gp)

        # Glass fill: Semi-transparent dark blue
        p.setBrush(QColor(10, 20, 45, int(210 * (0.8 + 0.2 * pulse))))
        # Cyan glow border
        p.setPen(QPen(QColor(0, 255, 255, int(140 * pulse)), 1.5))
        p.drawPath(path)

        # Top shimmer
        shimmer = QLinearGradient(bub_x, bub_y, bub_x, bub_y + bub_h * 0.5)
        shimmer.setColorAt(0.0, QColor(255, 255, 255, 22))
        shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shimmer))
        p.setPen(Qt.NoPen)
        p.drawPath(path)

        # Pink accent
        p.setPen(QPen(QColor(255, 60, 170, int(38 * pulse)), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

        # Text
        p.setFont(font)
        for i, line in enumerate(lines):
            lx = bub_x + pad
            ly = bub_y + pad + i * lh + fm.ascent()
            p.setPen(QColor(0, 150, 255, 40))
            p.drawText(lx + 1, ly + 1, line)
            p.setPen(QColor(245, 245, 255, 240))
            p.drawText(lx, ly, line)

    def _draw_waveform(self, p, w, h, box_rect):
        """Animated waveform at bottom of avatar widget."""
        cx     = w // 2
        base_y = int(box_rect.bottom() - 68)
        p.setRenderHint(QPainter.Antialiasing)

        if self.current_state == "speaking":
            amp   = 18 + 10 * math.sin(self.tick * 5)
            col1  = QColor(0, 255, 204, 200)
            col2  = QColor(255, 60, 170, 130)
            speed = 8
        else:
            amp   = 10 + 6 * math.sin(self.tick * 3)
            col1  = QColor(255, 107, 107, 170)
            col2  = QColor(255, 180, 80, 110)
            speed = 5

        npts  = 60
        width = 280
        sx    = cx - width // 2

        pts1, pts2 = [], []
        for i in range(npts):
            x   = sx + (i / npts) * width
            env = math.exp(-((x - cx) ** 2) / (2 * 48 ** 2))
            pts1.append(QPointF(x, base_y + env * amp * math.sin(i * 0.5 + self.tick * speed)))
            pts2.append(QPointF(x, base_y + env * (amp * 0.5) * math.sin(i * 0.7 - self.tick * speed * 0.7)))

        path1 = QPainterPath()
        path1.moveTo(pts1[0])
        for pt in pts1[1:]: path1.lineTo(pt)

        path2 = QPainterPath()
        path2.moveTo(pts2[0])
        for pt in pts2[1:]: path2.lineTo(pt)

        p.setPen(QPen(col1, 2.2)); p.setBrush(Qt.NoBrush); p.drawPath(path1)
        p.setPen(QPen(col2, 1.4)); p.drawPath(path2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ANIMATION TICK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _breathing_loop(self):
        """Smooth, continuous breathing motion for avatar window/pose."""
        now = time.time()
        dt = max(0.0, now - self._breathing_last_ts)
        self._breathing_last_ts = now
        self.time_counter += dt

        profile = self._get_motion_profile()
        realism_mul = self._get_realism_multiplier()
        amp = profile["amp"] * realism_mul
        x_sway = profile["x_sway"] * realism_mul
        scale_strength = profile["scale"] * realism_mul
        talk_boost = profile["talk_boost"] * realism_mul
        tilt_strength = profile["tilt"] * realism_mul
        jitter_strength = profile["jitter"] * realism_mul
        parallax_strength = profile["parallax"] * realism_mul

        # Core sine wave: new_y = base_y + amplitude * sin(time_counter * frequency)
        new_y = self.base_y + (amp * math.sin(self.time_counter * self.frequency))

        # Add layered micro-motions so Sia feels like a live character, not a sticker.
        sway_phase = self.time_counter * 1.05
        micro_phase = self.time_counter * 2.1
        self.breathing_offset_x = x_sway * math.sin(sway_phase + 0.8)
        self.live_scale = 1.0 + scale_strength * math.sin(self.time_counter * 1.1) + (scale_strength * 0.4) * math.sin(micro_phase)
        self.live_shadow_scale = 0.96 + 0.08 * (0.5 + 0.5 * math.sin(self.time_counter * 1.15 + 0.4))
        self.head_tilt_deg = (0.7 * tilt_strength) * math.sin(self.time_counter * 0.9) + (0.3 * tilt_strength) * math.sin(self.time_counter * 2.0 + 0.6)
        self.parallax_strength = 0.0

        # Occasional micro-jitter gives an alive eye/head micro-adjustment illusion.
        if now >= self._next_jitter_at:
            self.micro_jitter_x = random.uniform(-0.7, 0.7) * jitter_strength
            self.micro_jitter_y = random.uniform(-0.5, 0.5) * jitter_strength
            self._jitter_decay = 1.0
            if self.current_state == "speaking":
                self._next_jitter_at = now + random.uniform(0.8, 1.6)
            else:
                self._next_jitter_at = now + random.uniform(1.6, 3.2)

        self._jitter_decay *= 0.84
        self.breathing_offset_x += self.micro_jitter_x * self._jitter_decay

        # Slightly accent motion while speaking to mimic natural conversational body movement.
        if self.current_state == "speaking":
            self.breathing_offset_x += talk_boost * math.sin(self.time_counter * 3.2)
            self.live_scale += (scale_strength * 0.3) * math.sin(self.time_counter * 4.6)
            self.head_tilt_deg += (0.45 * tilt_strength) * math.sin(self.time_counter * 3.8)
            self.parallax_strength = parallax_strength + (0.9 * parallax_strength) * (0.5 + 0.5 * math.sin(self.time_counter * 3.4 + 0.3))

        # Keep full-screen transparent overlay anchored; move avatar pose instead.
        self.breathing_offset_y = new_y - self.base_y + (self.micro_jitter_y * self._jitter_decay)

        # If this window is ever used in non-fullscreen mode, apply true geometry breathing.
        screen = QApplication.primaryScreen().availableGeometry()
        if self.width() < screen.width() or self.height() < screen.height():
            g = self.geometry()
            self.setGeometry(g.x(), int(new_y), g.width(), g.height())

        self._position_status_label()

    def _animation_tick(self):
        # ── Sync string state → AnimationEngine enum ──
        _state_map = {
            "idle":      AvatarState.IDLE,
            "listening": AvatarState.LISTENING,
            "thinking":  AvatarState.THINKING,
            "speaking":  AvatarState.SPEAKING,
        }
        self.anim_engine.set_state(_state_map.get(self.current_state, AvatarState.IDLE))

        # ── Advance AnimationEngine one frame ──
        self.anim_engine.tick()

        # ── Sync compat aliases back into self for paintEvent ──
        self.tick          = self.anim_engine._tick
        self.breath_offset = self.anim_engine.breath_offset
        self.lip_frame_index = self.anim_engine.lip_index

        # ── Opacity smooth fade ──
        if abs(self.current_opacity - self.target_opacity) > 0.01:
            self.current_opacity += (self.target_opacity - self.current_opacity) * 0.1
            self.opacity_effect.setOpacity(self.current_opacity)

        # ── Status label pulse ──
        self._update_status_style()

        self.update()

    def _update_status_style(self):
        if not self.status_label:
            return
        if self.current_state == "listening":
            pulse = int(170 + 85 * math.sin(self.tick * 4))
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(255, 107, 107, {pulse});
                    color: white;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 10px;
                    border: 1px solid rgba(255,107,107,0.5);
                }}
            """)
        elif self.current_state == "speaking":
            pulse = int(140 + 70 * math.sin(self.tick * 3))
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(118, 75, 162, {pulse});
                    color: white;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 10px;
                    border: 1px solid rgba(118,75,162,0.5);
                }}
            """)
        elif self.current_state == "thinking":
            pulse = int(130 + 60 * math.sin(self.tick * 6))
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background: rgba(50, 140, 255, {pulse});
                    color: white;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 11px;
                    padding: 4px 10px;
                    border-radius: 10px;
                    border: 1px solid rgba(50,140,255,0.5);
                }}
            """)

    def _typewriter_tick(self):
        text = str(self.bubble_text)
        if self.typewriter_index < len(text):
            self.typewriter_index    += 1
            self.bubble_display_text  = text[:self.typewriter_index]
            self.update()
        else:
            self.typewriter_timer.stop()

    def _check_idle_fade(self):
        if self.current_state == "idle" and time.time() - self.last_active_time > 20:
            self.target_opacity = 0.40
        else:
            self.target_opacity = 1.0
            if self.current_state != "idle":
                self.last_active_time = time.time()

    def _canvas_box_rect(self) -> QRectF:
        char_h = 600
        return QRectF(
            self.width() / 2 - CANVAS_BOX_W / 2,
            self.height() - char_h - 20 + self.breathing_offset_y,
            CANVAS_BOX_W,
            char_h + 40
        )

    def _position_status_label(self):
        if not self.status_label:
            return
        box_rect = self._canvas_box_rect()
        self.status_label.adjustSize()

        status_y = int(box_rect.bottom() + (14 if self._compact_overlay_ui else 18))
        max_bottom = self.height() - 6
        if status_y + self.status_label.height() > max_bottom:
            status_y = int(box_rect.top() - self.status_label.height() - 10)

        self.status_label.move(
            int(box_rect.center().x() - self.status_label.width() / 2),
            status_y
        )

        if hasattr(self, "vision_mode_label") and self.vision_mode_label:
            self.vision_mode_label.adjustSize()
            gap = 4 if self._compact_overlay_ui else 8
            vision_y = self.status_label.y() + self.status_label.height() + gap
            if vision_y + self.vision_mode_label.height() > max_bottom:
                vision_y = self.status_label.y() - self.vision_mode_label.height() - gap
            self.vision_mode_label.move(
                int(box_rect.center().x() - self.vision_mode_label.width() / 2),
                vision_y
            )

        if hasattr(self, "motion_mode_label") and self.motion_mode_label:
            self.motion_mode_label.adjustSize()
            gap = 4 if self._compact_overlay_ui else 6
            anchor_y = self.vision_mode_label.y() + self.vision_mode_label.height() + gap if hasattr(self, "vision_mode_label") and self.vision_mode_label else self.status_label.y() + self.status_label.height() + gap
            if anchor_y + self.motion_mode_label.height() > max_bottom:
                anchor_y = self.status_label.y() - self.motion_mode_label.height() - gap
            self.motion_mode_label.move(
                int(box_rect.center().x() - self.motion_mode_label.width() / 2),
                anchor_y
            )

    def _refresh_overlay_layout_mode(self):
        compact = self.width() < 1280 or self.height() < 820
        if compact == self._compact_overlay_ui:
            return

        self._compact_overlay_ui = compact
        if compact:
            self.status_label.setStyleSheet("""
                QLabel {
                    background: rgba(0, 0, 0, 170);
                    color: #00FFCC;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 10px;
                    padding: 3px 8px;
                    border-radius: 9px;
                    border: 1px solid rgba(0,255,204,0.28);
                }
            """)
        else:
            self._reset_status_style()

        self._set_vision_badge({"mode": self._last_vision_mode})
        self._update_motion_badge()

    def _set_vision_badge(self, vision: dict):
        mode = vision.get("mode", "cloud")
        retry_seconds = int(vision.get("retry_seconds", 0) or 0)

        if mode == "cloud":
            text = "📷 Vision: Cloud"
            color = "#00FFCC"
            bg = "rgba(0, 40, 30, 165)"
        else:
            mins = max(1, retry_seconds // 60) if retry_seconds else 1
            text = f"📷 Vision: Offline ({mins}m)"
            color = "#FFD700"
            bg = "rgba(45, 30, 0, 170)"

        self.vision_mode_label.setText(text)
        font_size = 9 if self._compact_overlay_ui else 10
        pad = "2px 7px" if self._compact_overlay_ui else "3px 8px"
        self.vision_mode_label.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {color};
                font-family: 'Segoe UI', sans-serif;
                font-size: {font_size}px;
                padding: {pad};
                border-radius: 9px;
                border: 1px solid {color}55;
            }}
        """)
        self.vision_mode_label.adjustSize()
        self._position_status_label()

    def _update_motion_badge(self):
        mode_short = {
            "calm": "Calm",
            "expressive": "Expressive",
            "auto-switch": "Auto",
        }.get(self.motion_mode, "Auto")
        self.motion_mode_label.setText(f"🎬 Motion: {mode_short} | {int(self.realism_level)}%")

        font_size = 9 if self._compact_overlay_ui else 10
        pad = "2px 7px" if self._compact_overlay_ui else "3px 8px"
        self.motion_mode_label.setStyleSheet(f"""
            QLabel {{
                background: rgba(18, 24, 42, 165);
                color: #9AFBFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: {font_size}px;
                padding: {pad};
                border-radius: 9px;
                border: 1px solid rgba(154,251,255,0.32);
            }}
        """)
        self.motion_mode_label.adjustSize()
        self._position_status_label()

    def _on_api_status_updated(self, status: dict):
        vision = status.get("vision", {})
        self._set_vision_badge(vision)

        mode = vision.get("mode", "cloud")
        if mode == self._last_vision_mode:
            return

        now = time.time()
        if now - self._last_vision_notice_ts < 12:
            self._last_vision_mode = mode
            return

        if mode == "fallback":
            self._show_bubble(
                "Sia ❤️: Vision cloud abhi limit/cooldown pe hai, main offline mode mein screen context de rahi hoon."
            )
            if self.current_state == "idle":
                self._set_status("📷 Vision Offline Mode")
        elif self._last_vision_mode == "fallback" and mode == "cloud":
            self._show_bubble(
                "Sia 💚: Vision cloud wapas online ho gaya! Ab full screen analysis auto-resume ho chuka hai."
            )
            if self.current_state == "idle":
                self._set_status("💤 Say 'Sia'...")
                self._reset_status_style()

        self._last_vision_notice_ts = now
        self._last_vision_mode = mode

    def _show_bubble(self, text):
        self.bubble_text          = text
        self.bubble_display_text  = ""
        self.typewriter_index     = 0
        self.typewriter_timer.start(28)

    def _get_motion_profile(self):
        if self.motion_mode == "auto-switch":
            if self.current_state == "speaking":
                return self.motion_profiles["expressive"]
            if self.current_state in ("idle", "listening"):
                return self.motion_profiles["calm"]
        return self.motion_profiles.get(self.motion_mode, self.motion_profiles["auto-switch"])

    def _load_motion_settings(self):
        try:
            if not os.path.exists(self._motion_settings_path):
                return
            with open(self._motion_settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            mode = data.get("motion_mode", "auto-switch")
            if mode in self.motion_profiles:
                self.motion_mode = mode

            level = int(data.get("realism_level", 78))
            self.realism_level = max(0, min(100, level))
        except Exception as e:
            app_logger.warning(f"Could not load motion settings: {e}")

    def _save_motion_settings(self):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            data = {
                "motion_mode": self.motion_mode,
                "realism_level": int(self.realism_level),
            }
            with open(self._motion_settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
        except Exception as e:
            app_logger.warning(f"Could not save motion settings: {e}")

    def _get_realism_multiplier(self) -> float:
        # Maintain a baseline so motion never becomes completely dead at 0%.
        return 0.35 + (self.realism_level / 100.0) * 0.95

    def _open_realism_slider(self):
        if self.realism_slider_window and self.realism_slider_window.isVisible():
            self.realism_slider_window.close()
            return

        panel = QWidget(None, Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        panel.setAttribute(Qt.WA_TranslucentBackground, True)
        panel.setStyleSheet("""
            QWidget {
                background: rgba(8, 12, 24, 225);
                border: 1px solid rgba(0,255,204,0.35);
                border-radius: 12px;
            }
            QLabel {
                color: #E8FFFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QSlider::groove:horizontal {
                height: 7px;
                background: rgba(255,255,255,0.14);
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(0,255,204,0.80);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
                background: #00FFCC;
                border: 1px solid rgba(255,255,255,0.55);
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("Realism Intensity")
        title.setStyleSheet("font-size: 11px; font-weight: 600;")

        self.realism_value_label = QLabel(f"{self.realism_level}%")
        self.realism_value_label.setAlignment(Qt.AlignCenter)
        self.realism_value_label.setStyleSheet("font-size: 12px; color: #00FFCC; font-weight: 700;")

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(self.realism_level)
        slider.valueChanged.connect(self._on_realism_changed)

        tips = QLabel("0 = soft motion, 100 = cinematic")
        tips.setStyleSheet("font-size: 9px; color: rgba(230,245,255,0.74);")
        tips.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(self.realism_value_label)
        layout.addWidget(slider)
        layout.addWidget(tips)

        panel.resize(230, 108)
        cursor_pos = QCursor.pos()
        panel.move(cursor_pos.x() - 110, cursor_pos.y() - 125)
        panel.destroyed.connect(lambda *_: self._on_realism_panel_closed())
        panel.show()

        self.realism_slider_window = panel
        self._realism_autohide_timer.start(6000)

    def _on_realism_changed(self, value: int):
        self.realism_level = int(value)
        if self.realism_value_label:
            self.realism_value_label.setText(f"{self.realism_level}%")
        self._update_motion_badge()
        if self.current_state in ("idle", "listening"):
            self._set_status(f"🎚 Realism: {self.realism_level}%")
        self._save_motion_settings()
        self._realism_autohide_timer.start(6000)

    def _on_realism_panel_closed(self):
        self.realism_slider_window = None
        self.realism_value_label = None

    def _auto_close_realism_slider(self):
        if self.realism_slider_window and self.realism_slider_window.isVisible():
            self.realism_slider_window.close()

    def _set_motion_mode(self, mode: str):
        if mode not in self.motion_profiles:
            return
        self.motion_mode = mode
        self._update_motion_badge()
        self._save_motion_settings()
        mode_text = {
            "calm": "🧘 Motion: Calm",
            "expressive": "🔥 Motion: Expressive",
            "auto-switch": "⚙️ Motion: Auto",
        }.get(mode, "⚙️ Motion: Auto")
        if self.current_state in ("idle", "listening"):
            self._set_status(mode_text)
        self._show_bubble(f"Sia 🎬: Motion profile switched to {mode} mode.")

    def _reset_motion_settings(self):
        self.motion_mode = "auto-switch"
        self.realism_level = 78
        if self.realism_value_label:
            self.realism_value_label.setText(f"{self.realism_level}%")
        self._update_motion_badge()
        self._save_motion_settings()
        if self.current_state in ("idle", "listening"):
            self._set_status("♻ Motion reset to default")
        self._show_bubble("Sia 🎬: Motion settings reset to default (Auto + 78%).")

    def _reset_all_ui_settings(self):
        self._reset_motion_settings()
        self._compact_overlay_ui = False
        self._refresh_overlay_layout_mode()
        self._reset_status_style()

        if self.realism_slider_window and self.realism_slider_window.isVisible():
            self.realism_slider_window.close()

        try:
            if os.path.exists(self._tray_hint_path):
                os.remove(self._tray_hint_path)
        except Exception as e:
            app_logger.warning(f"Could not reset tray hint marker: {e}")

        if self.current_state in ("idle", "listening"):
            self._set_status("🧼 UI reset complete")
        self._show_bubble("Sia ⚙️: All UI settings reset. Next launch pe tray help hint phir dikhega.")

    def _show_startup_self_check_toast(self):
        checks = []
        checks.append("Avatar OK" if self.character_pixmap and not self.character_pixmap.isNull() else "Avatar Missing")
        checks.append("Blink OK" if self.blink_pixmap and not self.blink_pixmap.isNull() else "Blink Fallback")
        checks.append("Lip-sync OK" if len(self.lip_pixmaps) >= 3 else "Lip-sync Partial")
        checks.append("Wake Thread OK" if self.wake_thread and self.wake_thread.isRunning() else "Wake Thread Pending")

        summary = " | ".join(checks)
        try:
            self.tray_icon.showMessage(
                "Sia Startup Self-Check",
                summary,
                QSystemTrayIcon.Information,
                4500
            )
        except Exception:
            pass

        app_logger.info(f"Startup self-check: {summary}")

    def _show_panel(self):
        """Side panel was removed; keep handler to avoid runtime attribute errors."""
        if self.current_state in ("idle", "listening"):
            self._set_status("⚙️ Use tray for controls")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STATUS LABEL HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _set_status(self, text):
        if self.status_label:
            self.status_label.setText(text)
            self.status_label.adjustSize()
            self._position_status_label()

    def _reset_status_style(self):
        self.status_label.setStyleSheet("""
            QLabel {
                background: rgba(0,0,0,170);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 10px;
                border: 1px solid rgba(0,255,204,0.3);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_panel()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self.base_y = self.y()
        self._breathing_last_ts = time.time()

    def mouseDoubleClickEvent(self, event):
        self._show_panel()

    def enterEvent(self, event):
        """On hover."""
        self.target_opacity = 1.0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PANEL POSITIONING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_seamless_text(self, text):
        self.last_active_time = time.time()
        self._set_status("👂 Heard...")
        self._show_bubble(f"Sia ❤️: Sun rahi hu... ({text[:10]}...)")
        self._on_text_recognized(text)

    def _on_text_recognized(self, text):
        self.current_state = "thinking"
        self._set_status("🧠 Thinking...")
        self._show_bubble(f"Amar: {text}")
        app_logger.info(f"🎤 Heard: {text}")
        memory.add_memory_log(f"Voice: {text}")

        # ── Setup Streaming Pipeline ──
        self.streaming_buffer = ""
        
        if hasattr(self, 'audio_stream_thread') and self.audio_stream_thread.isRunning():
            self.audio_stream_thread.stop()
            self.audio_stream_thread.wait()

        self.audio_stream_thread = AudioStreamThread()
        self.audio_stream_thread.start()

        if self.think_thread and self.think_thread.isRunning():
            self.think_thread.terminate()
            self.think_thread.wait(1000)
        self.think_thread = ThinkThread(text)
        self.think_thread.chunk_ready.connect(self._on_chunk_ready)
        self.think_thread.response_ready.connect(self._on_response_ready)
        self.think_thread.start()

    def _on_chunk_ready(self, chunk):
        # Stop typewriter, render instantly (Zero Latency UI)
        self.typewriter_timer.stop()
        if self.current_state == "thinking" or not getattr(self, 'bubble_display_text', '').startswith("Sia"):
             self.bubble_text = "Sia 🧡: "
             self.bubble_display_text = "Sia 🧡: "
             self.current_state = "speaking"
             self._set_status("🧡 Speaking")
        
        # Clean control tags
        clean_chunk = re.sub(r'\[.*?\]', '', chunk)
        if not clean_chunk:
            return
            
        self.bubble_text += clean_chunk
        self.bubble_display_text += clean_chunk
        self.update()

        # Buffer for sentence-by-sentence TTS
        self.streaming_buffer += clean_chunk
        if any(p in self.streaming_buffer for p in ['. ', '? ', '! ', ', ', '\n']) or len(self.streaming_buffer) > 40:
            if self.streaming_buffer.strip():
                self.audio_stream_thread.enqueue(self.streaming_buffer.strip())
            self.streaming_buffer = ""

    def _on_response_ready(self, response):
        # Flush remaining chunks
        if getattr(self, 'streaming_buffer', "").strip():
            self.audio_stream_thread.enqueue(self.streaming_buffer.strip())
            self.streaming_buffer = ""
        if hasattr(self, 'audio_stream_thread'):
            self.audio_stream_thread.enqueue("<STOP>")

        if response.strip() == "[IGNORE]":
            self.current_state = "idle"
            self._set_status("👂 Listening...")
            self._reset_status_style()
            if self.wake_thread and self.wake_thread.isRunning():
                self.wake_thread.resume()
            return

        # ── MOOD_CHANGE Signal ──
        if response.startswith("MOOD_CHANGE:"):
            parts = response.split(":", 2)
            if len(parts) == 3:
                mood, text = parts[1], parts[2]
                self.current_state = "speaking"
                mood_labels = {"RELAX": "🧡 Relax", "ENERGIZE": "🔥 Energy", "FOCUS": "🎯 Focus"}
                self._set_status(mood_labels.get(mood, "✨ Mood Active"))
                self._show_bubble(f"Sia 🧡: {text}")
                if self.speak_thread and self.speak_thread.isRunning():
            self.speak_thread.terminate()
            self.speak_thread.wait(1000)
        self.speak_thread = SpeakThread(text, emotion="SMILE")
                self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
                self.speak_thread.start()
                return

        # ── SHOW_WIDGET:WEATHER Signal ──
        if response.startswith("SHOW_WIDGET:WEATHER:"):
            city = response.split(":", 2)[2].strip()
            self._show_weather_widget(city)
            text = f"Hero, {city} ka weather dekho! 🌤️"
            self.current_state = "speaking"
            self._set_status("🌤️ Weather Widget")
            self._show_bubble(f"Sia ❤️: {text}")
            if self.speak_thread and self.speak_thread.isRunning():
            self.speak_thread.terminate()
            self.speak_thread.wait(1000)
        self.speak_thread = SpeakThread(text, emotion="HAPPY")
            self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
            self.speak_thread.start()
            return

        # Parse emotion tag
        emotion_match = re.search(r'\[(.*?)\]', response)
        emotion = "IDLE"
        if emotion_match:
            emotion   = emotion_match.group(1).upper()
            response  = response.replace(f"[{emotion_match.group(1)}]", "").strip()

        self._load_character(emotion)
        self.current_state = "speaking"
        self._set_status("💬 Speaking...")
        self._show_bubble(f"Sia ❤️: {response}")
        app_logger.info(f"💬 Sia: {response}")
        memory.add_memory_log(f"Sia: {response}")

        if self.speak_thread and self.speak_thread.isRunning():
            self.speak_thread.terminate()
            self.speak_thread.wait(1000)
        self.speak_thread = SpeakThread(response, emotion=emotion)
        self.speak_thread.speaking_started.connect(self._on_speaking_started)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()

    def _show_weather_widget(self, city):
        """Show floating weather widget."""
        try:
            if self.weather_widget_ref and self.weather_widget_ref.isVisible():
                self.weather_widget_ref.close()
            self.weather_widget_ref = WeatherWidget(city=city)
            self.weather_widget_ref.show()
            app_logger.info(f"🌤️ Weather Widget: {city}")
        except Exception as e:
            app_logger.error(f"Weather widget error: {e}")

    def _on_speaking_started(self):
        pass   # lip_frame cycling handled by _animation_tick

    def _on_speaking_finished(self):
        self.last_active_time = time.time()
        self._load_character("IDLE")
        self.current_state    = "idle"
        self._set_status("👂 Listening...")
        self._reset_status_style()
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_user_interrupt(self):
        """Called by VAD monitor when user speaks while Sia is talking — instant silence!"""
        if self.current_state != "speaking":
            return
        app_logger.info("[Interrupt] User spoke — Sia silenced.")
        voice_engine.stop()

        # Stop AudioStreamThread cleanly
        if hasattr(self, 'audio_stream_thread') and self.audio_stream_thread.isRunning():
            self.audio_stream_thread.stop()

        self.current_state = "listening"
        self._set_status("👂 Suno kya bola...")
        self._show_bubble("Sia 👂: Ha bolo, main sun rahi hoon...")
        self.update()

    def _on_status_change(self, status):
        pass   # handled by _on_wake_word

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MANUAL / PANEL ACTIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _run_proactive_vision_loop(self):
        if self.current_state != "idle":
            return
        app_logger.info("Starting 5-minute proactive vision loop...")
        if getattr(self, "proactive_vision_thread", None) and self.proactive_vision_thread.isRunning():
            self.proactive_vision_thread.terminate()
            self.proactive_vision_thread.wait(1000)
        self.proactive_vision_thread = ProactiveVisionThread()
        self.proactive_vision_thread.result_ready.connect(self._proactive_speak)
        self.proactive_vision_thread.start()

    def _proactive_speak(self, message):
        if self.current_state != "idle":
            return
        if self.speak_thread and self.speak_thread.isRunning():
            self.speak_thread.terminate()
            self.speak_thread.wait(1000)
        self.speak_thread = SpeakThread(message, "SMILE")
        self.speak_thread.speaking_started.connect(self._on_speaking_started)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()
        self._show_bubble(f"Sia 🔔: {message}")

    def _show_proactive_toast(self, message):
        try:
            toast = ToastNotification(f"🔔 Sia: {message}")
            toast.show_toast()
            self._active_toasts.append(toast)
            self._active_toasts = [t for t in self._active_toasts if t.isVisible()]
        except Exception as e:
            app_logger.error(f"Toast error: {e}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  WINDOW CONTROLS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _toggle_on_top(self):
        self.is_on_top = not self.is_on_top
        flags = self.windowFlags()
        flags |= Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint
        flags &= ~(Qt.WindowStaysOnTopHint | Qt.WindowStaysOnBottomHint)
        flags |= Qt.WindowStaysOnTopHint if self.is_on_top else Qt.WindowStaysOnBottomHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Space and event.modifiers() == Qt.AltModifier:
            self.setVisible(not self.isVisible())

    def _quit_app(self):
        self._save_motion_settings()
        if self.wake_thread:
            self.wake_thread.stop()
            self.wake_thread.wait(2000)
        if self.proactive_engine:
            self.proactive_engine.stop()
        if self.api_status_thread:
            self.api_status_thread.stop()
            self.api_status_thread.wait(1000)
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        self._quit_app()
        event.accept()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    try:
        def _safe_console_print(text: str):
            try:
                print(text)
            except UnicodeEncodeError:
                fallback = text.encode("ascii", errors="replace").decode("ascii")
                print(fallback)

        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        def handle_exception(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.exit(0)
            app_logger.error("Uncaught: %s", ''.join(
                __import__('traceback').format_exception(exc_type, exc_value, exc_tb)))
        sys.excepthook = handle_exception

        app.setApplicationName("Sia Desktop Assistant")
        app.setOrganizationName("Amar Tech")

        os.chdir(SCRIPT_DIR)

        _safe_console_print("\n" + "═" * 55)
        _safe_console_print("  🎀 SIA v3.0 — Floating Desktop Assistant")
        _safe_console_print("  ✅ Transparent  ✅ Side Panel  ✅ Lip-Sync")
        _safe_console_print("  💖 Say 'Sia' to wake  |  Esc = Hide")
        _safe_console_print("═" * 55 + "\n")

        sia = SiaDesktop()

        smoke_seconds_raw = os.getenv("SIA_SMOKE_SECONDS", "").strip()
        if smoke_seconds_raw:
            try:
                smoke_seconds = max(1.0, float(smoke_seconds_raw))
            except ValueError:
                smoke_seconds = 8.0
            QTimer.singleShot(int(smoke_seconds * 1000), lambda: os._exit(0))
            _safe_console_print(f"[Smoke Mode] Auto-exit in {smoke_seconds:.1f}s")

        exit_code = app.exec_()
        if smoke_seconds_raw:
            sys.exit(0)
        sys.exit(exit_code)

    except Exception as e:
        try:
            _safe_console_print(f"❌ Fatal: {e}")
        except Exception:
            print(f"Fatal: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
