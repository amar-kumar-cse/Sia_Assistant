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
import brain
import voice_engine
import actions
import listen_engine
import memory


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
        recognizer.energy_threshold = 300
        recognizer.pause_threshold = 0.5

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
                                text = recognizer.recognize_google(audio).lower()
                                if "sia" in text:
                                    print("⚡ Wake word 'Sia' detected!")
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
                            print(f"⚠️ Wake word inner error: {e}")
                            time.sleep(1)
            except Exception as e:
                print(f"⚠️ Microphone error: {e}")
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


class SpeakThread(QThread):
    """Thread for voice synthesis."""
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text

    def run(self):
        self.speaking_started.emit()
        voice_engine.speak(self.text)
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

        # ── Window Configuration ──
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnBottomHint |  # Stay behind other windows like wallpaper
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.showFullScreen()

        # ── State ──
        self.current_state = "idle"  # idle, listening, thinking, speaking
        self.bubble_text = ""
        self.bubble_display_text = ""
        self.typewriter_index = 0
        self.tick = 0.0
        self.character_pixmap = None
        self.character_rect = QRect()
        self.stars = []
        self.is_on_top = False

        # ── Load Resources ──
        self._load_character()
        self._generate_stars()

        # ── Speech Bubble Config ──
        self.bubble_max_width = 600
        self.bubble_padding = 20
        self.bubble_visible = True

        # ── Create UI Elements ──
        self._create_status_indicator()
        self._create_avatar_badge()
        self._create_control_buttons()

        # ── Typewriter Timer ──
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self._typewriter_tick)

        # ── Animation Timer ──
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animation_tick)
        self.anim_timer.start(50)  # 20 FPS

        # ── Breathing animation for character ──
        self.breath_offset = 0.0

        # ── Initialize Backend ──
        memory.preload_cache()

        # ── Welcome Message ──
        hour = time.localtime().tm_hour
        if 5 <= hour < 12:
            greeting = "Good Morning Hero! ☀️ Aaj ka din amazing hoga! 💪"
        elif 12 <= hour < 17:
            greeting = "Hey Hero! 🌤️ Afternoon ho gayi, kuch khaaya? 😊"
        elif 17 <= hour < 21:
            greeting = "Good Evening Hero! 🌙 Kaisa raha aaj ka din? ❤️"
        else:
            greeting = "Hey Hero! 🌙 Itni raat ko jaag rahe ho? Take care yaar! 💤"

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

        # ── System Tray ──
        self._create_system_tray()

        print("✅ Sia Desktop Assistant is LIVE!")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RESOURCE LOADING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _load_character(self):
        """Load the Sia character image."""
        paths_to_try = [
            os.path.join(ASSETS_DIR, "sia_idle_1.png"),
            os.path.join(SCRIPT_DIR, "sia_idle.png"),
            os.path.join(ASSETS_DIR, "sia_idle.png"),
        ]
        for path in paths_to_try:
            if os.path.exists(path):
                self.character_pixmap = QPixmap(path)
                print(f"✅ Loaded character: {path}")
                return
        print("⚠️ No character image found!")

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

    def _create_control_buttons(self):
        """Create minimal control buttons."""
        button_style = """
            QPushButton {{
                background-color: rgba(0, 0, 0, 160);
                color: {color};
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            QPushButton:hover {{
                background-color: rgba(40, 40, 60, 200);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(60, 60, 80, 220);
            }}
        """

        # Mic button
        self.mic_btn = QPushButton("🎤 Voice", self)
        self.mic_btn.setStyleSheet(button_style.format(color="#FF6B98"))
        self.mic_btn.setFixedSize(120, 44)
        self.mic_btn.clicked.connect(self._manual_voice_input)
        self.mic_btn.setCursor(Qt.PointingHandCursor)

        # Toggle window mode
        self.toggle_btn = QPushButton("📌 Pin Top", self)
        self.toggle_btn.setStyleSheet(button_style.format(color="#00FFCC"))
        self.toggle_btn.setFixedSize(120, 44)
        self.toggle_btn.clicked.connect(self._toggle_on_top)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)

        # Exit button
        self.exit_btn = QPushButton("✕", self)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 160);
                color: #FF6B6B;
                font-size: 18px;
                font-weight: bold;
                border-radius: 20px;
                border: 1px solid rgba(255, 107, 107, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 100);
                border: 1px solid rgba(255, 107, 107, 0.6);
            }
        """)
        self.exit_btn.setFixedSize(40, 40)
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setCursor(Qt.PointingHandCursor)

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
        """Custom painting for the entire screen."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        # ── Background Gradient ──
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor(15, 15, 35))
        bg_grad.setColorAt(0.3, QColor(20, 18, 40))
        bg_grad.setColorAt(0.7, QColor(12, 12, 30))
        bg_grad.setColorAt(1.0, QColor(8, 8, 20))
        painter.fillRect(0, 0, w, h, bg_grad)

        # ── Subtle radial glow behind character ──
        center_x = w // 2
        center_y = int(h * 0.42)
        glow = QRadialGradient(center_x, center_y, min(w, h) * 0.45)
        glow.setColorAt(0.0, QColor(40, 30, 80, 60))
        glow.setColorAt(0.3, QColor(25, 20, 60, 30))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), min(w, h) * 0.45, min(w, h) * 0.4)

        # ── Stars ──
        for star in self.stars:
            painter.setPen(Qt.NoPen)
            c = QColor(255, 255, 255, int(255 * star.opacity))
            painter.setBrush(c)
            painter.drawEllipse(QPointF(star.x, star.y), star.size, star.size)

        # ── Character ──
        if self.character_pixmap:
            # Scale character to fit nicely
            char_h = int(h * 0.72)
            scaled = self.character_pixmap.scaledToHeight(char_h, Qt.SmoothTransformation)
            char_x = center_x - scaled.width() // 2
            char_y = int(h * 0.08) + int(self.breath_offset)
            self.character_rect = QRect(char_x, char_y, scaled.width(), scaled.height())
            painter.drawPixmap(char_x, char_y, scaled)

        # ── Speech Bubble ──
        if self.bubble_visible and self.bubble_display_text:
            self._draw_speech_bubble(painter, w, h)

        painter.end()

    def _draw_speech_bubble(self, painter, w, h):
        """Draw the speech bubble with text."""
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

        # Position: below center, slightly left
        bub_x = int(w * 0.5 - bub_w * 0.5)
        bub_y = int(h * 0.80)

        # Clamp to screen
        bub_x = max(20, min(bub_x, w - bub_w - 20))
        bub_y = max(20, min(bub_y, h - bub_h - 60))

        # Draw bubble background
        bubble_rect = QRectF(bub_x, bub_y, bub_w, bub_h)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 15, 15)

        # Glassmorphism effect
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawPath(path)

        # Inner glow
        inner_glow = QLinearGradient(bub_x, bub_y, bub_x, bub_y + bub_h)
        inner_glow.setColorAt(0.0, QColor(255, 255, 255, 10))
        inner_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(inner_glow))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        # Draw emoji indicator
        indicator = "🔴❤️"
        ind_font = QFont("Segoe UI Emoji", 10)
        painter.setFont(ind_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(bub_x + 8, bub_y - 4, indicator)

        # Draw text
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 240))
        for i, line in enumerate(lines):
            lx = bub_x + pad
            ly = bub_y + pad + i * line_height + fm.ascent()
            painter.drawText(lx, ly, line)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  LAYOUT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def resizeEvent(self, event):
        """Position all UI elements on resize."""
        w, h = self.width(), self.height()

        # Status label - bottom left
        self.status_label.move(20, h - 50)

        # Avatar badge - bottom right
        self.avatar_badge.move(w - 80, h - 110)
        self.avatar_name.move(w - 80, h - 45)

        # Control buttons - bottom center
        btn_y = h - 55
        center = w // 2
        self.mic_btn.move(center - 130, btn_y)
        self.toggle_btn.move(center + 10, btn_y)

        # Exit button - top right
        self.exit_btn.move(w - 55, 15)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ANIMATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _animation_tick(self):
        """Main animation loop at 20 FPS."""
        self.tick += 0.05

        # Update stars twinkling
        for star in self.stars:
            star.update(self.tick)

        # Breathing animation for character
        self.breath_offset = math.sin(self.tick * 1.5) * 3.0

        # Status pulse animation
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
        if self.typewriter_index < len(self.bubble_text):
            self.typewriter_index += 1
            self.bubble_display_text = self.bubble_text[:self.typewriter_index]
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
        self.current_state = "listening"
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
        self.status_label.setText("🧠 Thinking...")
        self.status_label.adjustSize()
        self._show_bubble(f"Amar: {text}")

        print(f"🎤 Heard: {text}")
        memory.add_memory_log(f"Voice: {text}")

        # Generate AI response
        self.think_thread = ThinkThread(text)
        self.think_thread.response_ready.connect(self._on_response_ready)
        self.think_thread.start()

    def _on_response_ready(self, response):
        """Handle AI response."""
        self.current_state = "speaking"
        self.status_label.setText("💬 Speaking...")
        self.status_label.adjustSize()
        self._show_bubble(f"Sia ❤️: {response}")

        print(f"💬 Sia: {response}")
        memory.add_memory_log(f"Sia: {response}")

        # Speak the response
        self.speak_thread = SpeakThread(response)
        self.speak_thread.speaking_finished.connect(self._on_speaking_finished)
        self.speak_thread.start()

    def _on_speaking_finished(self):
        """Handle speech completion - resume wake word listening."""
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

        # Resume wake word detection
        if self.wake_thread and self.wake_thread.isRunning():
            self.wake_thread.resume()

    def _on_listen_failed(self):
        """Handle failed speech recognition."""
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
        self.status_label.setText("👂 Listening... (Speak now!)")
        self.status_label.adjustSize()
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
    # Enable high DPI
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
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

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
