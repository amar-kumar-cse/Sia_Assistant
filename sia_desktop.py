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

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QSystemTrayIcon, QMenu, QAction, QLineEdit,
    QGraphicsOpacityEffect, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, QSize, QPoint, QPointF, QRectF
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QFont, QFontDatabase, QIcon,
    QRadialGradient, QLinearGradient, QPainterPath, QPen, QBrush,
    QFontMetrics, QCursor, QRegion
)

# ── Backend imports ──────────────────────────────────────────
from engine import listen_engine, brain, voice_engine, actions, memory
from engine.automation import SiaProactiveEngine
from engine.toast_ui import ToastNotification
from engine.weather_widget import WeatherWidget
from engine.logger import get_logger

app_logger = get_logger("Sia_Desktop")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")

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
    """Always-listening thread for 'Sia' wake word detection."""
    wake_word_detected = pyqtSignal()
    status_changed     = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused  = False

    def run(self):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold        = 300
        recognizer.pause_threshold         = 0.5
        recognizer.dynamic_energy_threshold = True

        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue

            self.status_changed.emit("idle")
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    while self.running and not self.paused:
                        try:
                            audio = recognizer.listen(source, timeout=2, phrase_time_limit=3)
                            try:
                                text  = recognizer.recognize_google(audio).lower()
                                aliases = ["sia", "siya", "see ya", "shia", "sya", "cia", "shea"]
                                if any(a in text for a in aliases):
                                    app_logger.info(f"⚡ Wake word! (Heard: {text})")
                                    self.status_changed.emit("detected")
                                    self.wake_word_detected.emit()
                                    self.paused = True
                                    break
                            except sr.UnknownValueError:
                                pass
                            except sr.RequestError:
                                pass
                        except sr.WaitTimeoutError:
                            pass
                        except Exception as e:
                            app_logger.error(f"Wake inner error: {e}")
                            time.sleep(1)
            except Exception as e:
                app_logger.error(f"Microphone error: {e}")
                time.sleep(3)

    def resume(self):
        self.paused = False

    def stop(self):
        """Gracefully stop the wake word detection thread."""
        self.running = False
        self.paused = False  # ✅ Resume first so it can exit from listen()
        self.wait(5000)  # ✅ Wait up to 5 seconds for thread to finish
        
        if self.isRunning():
            logger.warning("Wake word thread did not stop gracefully - forcing termination")
            self.terminate()  # Force kill if needed
            self.wait(2000)  # Wait 2 more seconds after terminate


class ListenThread(QThread):
    text_recognized  = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_failed  = pyqtSignal()

    def run(self):
        try:
            self.listening_started.emit()
            
            # ✅ FIX #5: Get raw text
            text = listen_engine.listen()
            
            if not text:  # ✅ FIX #5: Check for None/empty
                self.listening_failed.emit()
                return
            
            # ✅ FIX #5: Sanitize input
            try:
                from engine.validation import sanitize_input
                sanitized_text = sanitize_input(text, max_length=500)
            except (ImportError, ValueError) as e:
                app_logger.error(f"Input validation failed: {e}")
                self.listening_failed.emit()
                return
            
            if not sanitized_text:  # ✅ FIX #5: Empty after sanitization
                app_logger.warning(f"Text '{text[:50]}' was empty after sanitization")
                self.listening_failed.emit()
                return
            
            # ✅ FIX #5: Now emit safe text
            self.text_recognized.emit(sanitized_text)
            
        except PermissionError:
            app_logger.error("Microphone permission denied")
            self.listening_failed.emit()
        except Exception as e:
            app_logger.error(f"Listen thread error: {e}", exc_info=True)
            self.listening_failed.emit()


class ThinkThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, user_text, parent=None):
        super().__init__(parent)
        self.user_text = user_text

    def run(self):
        action_result = actions.perform_action(self.user_text)
        if action_result:
            self.response_ready.emit(action_result)
            return
        response = brain.think(self.user_text)
        self.response_ready.emit(response)


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


class VisionThread(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, question="Meri screen pe kya hai?", mode="screen", parent=None):
        super().__init__(parent)
        self.question = question
        self.mode     = mode

    def run(self):
        try:
            from engine import vision_engine
            if self.mode == "webcam":
                result = vision_engine.analyze_webcam(self.question)
            else:
                result = vision_engine.analyze_screen(self.question)
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit(f"[CONFUSED] Vision error: {str(e)[:50]}")


