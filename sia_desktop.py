"""
SIA - Premium Full-Screen Desktop Virtual Assistant
Wallpaper-style always-on anime character with speech bubbles
Built for Amar - B.Tech CSE @ RIT Roorkee
"""

import sys
import os
import math
import random
import threading
import time
import traceback

# Global exception handler moved to main() loop for better PyQt compatibility

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu, QAction, QLineEdit, QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, QSize, pyqtProperty, QPointF, QRectF
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QFont, QFontDatabase, QIcon,
    QRadialGradient, QLinearGradient, QPainterPath, QPen, QBrush,
    QFontMetrics
)

# Backend imports
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

# Colors
BG_DARK = QColor(15, 15, 30)
BG_GRADIENT_TOP = QColor(20, 20, 45)
BG_GRADIENT_BOTTOM = QColor(10, 10, 25)
BUBBLE_BG = QColor(0, 0, 0, 180)
BUBBLE_BORDER = QColor(255, 255, 255, 40)
TEXT_PRIMARY = QColor(255, 255, 255)
TEXT_ACCENT = QColor(0, 255, 204)  # Neon cyan
ACCENT_PINK = QColor(255, 107, 152)
ACCENT_PURPLE = QColor(118, 75, 162)
STAR_COLOR = QColor(255, 255, 255, 80)

# ── Mood Lighting Color Palettes ──
MOOD_COLORS = {
    "RELAX": {
        "bg_top": QColor(45, 30, 10, 200),
        "bg_mid": QColor(60, 40, 15, 180),
        "bg_bottom": QColor(35, 20, 5, 220),
        "glow": QColor(255, 160, 50, 60),
        "accent": QColor(255, 180, 80),
        "star": QColor(255, 200, 100, 80),
        "status_bg": "rgba(255, 160, 50, 160)",
        "status_border": "rgba(255, 180, 80, 0.5)",
    },
    "ENERGIZE": {
        "bg_top": QColor(40, 10, 10, 200),
        "bg_mid": QColor(60, 15, 20, 180),
        "bg_bottom": QColor(30, 5, 5, 220),
        "glow": QColor(255, 80, 60, 60),
        "accent": QColor(255, 100, 80),
        "star": QColor(255, 120, 100, 80),
        "status_bg": "rgba(255, 80, 60, 160)",
        "status_border": "rgba(255, 100, 80, 0.5)",
    },
    "FOCUS": {
        "bg_top": QColor(5, 15, 45, 200),
        "bg_mid": QColor(10, 25, 60, 180),
        "bg_bottom": QColor(5, 10, 35, 220),
        "glow": QColor(60, 120, 255, 60),
        "accent": QColor(80, 140, 255),
        "star": QColor(100, 180, 255, 80),
        "status_bg": "rgba(60, 120, 255, 160)",
        "status_border": "rgba(80, 140, 255, 0.5)",
    },
    "DEFAULT": {
        "bg_top": QColor(15, 15, 35, 200),
        "bg_mid": QColor(20, 18, 40, 180),
        "bg_bottom": QColor(8, 8, 20, 220),
        "glow": QColor(40, 30, 80, 60),
        "accent": QColor(0, 255, 204),
        "star": QColor(255, 255, 255, 80),
        "status_bg": "rgba(0, 0, 0, 160)",
        "status_border": "rgba(0, 255, 204, 0.3)",
    },
    "CONCERNED": {
        "bg_top": QColor(30, 25, 40, 200),
        "bg_mid": QColor(40, 30, 50, 180),
        "bg_bottom": QColor(20, 15, 30, 220),
        "glow": QColor(150, 100, 200, 60),
        "accent": QColor(180, 120, 220),
        "star": QColor(180, 120, 220, 80),
        "status_bg": "rgba(150, 100, 200, 160)",
        "status_border": "rgba(180, 120, 220, 0.5)",
    },
    "SAD": {
        "bg_top": QColor(10, 15, 25, 200),
        "bg_mid": QColor(15, 20, 35, 180),
        "bg_bottom": QColor(5, 10, 20, 220),
        "glow": QColor(50, 80, 150, 60),
        "accent": QColor(80, 120, 200),
        "star": QColor(100, 150, 200, 80),
        "status_bg": "rgba(50, 80, 150, 160)",
        "status_border": "rgba(80, 120, 200, 0.5)",
    },
}

# Neon Glow Colors
NEON_BLUE = QColor(0, 180, 255)
NEON_PINK = QColor(255, 60, 170)
NEON_CYAN = QColor(0, 255, 220)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BACKGROUND THREADS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WakeWordThread(QThread):
    """Always-listening thread for 'Sia' wake word detection."""
    wake_word_detected = pyqtSignal()
    status_changed = pyqtSignal(str)  # "idle", "listening", "detected"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused = False

    def run(self):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        # ✅ WAKE WORD OPTIMIZATION: Sensitive detection
        recognizer.energy_threshold = 50  # ← Ultra-low for wake word detection
        recognizer.pause_threshold = 0.5
        recognizer.dynamic_energy_threshold = True

        while self.running:
            if self.paused:
                time.sleep(0.3)
                continue

            self.status_changed.emit("idle")
            try:
                import speech_recognition as sr
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    while self.running and not self.paused:
                        try:
                            audio = recognizer.listen(source, timeout=2, phrase_time_limit=3)
                            try:
                                text = recognizer.recognize_google(audio).lower()
                                if "sia" in text:
                                    app_logger.info("⚡ Wake word 'Sia' detected!")
                                    self.status_changed.emit("detected")
                                    self.wake_word_detected.emit()
                                    # Pause wake word detection while processing
                                    self.paused = True
                                    break
                            except sr.UnknownValueError:
                                pass
                            except sr.RequestError:
                                pass
                        except sr.WaitTimeoutError:
                            pass
                        except Exception as e:
                            app_logger.error(f"⚠️ Wake word inner error: {e}")
                            time.sleep(1)
            except Exception as e:
                app_logger.error(f"⚠️ Microphone error: {e}")
                time.sleep(3)

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False


class ListenThread(QThread):
    """Thread for active speech recognition (after wake word)."""
    text_recognized = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_failed = pyqtSignal()

    def run(self):
        self.listening_started.emit()
        text = listen_engine.listen()
        if text:
            self.text_recognized.emit(text)
        else:
            self.listening_failed.emit()


class ThinkThread(QThread):
    """Thread for AI response generation."""
    response_ready = pyqtSignal(str)

    def __init__(self, user_text, parent=None):
        super().__init__(parent)
        self.user_text = user_text

    def run(self):
        # Check for system actions
        action_result = actions.perform_action(self.user_text)
        if action_result:
            self.response_ready.emit(f"{action_result}")
            return
        # AI response
        response = brain.think(self.user_text)
        self.response_ready.emit(response)


class VisionThread(QThread):
    """Thread for visual intelligence (screenshot + analysis)."""
    result_ready = pyqtSignal(str)
    
    def __init__(self, question="Meri screen pe kya hai?", mode="screen", parent=None):
        super().__init__(parent)
        self.question = question
        self.mode = mode  # "screen" or "webcam"
    
    def run(self):
        try:
            from engine import vision_engine
            if self.mode == "webcam":
                result = vision_engine.analyze_webcam(self.question)
            else:
                result = vision_engine.analyze_screen(self.question)
            self.result_ready.emit(result)
        except Exception as e:
            self.result_ready.emit(f"[CONFUSED] Vision mein error: {str(e)[:50]}")


class WebSearchThread(QThread):
    """Thread for web search."""
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


class SpeakThread(QThread):
    """Thread for voice synthesis with emotion support."""
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()

    def __init__(self, text, emotion=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.emotion = emotion

    def run(self):
        self.speaking_started.emit()
        voice_engine.speak(self.text, emotion=self.emotion)
        self.speaking_finished.emit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PARTICLE / STAR SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Star:
    def __init__(self, x, y, size, opacity, speed):
        self.x = x
        self.y = y
        self.size = size
        self.opacity = opacity
        self.base_opacity = opacity
        self.speed = speed
        self.phase = random.uniform(0, 2 * math.pi)

    def update(self, tick):
        # Gentle twinkling
        self.opacity = self.base_opacity * (0.5 + 0.5 * math.sin(tick * self.speed + self.phase))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN APPLICATION WINDOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SiaDesktop(QWidget):
    """Full-screen wallpaper-style Sia Desktop Assistant."""

    def __init__(self):
        super().__init__()

        # ── State ──
        self.current_state = "idle"  # idle, listening, thinking, speaking
        self.bubble_text = ""
        self.bubble_display_text = ""
        self.typewriter_index = 0
        self.tick = 0.0
        self.character_pixmap = None
        self.character_rect = QRect()
        self.lip_pixmaps = []  # Initialize lip-sync frames list
        self.stars = []
        self.is_on_top = False
        self.current_mood = "DEFAULT"  # Mood Lighting state
        self.mood_transition = 0.0  # 0.0 = old mood, 1.0 = new mood
        self.weather_widget_ref = None  # Weather widget reference
        self.status_label = None
        self.avatar_badge = None
        self.avatar_name = None
        self.mic_btn = None
        self.toggle_btn = None
        self.exit_btn = None

        # ── Load Resources ──
        self._load_character()
        self._generate_stars()

        # ── Speech Bubble Config ──
        self.bubble_max_width = 600
        self.bubble_padding = 20
        self.bubble_visible = True

        # ── Create UI Elements (MUST be before showFullScreen) ──
        self._create_status_indicator()
        self._create_avatar_badge()
        self._create_control_buttons()

        # ── Show Window ──
        # CONCEPT 1: TRANSPARENT LAYER (Transparency Key) - Black pixels invisible
        # CONCEPT 2: ALWAYS ON TOP - WindowStaysOnTopHint
        # CONCEPT 3: SCREEN GEOMETRY - Full monitor coverage
        
        # Get screen geometry for full coverage
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # Set window flags: Always on top + Frameless + Tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |  # Always on top!
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        
        # Enable transparency
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setStyleSheet("background: transparent;")
        
        self.show()
        self.is_on_top = True
        
        # Apply transparency mask - make black pixels invisible
        # self._apply_transparency_mask()  # Disabled to let WA_TranslucentBackground work perfectly

        # ── Smart Transparency ──
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.target_opacity = 1.0
        self.current_opacity = 1.0
        self.last_active_time = time.time()
        
        # ── Simple Transparent Opacity Timer ──
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._check_idle_fade)
        self.idle_timer.start(1000)
        
        # ── Proactive Intelligence Engine (Background Thread) ──
        self._active_toasts = []  # prevent GC of toast widgets
        self.proactive_engine = SiaProactiveEngine(
            speak_function=self._proactive_speak,
            show_toast_function=self._show_proactive_toast
        )
        self.proactive_engine.start()

        # ── Typewriter Timer ──
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self._typewriter_tick)

        # ── Animation Timer ──
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animation_tick)
        self.anim_timer.start(50)  # 20 FPS

        # ── Breathing animation for character ──
        self.breath_offset = 0.0

        # ── Lip-Sync Animation State ──
        # Frame cycle: 0=closed, 1=semi, 2=open, 3=semi (loop)
        self.lip_frame_index = 0      # current position in the cycle
        self.lip_tick_counter = 0     # counts anim_timer ticks (50ms each)
        self.lip_tick_speed = 3       # advance frame every N ticks (~150ms)
        self.lip_pixmaps = []         # [closed, semi, open] QPixmap cache

        # ── Initialize Backend ──
        try:
            memory.preload_cache()
        except Exception as e:
            app_logger.warning(f"Memory preload skipped: {e}")

        # ── Welcome Message ──
        hour = time.localtime().tm_hour
        if 5 <= hour < 12:
            greeting = "Namaste Hero! ☀️ Good Morning! Aaj ka din amazing hoga! 💪"
        elif 12 <= hour < 17:
            greeting = "Namaste Hero! 🌤️ Afternoon ho gayi, kuch khaaya? 😊"
        elif 17 <= hour < 21:
            greeting = "Namaste Hero! 🌙 Good Evening! Kaisa raha aaj ka din? ❤️"
        else:
            greeting = "Namaste Hero! 🌙 Itni raat ko jaag rahe ho? Take care yaar! 💤"

        self._show_bubble(f"Sia ❤️: {greeting}")

        # ── Wake Word Thread ──
        self.wake_thread = WakeWordThread()
        self.wake_thread.wake_word_detected.connect(self._on_wake_word)
        self.wake_thread.status_changed.connect(self._on_status_change)
        self.wake_thread.start()

        # ── Thread references ──
        self.listen_thread = None
        self.think_thread = None
        self.speak_thread = None
        self.vision_thread = None
        self.search_thread = None

        # ── System Tray ──
        self._create_system_tray()

        app_logger.info("✅ Sia Desktop Assistant is LIVE!")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RESOURCE LOADING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_character(self, emotion="IDLE"):
        """Load the Sia character image based on emotion. Prefers HD avatar."""
        emotion_files = {
            "IDLE": ["Sia_closed.png", "sia_avatar_hd.png", "sia_idle.png"],
            "SMILE": ["Sia_open.png", "Sia_closed.png", "sia_happy.png", "sia_idle.png"],
            "HAPPY": ["Sia_open.png", "Sia_closed.png", "sia_happy.png", "sia_idle.png"],
            "SAD": ["Sia_closed.png", "sia_sad.png", "sia_idle.png"],
            "CONCERNED": ["Sia_closed.png", "sia_sad.png", "sia_idle.png"],
            "CONFUSED": ["Sia_semi.png", "Sia_closed.png", "sia_confused.png", "sia_idle.png"],
            "SURPRISED": ["Sia_open.png", "Sia_closed.png", "sia_surprised.png", "sia_idle.png"],
            "ANGRY": ["Sia_closed.png", "sia_angry.png", "sia_idle.png"]
        }
        
        filenames = emotion_files.get(emotion.upper(), ["Sia_closed.png", "sia_idle.png"])
        
        paths_to_try = []
        for fn in filenames:
            paths_to_try.extend([
                os.path.join(ASSETS_DIR, fn),
                os.path.join(SCRIPT_DIR, fn)
            ])
            
        for path in paths_to_try:
            if os.path.exists(path):
                # ✅ TRANSPARENCY: Load with RGBA to preserve alpha channel
                pixmap = QPixmap(path)
                if pixmap.hasAlphaChannel():
                    app_logger.info(f"✅ Loaded transparent avatar: {os.path.basename(path)}")
                else:
                    app_logger.warning(f"⚠️ Avatar has no alpha channel: {os.path.basename(path)}")
                    app_logger.info("💡 Tip: Use setup_transparent_avatar.py to remove background")
                self.character_pixmap = pixmap
                break
        else:
            app_logger.warning(f"⚠️ No character image found for {emotion} (or idle fallback)!")

        # ── Load Lip-Sync Frames (once, cached) ──
        if not self.lip_pixmaps:
            lip_files = ["Sia_closed.png", "Sia_semi.png", "Sia_open.png"]
            for lip_fn in lip_files:
                lp_path = os.path.join(ASSETS_DIR, lip_fn)
                lp = QPixmap(lp_path)
                if lp.isNull():
                    # Fallback: use the base character pixmap for all 3 frames
                    lp = self.character_pixmap
                else:
                    # ✅ TRANSPARENCY: Verify alpha channel
                    if not lp.hasAlphaChannel():
                        app_logger.debug(f"⚠️ Lip-sync frame missing alpha: {lip_fn}")
                self.lip_pixmaps.append(lp)
            app_logger.info(f"✅ Lip-sync frames loaded: {len(self.lip_pixmaps)} frames")

    def _generate_stars(self):
        """Generate starfield for background."""
        screen = QApplication.primaryScreen().geometry()
        for _ in range(120):
            self.stars.append(Star(
                x=random.randint(0, screen.width()),
                y=random.randint(0, screen.height()),
                size=random.uniform(1.0, 3.0),
                opacity=random.uniform(0.2, 0.8),
                speed=random.uniform(0.5, 2.0)
            ))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  UI ELEMENTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _create_status_indicator(self):
        """Create the status label at bottom-left."""
        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 160);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 8px 16px;
                border-radius: 12px;
                border: 1px solid rgba(0, 255, 204, 0.3);
            }
        """)
        self.status_label.setText("💤 Always Listening...")
        self.status_label.adjustSize()

    def _create_avatar_badge(self):
        """Create the small 'Sia' avatar badge in bottom-right."""
        self.avatar_badge = QLabel(self)
        self.avatar_badge.setStyleSheet("background-color: transparent; border: none;")
        self.avatar_badge.setFixedSize(60, 60)

        # Load the sia_idle.png as avatar
        avatar_path = os.path.join(SCRIPT_DIR, "sia_idle.png")
        if os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Make circular
            rounded = QPixmap(60, 60)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 60, 60)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.setPen(QPen(QColor(0, 255, 204, 150), 2))
            painter.drawEllipse(1, 1, 58, 58)
            painter.end()
            self.avatar_badge.setPixmap(rounded)

        # "Sia" label below badge
        self.avatar_name = QLabel("Sia", self)
        self.avatar_name.setStyleSheet("""
            QLabel {
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)
        self.avatar_name.setAlignment(Qt.AlignCenter)
        self.avatar_name.setFixedWidth(60)

    def _apply_transparency_mask(self):
        """CONCEPT 1: Make black/dark pixels transparent using mask."""
        from PyQt5.QtGui import QBitmap
        
        pixmap = self.grab()
        mask = QBitmap(pixmap.size())
        mask.fill(Qt.white)
        
        painter = QPainter(mask)
        painter.setPen(Qt.NoPen)
        image = pixmap.toImage()
        
        # Sample every 4th pixel for performance
        for y in range(0, image.height(), 4):
            for x in range(0, image.width(), 4):
                color = image.pixelColor(x, y)
                if color.lightness() < 25:  # Dark pixels become transparent
                    painter.setBrush(Qt.black)
                    painter.drawRect(x, y, 4, 4)
        
        painter.end()
        self.setMask(mask)
        print("[OK] Transparency mask applied")



    def _create_control_buttons(self):
        """Create sleek minimalist control bar buttons with glass effect."""
        button_style = """
            QPushButton {{
                background-color: rgba(15, 15, 35, 180);
                color: {color};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 22px;
                border: 1px solid rgba({border_rgb}, 0.25);
            }}
            QPushButton:hover {{
                background-color: rgba(30, 30, 60, 220);
                border: 1px solid rgba({border_rgb}, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba(50, 50, 80, 240);
            }}
        """

        # Mic button — neon pink
        self.mic_btn = QPushButton("🎤", self)
        self.mic_btn.setStyleSheet(button_style.format(color="#FF6B98", border_rgb="255, 107, 152"))
        self.mic_btn.setFixedSize(48, 48)
        self.mic_btn.clicked.connect(self._manual_voice_input)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setToolTip("Voice Input")
        self.mic_btn.hide()

        # Vision button — gold
        self.vision_btn = QPushButton("📷", self)
        self.vision_btn.setStyleSheet(button_style.format(color="#FFD700", border_rgb="255, 215, 0"))
        self.vision_btn.setFixedSize(48, 48)
        self.vision_btn.clicked.connect(self._vision_screen)
        self.vision_btn.setCursor(Qt.PointingHandCursor)
        self.vision_btn.setToolTip("Screen Vision")
        self.vision_btn.hide()

        # Search button — cyan
        self.search_btn = QPushButton("🔍", self)
        self.search_btn.setStyleSheet(button_style.format(color="#00BFFF", border_rgb="0, 191, 255"))
        self.search_btn.setFixedSize(48, 48)
        self.search_btn.clicked.connect(self._start_search)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setToolTip("Web Search")
        self.search_btn.hide()

        # Toggle window mode — neon green
        self.toggle_btn = QPushButton("📌", self)
        self.toggle_btn.setStyleSheet(button_style.format(color="#00FFCC", border_rgb="0, 255, 204"))
        self.toggle_btn.setFixedSize(48, 48)
        self.toggle_btn.clicked.connect(self._toggle_on_top)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setToolTip("Pin / Unpin")
        self.toggle_btn.hide()

        # Exit button — minimal circle
        self.exit_btn = QPushButton("✕", self)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 15, 35, 160);
                color: #FF6B6B;
                font-size: 16px;
                font-weight: bold;
                border-radius: 18px;
                border: 1px solid rgba(255, 107, 107, 0.2);
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 80);
                border: 1px solid rgba(255, 107, 107, 0.5);
            }
        """)
        self.exit_btn.setFixedSize(36, 36)
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setCursor(Qt.PointingHandCursor)
        self.exit_btn.hide()

    def _create_system_tray(self):
        """Create system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)

        # Use the avatar as tray icon
        icon_path = os.path.join(SCRIPT_DIR, "sia_idle.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))

        # Tray menu
        tray_menu = QMenu()

        show_action = QAction("👁️ Show Sia", self)
        show_action.triggered.connect(self.showFullScreen)
        tray_menu.addAction(show_action)

        hide_action = QAction("👻 Hide Sia", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("❌ Exit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Sia - Your AI Assistant ❤️")
        self.tray_icon.show()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PAINTING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def paintEvent(self, event):
        """Enhanced painting with improved visual effects."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.HighQualityAntialiasing)
        w, h = self.width(), self.height()

        # ✅ TRANSPARENCY FIX: No background fill - true transparency!
        # The window background is transparent - only draw avatar and effects

        # ── Enhanced multi-layer glow effect ──
        mood = MOOD_COLORS.get(self.current_mood, MOOD_COLORS["DEFAULT"])
        center_x = w // 2
        center_y = int(h * 0.42)
        
        # Outer glow layer
        outer_glow = QRadialGradient(center_x, center_y, min(w, h) * 0.70)
        outer_glow.setColorAt(0.0, QColor(mood["glow"].red(), mood["glow"].green(), mood["glow"].blue(), 20))
        outer_glow.setColorAt(0.5, QColor(mood["glow"].red() // 3, mood["glow"].green() // 3, mood["glow"].blue() // 3, 10))
        outer_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(outer_glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), min(w, h) * 0.70, min(w, h) * 0.65)
        
        # Inner glow layer (brighter)
        inner_glow = QRadialGradient(center_x, center_y, min(w, h) * 0.50)
        inner_glow.setColorAt(0.0, QColor(mood["glow"].red(), mood["glow"].green(), mood["glow"].blue(), 45))
        inner_glow.setColorAt(0.3, QColor(mood["glow"].red() // 2, mood["glow"].green() // 2, mood["glow"].blue() // 2, 30))
        inner_glow.setColorAt(0.7, QColor(mood["glow"].red() // 4, mood["glow"].green() // 4, mood["glow"].blue() // 4, 15))
        inner_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(inner_glow))
        painter.drawEllipse(QPointF(center_x, center_y), min(w, h) * 0.50, min(w, h) * 0.45)

        # ── Enhanced animated neon ring ──
        neon_alpha = int(25 + 20 * math.sin(self.tick * 2.5))
        neon_pulse = int(5 + 3 * math.sin(self.tick * 4))
        neon_pen = QPen(QColor(mood["accent"].red(), mood["accent"].green(), mood["accent"].blue(), neon_alpha), 1.5 + neon_pulse * 0.1)
        painter.setPen(neon_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), min(w, h) * 0.38, min(w, h) * 0.36)
        
        # Secondary ring for depth
        secondary_alpha = neon_alpha // 2
        secondary_pen = QPen(QColor(0, 180, 255, secondary_alpha), 0.8)
        painter.setPen(secondary_pen)
        painter.drawEllipse(QPointF(center_x, center_y), min(w, h) * 0.42, min(w, h) * 0.40)

        # ── Stars ──
        for star in self.stars:
            painter.setPen(Qt.NoPen)
            c = QColor(255, 255, 255, int(255 * star.opacity))
            painter.setBrush(c)
            painter.drawEllipse(QPointF(star.x, star.y), star.size, star.size)

        # ── Character with drop shadow ──
        if self.character_pixmap:
            char_h = int(h * 0.72)
            # Pick the correct lip-sync frame when speaking, else default
            cycle_map = [0, 1, 2, 1]
            if self.current_state == "speaking" and self.lip_pixmaps:
                frame_idx = cycle_map[self.lip_frame_index % len(cycle_map)]
                active_pixmap = self.lip_pixmaps[frame_idx]
            else:
                active_pixmap = self.character_pixmap
            scaled = active_pixmap.scaledToHeight(char_h, Qt.SmoothTransformation)
            char_x = center_x - scaled.width() // 2
            # Move her significantly up (equivalent to adjusting y-geometry offset earlier)
            char_y = int(h * 0.02) + int(self.breath_offset)
            self.character_rect = QRect(char_x, char_y, scaled.width(), scaled.height())
            
            # Soft shadow beneath character
            shadow_grad = QRadialGradient(center_x, char_y + scaled.height() - 20, scaled.width() * 0.4)
            shadow_grad.setColorAt(0.0, QColor(0, 0, 0, 50))
            shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(shadow_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(center_x, char_y + scaled.height() - 10),
                               scaled.width() * 0.35, 20)
            
            painter.drawPixmap(char_x, char_y, scaled)

        # ── Speech Bubble ──
        if self.bubble_visible and self.bubble_display_text:
            self._draw_speech_bubble(painter, w, h)

        # ── Waveform (speaking OR listening) ──
        if self.current_state in ("speaking", "listening"):
            self._draw_waveform(painter, w, h)

        painter.end()

    def _draw_speech_bubble(self, painter, w, h):
        """Draw neon-glow speech bubble with glassmorphism."""
        # Font
        font = QFont("Segoe UI", 14)
        font.setWeight(QFont.Normal)
        painter.setFont(font)
        fm = QFontMetrics(font)

        text = self.bubble_display_text
        pad = self.bubble_padding
        max_w = min(self.bubble_max_width, int(w * 0.5))

        # Word-wrap text
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            if fm.horizontalAdvance(test_line) > max_w - pad * 2:
                if current_line:
                    lines.append(current_line)
                current_line = word
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)

        if not lines:
            return

        line_height = fm.height() + 4
        text_height = line_height * len(lines)
        text_width = max(fm.horizontalAdvance(line) for line in lines)

        bub_w = text_width + pad * 2
        bub_h = text_height + pad * 2

        # Position: below center
        bub_x = int(w * 0.5 - bub_w * 0.5)
        bub_y = int(h * 0.80)

        # Clamp to screen
        bub_x = max(20, min(bub_x, w - bub_w - 20))
        bub_y = max(20, min(bub_y, h - bub_h - 60))

        bubble_rect = QRectF(bub_x, bub_y, bub_w, bub_h)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 18, 18)

        # ── Neon Glow Layers (outer to inner) ──
        is_speaking = self.current_state == "speaking"
        # Pulse intensity: oscillates between 0.4 and 1.0 when speaking
        pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self.tick * 4)) if is_speaking else 0.35

        # Layer 1: Outermost diffuse glow
        glow_spread = 12
        glow_rect_outer = QRectF(bub_x - glow_spread, bub_y - glow_spread,
                                  bub_w + glow_spread * 2, bub_h + glow_spread * 2)
        glow_path_outer = QPainterPath()
        glow_path_outer.addRoundedRect(glow_rect_outer, 26, 26)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 150, 255, int(18 * pulse)))
        painter.drawPath(glow_path_outer)

        # Layer 2: Mid glow
        glow_spread2 = 6
        glow_rect_mid = QRectF(bub_x - glow_spread2, bub_y - glow_spread2,
                                bub_w + glow_spread2 * 2, bub_h + glow_spread2 * 2)
        glow_path_mid = QPainterPath()
        glow_path_mid.addRoundedRect(glow_rect_mid, 22, 22)
        painter.setBrush(QColor(0, 180, 255, int(30 * pulse)))
        painter.drawPath(glow_path_mid)

        # ── Glass bubble fill ──
        painter.setPen(QPen(QColor(0, 180, 255, int(80 * pulse)), 1.5))
        painter.setBrush(QColor(10, 10, 30, 180))
        painter.drawPath(path)

        # Inner frosted glass gradient
        inner_glow = QLinearGradient(bub_x, bub_y, bub_x, bub_y + bub_h)
        inner_glow.setColorAt(0.0, QColor(100, 150, 255, 18))
        inner_glow.setColorAt(0.5, QColor(255, 255, 255, 5))
        inner_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(inner_glow))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # ── Pink neon accent on bottom edge ──
        accent_path = QPainterPath()
        accent_rect = QRectF(bub_x, bub_y, bub_w, bub_h)
        accent_path.addRoundedRect(accent_rect, 18, 18)
        pink_alpha = int(40 * pulse)
        painter.setPen(QPen(QColor(255, 60, 170, pink_alpha), 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(accent_path)

        # Draw emoji indicator
        indicator = "🔴❤️"
        ind_font = QFont("Segoe UI Emoji", 10)
        painter.setFont(ind_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(bub_x + 8, bub_y - 4, indicator)

        # Draw text with subtle text shadow
        painter.setFont(font)
        for i, line in enumerate(lines):
            lx = bub_x + pad
            ly = bub_y + pad + i * line_height + fm.ascent()
            # Shadow
            painter.setPen(QColor(0, 100, 200, 40))
            painter.drawText(lx + 1, ly + 1, line)
            # Main text
            painter.setPen(QColor(255, 255, 255, 245))
            painter.drawText(lx, ly, line)

    def _draw_waveform(self, painter, w, h):
        """Draw a minimalist animated waveform during speaking or listening."""
        center_x = w // 2
        base_y = int(h * 0.96)
        painter.setRenderHint(QPainter.Antialiasing)

        is_listening = self.current_state == "listening"
        is_speaking = self.current_state == "speaking"

        # Amplitude varies by state
        if is_speaking:
            amp = 25 + 12 * math.sin(self.tick * 5)
            primary_color = QColor(0, 255, 204, 200)  # Cyan
            secondary_color = QColor(255, 60, 170, 140)  # Pink
            speed = 8
        else:  # listening
            amp = 15 + 8 * math.sin(self.tick * 3)
            primary_color = QColor(255, 107, 107, 180)  # Red-ish
            secondary_color = QColor(255, 180, 80, 120)  # Warm
            speed = 5

        num_points = 80
        width = 350
        start_x = center_x - width // 2

        # ── "Listening..." text label ──
        if is_listening:
            label_font = QFont("Segoe UI", 11)
            label_font.setWeight(QFont.DemiBold)
            painter.setFont(label_font)
            dot_count = int(self.tick * 2) % 4
            label_text = "Listening" + "." * dot_count
            lfm = QFontMetrics(label_font)
            label_w = lfm.horizontalAdvance(label_text)
            # Glow behind text
            painter.setPen(QColor(255, 107, 107, 60))
            painter.drawText(center_x - label_w // 2 + 1, base_y - 28, label_text)
            painter.setPen(QColor(255, 200, 200, 220))
            painter.drawText(center_x - label_w // 2, base_y - 30, label_text)

        # Primary Wave
        points = []
        for i in range(num_points):
            x = start_x + (i / num_points) * width
            envelope = math.exp(-((x - center_x) ** 2) / (2 * 55**2))
            y = base_y + envelope * amp * math.sin(i * 0.5 + self.tick * speed)
            points.append(QPointF(x, y))

        path1 = QPainterPath()
        path1.moveTo(points[0])
        for p in points[1:]:
            path1.lineTo(p)

        painter.setPen(QPen(primary_color, 2.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path1)

        # Secondary Wave (offset)
        points2 = []
        for i in range(num_points):
            x = start_x + (i / num_points) * width
            envelope = math.exp(-((x - center_x) ** 2) / (2 * 55**2))
            y = base_y + envelope * (amp * 0.55) * math.sin(i * 0.7 - self.tick * (speed * 0.75))
            points2.append(QPointF(x, y))

        path2 = QPainterPath()
        path2.moveTo(points2[0])
        for p in points2[1:]:
            path2.lineTo(p)

        painter.setPen(QPen(secondary_color, 1.5))
        painter.drawPath(path2)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  LAYOUT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def resizeEvent(self, event):
        """Position all UI elements on resize — minimalist control bar."""
        w, h = self.width(), self.height()

        # Status label - bottom left
        self.status_label.move(20, h - 50)

        # Avatar badge - bottom right
        self.avatar_badge.move(w - 80, h - 110)
        self.avatar_name.move(w - 80, h - 45)

        # Control bar — compact icon row, bottom center
        btn_y = h - 58
        btn_gap = 56  # 48px button + 8px gap
        total_w = btn_gap * 4
        start_x = (w - total_w) // 2
        self.mic_btn.move(start_x, btn_y)
        self.vision_btn.move(start_x + btn_gap, btn_y)
        self.search_btn.move(start_x + btn_gap * 2, btn_y)
        self.toggle_btn.move(start_x + btn_gap * 3, btn_y)

        # Exit button - top right
        self.exit_btn.move(w - 50, 12)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ANIMATION & PROACTIVE LOOPS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  PROACTIVE ENGINE CALLBACKS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _proactive_speak(self, message):
        """Thread-safe callback for proactive engine to make Sia speak."""
        if self.current_state != "idle":
            return  # Don't interrupt active conversations
        self.speak_thread = SpeakThread(message, "SMILE")
        self.speak_thread.speaking_started.connect(self._on_speaking_started)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()
        self._show_bubble(f"Sia 🔔: {message}")

    def _show_proactive_toast(self, message):
        """Show a floating visual toast notification on screen."""
        try:
            toast = ToastNotification(f"🔔 Sia: {message}")
            toast.show_toast()
            self._active_toasts.append(toast)
            # Cleanup old closed toasts
            self._active_toasts = [t for t in self._active_toasts if t.isVisible()]
        except Exception as e:
            app_logger.error(f"Toast notification error: {e}")

    def _check_idle_fade(self):
        """Fade out if idle for 15 seconds to stay out of the way while coding."""
        if self.current_state == "idle" and time.time() - self.last_active_time > 15:
            self.target_opacity = 0.35 # Smart Transparency
        else:
            self.target_opacity = 1.0
            if self.current_state != "idle":
                self.last_active_time = time.time()

    def _animation_tick(self):
        """Global animation tick (50ms = 20 FPS)."""
        self.tick += 0.1
        self.breath_offset = math.sin(self.tick * 1.5) * 3.0

        # ── Lip-Sync Frame Cycling ──
        if self.lip_pixmaps:
            if self.current_state == "speaking":
                self.lip_tick_counter += 1
                if self.lip_tick_counter >= self.lip_tick_speed:
                    self.lip_tick_counter = 0
                    # Cycle: 0(closed)->1(semi)->2(open)->3(semi)->0...
                    # We map indices [0,1,2,3] -> frames [0,1,2,1]
                    cycle_map = [0, 1, 2, 1]
                    self.lip_frame_index = (self.lip_frame_index + 1) % len(cycle_map)
            else:
                # Reset to closed mouth when not speaking
                self.lip_frame_index = 0
                self.lip_tick_counter = 0
        
        # Smooth Opacity transition
        if abs(self.current_opacity - self.target_opacity) > 0.01:
            self.current_opacity += (self.target_opacity - self.current_opacity) * 0.1
            self.opacity_effect.setOpacity(self.current_opacity)
        
        # Update stars twinkling
        for star in self.stars:
            star.update(self.tick)

        # Status pulse animation
        if self.status_label:
            if self.current_state == "listening":
                pulse = int(180 + 75 * math.sin(self.tick * 4))
                self.status_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba(255, 107, 107, {pulse});
                        color: white;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 13px;
                        padding: 8px 16px;
                        border-radius: 12px;
                        border: 1px solid rgba(255, 107, 107, 0.5);
                    }}
                """)
            elif self.current_state == "speaking":
                pulse = int(150 + 80 * math.sin(self.tick * 3))
                self.status_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba(118, 75, 162, {pulse});
                        color: white;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 13px;
                        padding: 8px 16px;
                        border-radius: 12px;
                        border: 1px solid rgba(118, 75, 162, 0.5);
                    }}
                """)

        self.update()

    def _typewriter_tick(self):
        """Typewriter effect for speech bubble text."""
        text = str(self.bubble_text)
        if self.typewriter_index < len(text):
            self.typewriter_index += 1
            self.bubble_display_text = text[:self.typewriter_index]
            self.update()
        else:
            self.typewriter_timer.stop()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  BUBBLE MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _show_bubble(self, text):
        """Show text in speech bubble with typewriter effect."""
        self.bubble_text = text
        self.bubble_display_text = ""
        self.typewriter_index = 0
        self.bubble_visible = True
        self.typewriter_timer.start(30)  # ~33 chars per second

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  VOICE PIPELINE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_wake_word(self):
        """Handle wake word detection - start active listening."""
        self.last_active_time = time.time()
        self.current_state = "listening"
        if self.status_label:
            self.status_label.setText("👂 Listening... (Speak now!)")
            self.status_label.adjustSize()
        self._show_bubble("Sia ❤️: Haan bolo Hero, main sun rahi hoon! 👂")

        # Start active listening
        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_text_recognized)
        self.listen_thread.listening_failed.connect(self._on_listen_failed)
        self.listen_thread.start()

    def _on_text_recognized(self, text):
        """Handle recognized speech text."""
        self.current_state = "thinking"
        if self.status_label:
            self.status_label.setText("🧠 Thinking...")
            self.status_label.adjustSize()
        self._show_bubble(f"Amar: {text}")

        app_logger.info(f"🎤 Heard: {text}")
        memory.add_memory_log(f"Voice: {text}")

        # Generate AI response
        self.think_thread = ThinkThread(text)
        self.think_thread.response_ready.connect(self._on_response_ready)
        self.think_thread.start()

    def _on_response_ready(self, response):
        """Handle AI response with emotion detection, mood lighting, and widget signals."""
        # --- IGNORE Handler: Background chatter detected ---
        if response.strip() == "[IGNORE]":
            app_logger.info("[IGNORE] Background chatter detected, resuming wake word listen.")
            self.current_state = "idle"
            if self.status_label:
                self.status_label.setText("💤 Always Listening...")
                self.status_label.adjustSize()
            if hasattr(self, 'wake_thread') and self.wake_thread and self.wake_thread.isRunning():
                self.wake_thread.resume()
            return

        # ── MOOD_CHANGE Signal Handler ──
        if response.startswith("MOOD_CHANGE:"):
            parts = response.split(":", 2)
            if len(parts) == 3:
                mood = parts[1]   # RELAX, ENERGIZE, FOCUS
                text = parts[2]
                self._apply_mood_lighting(mood)
                self.current_state = "speaking"
                if self.status_label:
                    mood_labels = {"RELAX": "🧡 Relax Mode", "ENERGIZE": "🔥 Energy Mode", "FOCUS": "🎯 Focus Mode"}
                    self.status_label.setText(mood_labels.get(mood, "✨ Mood Active"))
                    self.status_label.adjustSize()
                self._show_bubble(f"Sia 🧡: {text}")
                app_logger.info(f"🎨 Mood Lighting → {mood}: {text}")
                self.speak_thread = SpeakThread(text, emotion="SMILE")
                self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
                self.speak_thread.start()
                # Auto-reset mood after 3 minutes
                QTimer.singleShot(180000, self._reset_mood_lighting)
                return

        # ── SHOW_WIDGET Signal Handler ──
        if response.startswith("SHOW_WIDGET:WEATHER:"):
            city = response.split(":", 2)[2].strip()
            self._show_weather_widget(city)
            text = f"Hero, main {city} ka weather widget open kar rahi hoon! 🌤️ Dekho desktop pe! ❤️"
            self.current_state = "speaking"
            if self.status_label:
                self.status_label.setText("🌤️ Weather Widget Open")
                self.status_label.adjustSize()
            self._show_bubble(f"Sia ❤️: {text}")
            app_logger.info(f"🌤️ Weather Widget → {city}")
            self.speak_thread = SpeakThread(text, emotion="HAPPY")
            self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
            self.speak_thread.start()
            return

        # Parse emotion tag if present
        import re
        emotion_match = re.search(r'\[(.*?)\]', response)
        emotion = "IDLE"
        if emotion_match:
            emotion = emotion_match.group(1).upper()
            # Remove tag from display text
            response = response.replace(f"[{emotion_match.group(1)}]", "").strip()
            
        self._load_character(emotion)
        
        self.current_state = "speaking"

        if self.status_label:
            self.status_label.setText("💬 Speaking...")
            self.status_label.adjustSize()
        self._show_bubble(f"Sia ❤️: {response}")

        app_logger.info(f"💬 Sia: {response}")
        memory.add_memory_log(f"Sia: {response}")

        # Speak with emotion-adaptive voice
        self.speak_thread = SpeakThread(response, emotion=emotion)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MOOD LIGHTING SYSTEM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _apply_mood_lighting(self, mood):
        """Apply mood-specific color scheme to the entire UI."""
        self.current_mood = mood
        colors = MOOD_COLORS.get(mood, MOOD_COLORS["DEFAULT"])
        app_logger.info(f"🎨 Mood Lighting applied: {mood}")
        if self.status_label:
            accent = colors["accent"]
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors['status_bg']};
                    color: white;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    padding: 8px 16px;
                    border-radius: 12px;
                    border: 1px solid {colors['status_border']};
                }}
            """)
        self.update()  # Trigger repaint with new mood colors

    def _reset_mood_lighting(self):
        """Reset mood lighting back to default."""
        self.current_mood = "DEFAULT"
        app_logger.info("🎨 Mood Lighting reset to DEFAULT")
        if self.status_label:
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 160);
                    color: #00FFCC;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    padding: 8px 16px;
                    border-radius: 12px;
                    border: 1px solid rgba(0, 255, 204, 0.3);
                }
            """)
        self.update()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  WEATHER WIDGET SYSTEM
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _show_weather_widget(self, city):
        """Pop up a floating weather widget on the desktop."""
        try:
            # Close any existing weather widget
            if self.weather_widget_ref and self.weather_widget_ref.isVisible():
                self.weather_widget_ref.close()
            self.weather_widget_ref = WeatherWidget(city=city)
            self.weather_widget_ref.show()
            app_logger.info(f"🌤️ Weather Widget shown for: {city}")
        except Exception as e:
            app_logger.error(f"Weather widget error: {e}")

    def _on_speaking_started(self):
        """Handle speech started signal."""
        pass

    def _on_speaking_finished(self):
        """Handle speech completion - resume wake word listening."""
        self.last_active_time = time.time()
        # Revert to idle expression
        self._load_character("IDLE")
        
        self.current_state = "idle"
        if self.status_label:
            # Use mood-aware status label
            if self.current_mood != "DEFAULT":
                mood_labels = {"RELAX": "🧡 Relaxing...", "ENERGIZE": "🔥 Energized!", "FOCUS": "🎯 Focused!"}
                self.status_label.setText(mood_labels.get(self.current_mood, "💤 Always Listening..."))
            else:
                self.status_label.setText("💤 Always Listening...")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: rgba(0, 0, 0, 160);
                        color: #00FFCC;
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 13px;
                        padding: 8px 16px;
                        border-radius: 12px;
                        border: 1px solid rgba(0, 255, 204, 0.3);
                    }
                """)
            self.status_label.adjustSize()

        # Resume wake word detection
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_listen_failed(self):
        """Handle failed speech recognition."""
        self.current_state = "idle"
        if self.status_label:
            self.status_label.setText("💤 Always Listening...")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 160);
                    color: #00FFCC;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 13px;
                    padding: 8px 16px;
                    border-radius: 12px;
                    border: 1px solid rgba(0, 255, 204, 0.3);
                }
            """)
            self.status_label.adjustSize()
        self._show_bubble("Sia ❤️: Kuch sunayi nahi diya... Dobara bolo na Hero! 😊")

        # Resume wake word
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_status_change(self, status):
        """Handle wake word thread status changes."""
        if status == "idle":
            pass  # Already handled
        elif status == "detected":
            pass  # Handled by _on_wake_word

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MANUAL INPUT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _manual_voice_input(self):
        """Manual microphone button press."""
        if self.current_state != "idle":
            return

        # Pause wake word and start listening
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.paused = True

        self.current_state = "listening"
        if self.status_label:
            self.status_label.setText("👂 Listening... (Speak now!)")
            self.status_label.adjustSize()
        if self.mic_btn:
            self.mic_btn.setEnabled(False)
            self.mic_btn.setText("⏳ ...")

        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_text_recognized)
        self.listen_thread.listening_failed.connect(self._on_manual_listen_failed)
        self.listen_thread.start()

    def _on_manual_listen_failed(self):
        """Handle failed manual listen."""
        self._on_listen_failed()
        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("🎤 Voice")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  VISION & SEARCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _vision_screen(self):
        """Capture and analyze screen via Visual Intelligence."""
        if self.current_state != "idle":
            return
        
        self.current_state = "thinking"
        if self.status_label:
            self.status_label.setText("📷 Analyzing screen...")
            self.status_label.adjustSize()
        self._show_bubble("Sia ❤️: Ruko Hero, tumhari screen dekh rahi hoon... 📷")
        if self.vision_btn:
            self.vision_btn.setEnabled(False)
        
        self.vision_thread = VisionThread(question="Meri screen pe kya hai? Error hai toh batao.", mode="screen")
        self.vision_thread.result_ready.connect(self._on_vision_result)
        self.vision_thread.start()
    
    def _on_vision_result(self, result):
        """Handle vision analysis result."""
        self.vision_btn.setEnabled(True)
        self._on_response_ready(result)
    
    def _start_search(self):
        """Start a web search - first listen for the query."""
        if self.current_state != "idle":
            return
        
        # Pause wake word and start listening for search query
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.paused = True
        
        self.current_state = "listening"
        self.status_label.setText("🔍 Kya search karna hai? Bolo!")
        self.status_label.adjustSize()
        self._show_bubble("Sia ❤️: Kya search karna hai Hero? Bolo! 🔍")
        self.search_btn.setEnabled(False)
        
        self.listen_thread = ListenThread()
        self.listen_thread.text_recognized.connect(self._on_search_query)
        self.listen_thread.listening_failed.connect(self._on_search_listen_failed)
        self.listen_thread.start()
    
    def _on_search_query(self, text):
        """Handle recognized search query."""
        self.current_state = "thinking"
        self.status_label.setText("🔍 Searching...")
        self.status_label.adjustSize()
        self._show_bubble(f"🔍 Searching: {text}")
        
        self.search_thread = WebSearchThread(text)
        self.search_thread.result_ready.connect(self._on_search_result)
        self.search_thread.start()
    
    def _on_search_result(self, result):
        """Handle web search result."""
        self.search_btn.setEnabled(True)
        # Show results in bubble (truncate for display)
        display_result = result[:500] + "..." if len(result) > 500 else result
        self._show_bubble(f"Sia ❤️: {display_result}")
        self.current_state = "idle"
        self.status_label.setText("💤 Always Listening...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 160);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 8px 16px;
                border-radius: 12px;
                border: 1px solid rgba(0, 255, 204, 0.3);
            }
        """)
        self.status_label.adjustSize()
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()
    
    def _on_search_listen_failed(self):
        """Handle failed search listen."""
        self.search_btn.setEnabled(True)
        self._on_listen_failed()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  WINDOW CONTROLS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _toggle_on_top(self):
        """Toggle between wallpaper mode and always-on-top."""
        self.is_on_top = not self.is_on_top
        if self.is_on_top:
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.toggle_btn.setText("📌 Unpin")
        else:
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnBottomHint |
                Qt.Tool
            )
            self.toggle_btn.setText("📌 Pin Top")
        self.showFullScreen()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Space and event.modifiers() == Qt.AltModifier:
            if self.isVisible():
                self.hide()
            else:
                self.showFullScreen()

    def _quit_app(self):
        """Clean shutdown."""
        if self.wake_thread:
            self.wake_thread.stop()
            self.wake_thread.wait(2000)
            
        if self.proactive_engine:
            self.proactive_engine.stop()
            
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """Handle window close."""
        self._quit_app()
        event.accept()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """Enhanced main with comprehensive error handling."""
    try:
        # Enable high DPI
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running in tray
        
        # Global exception handler
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.exit(0)
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            print(f"❌ Uncaught Exception: {error_msg}")
            
        sys.excepthook = handle_exception
        
        app.setApplicationName("Sia Desktop Assistant")
        app.setOrganizationName("Amar Tech")

        print("\n" + "═" * 60)
        print("  🎀 SIA - Premium Desktop Virtual Assistant")
        print("═" * 60)
        print("  📍 Built for: Amar (B.Tech CSE @ RIT Roorkee)")
        print("  🎯 Career: TCS, J.P. Morgan")
        print("  💖 Say 'Sia' to activate voice!")
        print("  ⌨️  Esc = Hide | Alt+Space = Toggle")
        print("═" * 60 + "\n")

        # Change working directory
        os.chdir(SCRIPT_DIR)

        sia = SiaDesktop()
        sia.show()

        print("🎀 Sia started successfully! Say 'Sia' to activate.")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