class WebSearchThread(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        try:
            from engine import web_search
            result = web_search.search_web(self.query, num_results=3)
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit(f"❌ Search error: {str(e)[:50]}")


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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GLASSMORPHISM SIDE PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SidePanel(QWidget):
    """Floating glass-morphism control panel — slides in from the right."""

    mic_clicked    = pyqtSignal()
    vision_clicked = pyqtSignal()
    search_clicked = pyqtSignal()
    pin_clicked    = pyqtSignal()
    close_clicked  = pyqtSignal()
    text_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedSize(PANEL_W, PANEL_H)
        self._pinned = False
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide)
        self._build_ui()

    # ── Build ──────────────────────────────────────────────

    def _build_ui(self):
        self.setContentsMargins(0, 0, 0, 0)

        # Compact card layout: badge + 2x2 action grid + bottom controls.
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        # Container for the controls inside the glass panel.
        vbox = QVBoxLayout()
        vbox.setSpacing(8)
        vbox.setAlignment(Qt.AlignTop)

        # API status badge (small, sleek at top)
        self.api_label = QLabel("⏳ API", self)
        self.api_label.setAlignment(Qt.AlignCenter)
        self.api_label.setStyleSheet("""
            QLabel {
                color: #00FFCC;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10px;
                font-weight: bold;
                padding: 5px 6px;
                border-radius: 6px;
                background: rgba(0,255,204,0.1);
                border: 1px solid rgba(0,255,204,0.3);
            }
        """)
        vbox.addWidget(self.api_label)

        # Small divider
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: rgba(255,255,255,0.15);")
        vbox.addWidget(line)

        # Action buttons arranged as a compact grid instead of a vertical stack.
        self.mic_btn    = self._make_btn("🎤", "#FF6B98", "Voice Input")
        self.vision_btn = self._make_btn("📷", "#FFD700", "Analyze Screen")
        self.search_btn = self._make_btn("🔍", "#00BFFF", "Web Search")
        self.pin_btn    = self._make_btn("📌", "#00FFCC", "Pin Panel")
        self.close_btn  = self._make_btn("✕", "#FF4444", "Close App")

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(self.mic_btn, 0, 0)
        grid.addWidget(self.vision_btn, 0, 1)
        grid.addWidget(self.search_btn, 1, 0)
        grid.addWidget(self.pin_btn, 1, 1)

        vbox.addLayout(grid)
        vbox.addStretch(1)
        vbox.addWidget(self.close_btn)

        main_layout.addLayout(vbox)

        # Wire buttons
        self.mic_btn.clicked.connect(self.mic_clicked.emit)
        self.vision_btn.clicked.connect(self.vision_clicked.emit)
        self.search_btn.clicked.connect(self.search_clicked.emit)
        self.pin_btn.clicked.connect(self._toggle_pin)
        self.close_btn.clicked.connect(self.close_clicked.emit)

        # Note: Text input is removed from the side panel to keep it sleek.
        # User can speak or type in a dedicated chat window or prompt later.

    def _make_btn(self, icon_text, color, tooltip):
        btn = QPushButton(icon_text, self)
        btn.setToolTip(tooltip)
        r, g, b = QColor(color).red(), QColor(color).green(), QColor(color).blue()
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({r},{g},{b}, 25);
                color: {color};
                font-family: 'Segoe UI Emoji', 'Segoe UI', Arial;
                font-size: 15px;
                padding: 8px;
                border-radius: 12px;
                border: 1px solid rgba({r},{g},{b}, 0.3);
            }}
            QPushButton:hover {{
                background: rgba({r},{g},{b}, 65);
                border: 1px solid rgba({r},{g},{b}, 0.7);
            }}
            QPushButton:pressed {{
                background: rgba({r},{g},{b}, 120);
            }}
        """)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    # ── Panel painting (glassmorphism) ────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Ultra-sleek Glass body
        path = QPainterPath()
        path.addRoundedRect(QRectF(2, 2, w - 4, h - 4), 16, 16)
        
        # Soft dark gradient background
        bg_grad = QLinearGradient(0, 0, w, h)
        bg_grad.setColorAt(0, QColor(10, 10, 25, 200))
        bg_grad.setColorAt(1, QColor(5, 5, 15, 230))
        
        p.setBrush(QBrush(bg_grad))
        p.setPen(QPen(QColor(0, 255, 204, 60), 1.0))
        p.drawPath(path)
        
        # Edge highlight
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        path_inner = QPainterPath()
        path_inner.addRoundedRect(QRectF(3, 3, w - 6, h - 6), 15, 15)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path_inner)
        
        p.end()

    # ── Logic ─────────────────────────────────────────────

    def _on_text_enter(self):
        text = self.text_input.text().strip()
        if text:
            self.text_input.clear()
            self.text_submitted.emit(text)

    def _toggle_pin(self):
        self._pinned = not self._pinned
        self.pin_btn.setText("📌  Pinned" if self._pinned else "📌  Pin")
        if self._pinned:
            self._hide_timer.stop()
        else:
            self._hide_timer.start(3000)

    def update_api_status(self, status: dict):
        text  = status.get("status_text", "?")
        color_map = {"green": "#00FFCC", "yellow": "#FFD700", "red": "#FF4444"}
        color = color_map.get(status.get("status_color", "green"), "#00FFCC")
        self.api_label.setText(text)
        self.api_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 8px;
                background: rgba(0,0,0,0.15);
                border: 1px solid {color}44;
            }}
        """)

    def show_panel(self):
        self.show()
        self.raise_()
        if not self._pinned:
            self._hide_timer.start(4000)

    def _auto_hide(self):
        if not self._pinned:
            # Fade out
            self._fade_out()

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(350)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(self.hide)
        anim.finished.connect(lambda: self.setWindowOpacity(1.0))
        anim.start()

    def enterEvent(self, event):
        self._hide_timer.stop()
        self.setWindowOpacity(1.0)

    def leaveEvent(self, event):
        if not self._pinned:
            self._hide_timer.start(2500)


class TaskbarDock(QWidget):
    """Minimal dock for WhatsApp and Work mode, anchored to the taskbar edge."""

    wa_clicked = pyqtSignal()
    work_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedSize(DOCK_W, DOCK_H)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.wa_btn = self._make_btn("WA", "#00C2FF", "Open WhatsApp")
        self.work_btn = self._make_btn("Work", "#00FFCC", "Work Mode")

        layout.addWidget(self.wa_btn)
        layout.addWidget(self.work_btn)

        self.wa_btn.clicked.connect(self.wa_clicked.emit)
        self.work_btn.clicked.connect(self.work_clicked.emit)

    def _make_btn(self, label, color, tooltip):
        btn = QPushButton(label, self)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(8, 8, 22, 190);
                color: {color};
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 700;
                padding: 8px 12px;
                border-radius: 15px;
                border: 1px solid {color}66;
            }}
            QPushButton:hover {{
                background: rgba(16, 16, 36, 235);
                border: 1px solid {color}CC;
            }}
            QPushButton:pressed {{
                background: rgba(0, 0, 0, 220);
            }}
        """)
        return btn

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor(8, 8, 22, 180))
        grad.setColorAt(1, QColor(18, 18, 36, 210))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.drawPath(path)
        p.end()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN AVATAR WINDOW
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
        self.tick          = 0.0
        self.breath_offset = 0.0

        self.character_pixmap  = None
        self.character_rect    = QRect()
        self.lip_pixmaps       = []
        self.lip_frame_index   = 0
        self.lip_tick_counter  = 0
        self.lip_tick_speed    = 3        # advance frame every 3×50ms = 150ms

        self.current_mood      = "DEFAULT"
        self.is_on_top         = True
        self.weather_widget_ref = None

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

        screen = QApplication.primaryScreen().availableGeometry()
        self.canvas_rect = QRect(screen)

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

        # ── Size & position: screen-sized transparent canvas ──
        self.setGeometry(screen)

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

        # ── Side Panel ──
        self.side_panel = SidePanel()
        self.side_panel.mic_clicked.connect(self._manual_voice_input)
        self.side_panel.vision_clicked.connect(self._vision_screen)
        self.side_panel.search_clicked.connect(self._start_search)
        self.side_panel.pin_clicked.connect(self._toggle_on_top)
        self.side_panel.close_clicked.connect(self.close)
        self.side_panel.text_submitted.connect(self._on_text_recognized)
        self._position_side_panel()

        # ── Taskbar Dock ──
        self.taskbar_dock = TaskbarDock(self)
        self.taskbar_dock.wa_clicked.connect(self._open_whatsapp)
        self.taskbar_dock.work_clicked.connect(self._open_work_mode)
        self.taskbar_dock.show()
        self._position_taskbar_dock()

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

        # ── API Status polling ──
        self.api_status_thread = ApiStatusThread()
        self.api_status_thread.status_updated.connect(self.side_panel.update_api_status)
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
        self.wake_thread.wake_word_detected.connect(self._on_wake_word)
        self.wake_thread.status_changed.connect(self._on_status_change)
        self.wake_thread.start()

        # ── Greeting ──
        hour = time.localtime().tm_hour
        if 5  <= hour < 12: g = "Good Morning Hero! ☀️ Aaj ka din amazing hoga! 💪"
        elif 12 <= hour < 17: g = "Good Afternoon Hero! 🌤️ Kuch khaaya? 😊"
        elif 17 <= hour < 21: g = "Good Evening Hero! 🌙 Kaisa raha din? ❤️"
        else:                  g = "Itni raat ko jaag rahe ho? Take care yaar! 💤"
        self._show_bubble(f"Sia ❤️: {g}")

        self.show()
        app_logger.info("✅ Sia Desktop v3.0 is LIVE!")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_status_label()
        self._position_side_panel()
        self._position_taskbar_dock()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ASSETS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_character(self, emotion="IDLE"):
        """Load avatar frame for given emotion. Lip-sync frames always cached."""
        emotion_files = {
            "IDLE":      ["Sia_closed.png", "sia_idle.png"],
            "SMILE":     ["Sia_open.png",   "sia_idle.png"],
            "HAPPY":     ["Sia_open.png",   "sia_idle.png"],
            "SAD":       ["Sia_closed.png", "sia_idle.png"],
            "CONCERNED": ["Sia_closed.png", "sia_idle.png"],
            "CONFUSED":  ["Sia_semi.png",   "sia_idle.png"],
            "SURPRISED": ["Sia_open.png",   "sia_idle.png"],
            "ANGRY":     ["Sia_closed.png", "sia_idle.png"],
        }
        filenames = emotion_files.get(emotion.upper(), ["Sia_closed.png", "sia_idle.png"])

        for fn in filenames:
            for base in [ASSETS_DIR, SCRIPT_DIR]:
                path = os.path.join(base, fn)
                if os.path.exists(path):
                    px = QPixmap(path)
                    if not px.isNull():
                        self.character_pixmap = px
                        break
            else:
                continue
            break

        # Cache lip-sync frames once
        if not self.lip_pixmaps:
            for fn in ["Sia_closed.png", "Sia_semi.png", "Sia_open.png"]:
                path = os.path.join(ASSETS_DIR, fn)
                lp   = QPixmap(path)
                if lp.isNull() and self.character_pixmap:
                    lp = self.character_pixmap
                self.lip_pixmaps.append(lp)
            app_logger.info(f"✅ Lip-sync frames: {len(self.lip_pixmaps)} loaded")

    def _apply_win32_transparency(self):
        """Remove DWM halo border (Windows only)."""
        if platform.system() != "Windows":
            return
        try:
            hwnd = int(self.winId())
            try:
                import win32con
                import win32gui

                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex_style |= win32con.WS_EX_LAYERED
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
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
        tray_menu.addAction(QAction("🎛️ Panel",     self, triggered=self._show_panel))
        tray_menu.addSeparator()
        tray_menu.addAction(QAction("❌ Exit",       self, triggered=self._quit_app))

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Sia — Your AI Assistant ❤️")
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

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
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        center_x = w // 2
        center_y = h // 2
        box_rect = QRectF(
            center_x - CANVAS_BOX_W / 2,
            center_y - CANVAS_BOX_H / 2,
            CANVAS_BOX_W,
            CANVAS_BOX_H
        )

        self._draw_memory_box(p, box_rect)

        # ── Pick correct pixmap (lip-sync or idle) ──
        cycle_map   = [0, 1, 2, 1]
        if self.current_state == "speaking" and self.lip_pixmaps:
            frame_idx  = cycle_map[self.lip_frame_index % len(cycle_map)]
            active_pix = self.lip_pixmaps[frame_idx]
        else:
            active_pix = self.character_pixmap

        # ── Draw avatar ──
        if active_pix and not active_pix.isNull():
            char_h  = min(int(CANVAS_BOX_H * 0.72), 460)
            scaled  = active_pix.scaledToHeight(char_h, Qt.SmoothTransformation)
            char_x  = center_x - scaled.width() // 2
            char_y  = int(box_rect.top() + 92 + self.breath_offset)
            self.character_rect = QRect(char_x, char_y, scaled.width(), scaled.height())

            # Soft ground shadow
            sg = QRadialGradient(center_x, char_y + char_h - 12, scaled.width() * 0.38)
            sg.setColorAt(0.0, QColor(0, 0, 0, 45))
            sg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(sg))
            p.setPen(Qt.NoPen)
            p.drawEllipse(
                QPointF(center_x, char_y + char_h - 6),
                scaled.width() * 0.32, 14
            )

            p.drawPixmap(char_x, char_y, scaled)

        # ── Neon glow ring around avatar (idle pulse) ──
        if self.current_state == "idle":
            pulse_a = int(18 + 10 * math.sin(self.tick * 1.8))
            glow_r  = QRadialGradient(center_x, center_y, CANVAS_BOX_W * 0.42)
            glow_r.setColorAt(0.6, QColor(0, 255, 204, 0))
            glow_r.setColorAt(1.0, QColor(0, 255, 204, pulse_a))
            p.setBrush(QBrush(glow_r))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(center_x, center_y),
                          CANVAS_BOX_W * 0.46, CANVAS_BOX_H * 0.50)

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
        # Place bubble in the upper portion of the centered canvas box
        bub_y = max(8, int(box_rect.top() + 24))

        is_speaking = self.current_state == "speaking"
        pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.tick * 4)) if is_speaking else 0.4

        bubble_rect = QRectF(bub_x, bub_y, bub_w, bub_h)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 14, 14)

        # Outer glow
        gp = QPainterPath()
        gp.addRoundedRect(QRectF(bub_x - 8, bub_y - 8, bub_w + 16, bub_h + 16), 20, 20)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 160, 255, int(16 * pulse)))
        p.drawPath(gp)

        # Glass fill
        p.setBrush(QColor(8, 8, 25, int(195 * (0.8 + 0.2 * pulse))))
        p.setPen(QPen(QColor(0, 200, 255, int(90 * pulse)), 1.2))
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

    def _animation_tick(self):
        self.tick         += 0.1
        self.breath_offset = math.sin(self.tick * 1.5) * 3.0

        # ── Lip-sync ──
        if self.lip_pixmaps:
            if self.current_state == "speaking":
                self.lip_tick_counter += 1
                if self.lip_tick_counter >= self.lip_tick_speed:
                    self.lip_tick_counter = 0
                    self.lip_frame_index  = (self.lip_frame_index + 1) % 4
            else:
                self.lip_frame_index  = 0
                self.lip_tick_counter = 0

        # ── Opacity ──
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
        return QRectF(
            self.width() / 2 - CANVAS_BOX_W / 2,
            self.height() / 2 - CANVAS_BOX_H / 2,
            CANVAS_BOX_W,
            CANVAS_BOX_H
        )

    def _position_status_label(self):
        if not self.status_label:
            return
        box_rect = self._canvas_box_rect()
        self.status_label.adjustSize()
        self.status_label.move(
            int(box_rect.center().x() - self.status_label.width() / 2),
            int(box_rect.bottom() + 18)
        )

    def _position_taskbar_dock(self):
        if not hasattr(self, "taskbar_dock"):
            return
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + screen.width() - DOCK_W - 20
        y = screen.top() + screen.height() - DOCK_H - 18
        self.taskbar_dock.move(x, y)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  BUBBLE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _show_bubble(self, text):
        self.bubble_text          = text
        self.bubble_display_text  = ""
        self.typewriter_index     = 0
        self.typewriter_timer.start(28)

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

    def _open_whatsapp(self):
        try:
            from engine import os_automation
            result = os_automation.open_whatsapp_web()
        except Exception as e:
            result = f"❌ WhatsApp open nahi hua: {e}"
        self._show_bubble(f"Sia ❤️: {result}")
        self._set_status("📱 WhatsApp")

    def _open_work_mode(self):
        try:
            from engine import os_automation
            result = os_automation.open_work_mode()
        except Exception as e:
            result = f"❌ Work mode start nahi hua: {e}"
        self._show_bubble(f"Sia ❤️: {result}")
        self._set_status("💼 Work Mode")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  DRAG SUPPORT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_panel()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            self._position_side_panel()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._show_panel()

    def enterEvent(self, event):
        """On hover → show side panel."""
        self._show_panel()
        self.target_opacity = 1.0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PANEL POSITIONING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _position_side_panel(self):
        """Place panel to the left of the avatar widget."""
        box_rect = self._canvas_box_rect()
        screen = QApplication.primaryScreen().availableGeometry()
        px = int(box_rect.right() + 24)
        py = int(box_rect.center().y() - PANEL_H / 2)
        if px + PANEL_W > screen.right() - 8:
            px = int(box_rect.left() - PANEL_W - 24)
        px = max(screen.left() + 8, min(px, screen.right() - PANEL_W - 8))
        py = max(screen.top() + 8, min(py, screen.bottom() - PANEL_H - 8))
        self.side_panel.move(px, py)

    def _show_panel(self):
        self._position_side_panel()
        self.side_panel.setWindowOpacity(1.0)
        self.side_panel.show_panel()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  VOICE PIPELINE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_wake_word(self):
        self.last_active_time = time.time()
        self.current_state    = "listening"
        self._set_status("👂 Listening...")
        self._show_bubble("Sia ❤️: Haan bolo Hero! 👂")

        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_text_recognized)
        self.listen_thread.listening_failed.connect(self._on_listen_failed)
        self.listen_thread.start()

    def _on_text_recognized(self, text):
        self.current_state = "thinking"
        self._set_status("🧠 Thinking...")
        self._show_bubble(f"Amar: {text}")
        app_logger.info(f"🎤 Heard: {text}")
        memory.add_memory_log(f"Voice: {text}")

        self.think_thread = ThinkThread(text)
        self.think_thread.response_ready.connect(self._on_response_ready)
        self.think_thread.start()

    def _on_response_ready(self, response):
        if response.strip() == "[IGNORE]":
            self.current_state = "idle"
            self._set_status("💤 Say 'Sia'...")
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
        self._set_status("💤 Say 'Sia'...")
        self._reset_status_style()
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_listen_failed(self):
        self.current_state = "idle"
        self._set_status("💤 Say 'Sia'...")
        self._reset_status_style()
        self._show_bubble("Sia ❤️: Kuch sunayi nahi diya... Dobara bolo Hero! 😊")
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_status_change(self, status):
        pass   # handled by _on_wake_word

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MANUAL / PANEL ACTIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _manual_voice_input(self):
        if self.current_state != "idle":
            return
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.paused = True
        self.current_state = "listening"
        self._set_status("👂 Listening...")
        self._show_bubble("Sia ❤️: Bol Hero! 🎤")

        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_text_recognized)
        self.listen_thread.listening_failed.connect(self._on_listen_failed)
        self.listen_thread.start()

    def _vision_screen(self):
        if self.current_state != "idle":
            return
        self.current_state = "thinking"
        self._set_status("📷 Analyzing screen...")
        self._show_bubble("Sia ❤️: Screen dekh rahi hoon... 📷")

        self.vision_thread = VisionThread(
            question="Meri screen pe kya hai? Error hai toh batao.", mode="screen"
        )
        self.vision_thread.result_ready.connect(self._on_vision_result)
        self.vision_thread.start()

    def _on_vision_result(self, result):
        self._on_response_ready(result)

    def _start_search(self):
        if self.current_state != "idle":
            return
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.paused = True
        self.current_state = "listening"
        self._set_status("🔍 Bol: Kya search karoon?")
        self._show_bubble("Sia ❤️: Kya search karna hai? Bolo! 🔍")

        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_search_query)
        self.listen_thread.listening_failed.connect(self._on_listen_failed)
        self.listen_thread.start()

    def _on_search_query(self, text):
        self.current_state = "thinking"
        self._set_status("🔍 Searching...")
        self._show_bubble(f"🔍 Searching: {text}")

        self.search_thread = WebSearchThread(text)
        self.search_thread.result_ready.connect(self._on_search_result)
        self.search_thread.start()

    def _on_search_result(self, result):
        display = result[:450] + "..." if len(result) > 450 else result
        self._show_bubble(f"Sia ❤️: {display}")
        self.current_state = "idle"
        self._set_status("💤 Say 'Sia'...")
        self._reset_status_style()
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PROACTIVE ENGINE CALLBACKS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _proactive_speak(self, message):
        if self.current_state != "idle":
            return
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

        print("\n" + "═" * 55)
        print("  🎀 SIA v3.0 — Floating Desktop Assistant")
        print("  ✅ Transparent  ✅ Side Panel  ✅ Lip-Sync")
        print(f"  💖 Say 'Sia' to wake  |  Esc = Hide")
        print("═" * 55 + "\n")

        sia = SiaDesktop()
        sys.exit(app.exec_())

    except Exception as e:
        print(f"❌ Fatal: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
