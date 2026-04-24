"""
Sia AI - Video Character Widget
Black background ko Win32 colorkey se transparent banate hain.
Video modify karne ki zaroorat nahi!
"""

import os
import math
import time
import random

import win32gui
import win32con
import win32api

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QStackedWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QPixmap


# ── Asset paths ──────────────────────────────────────────────
IDLE_VIDEO     = "assets/idle.mp4"
THINKING_VIDEO = "assets/thinking.mp4"
IDLE_PNG       = "assets/sia_idle.png"
SEMI_PNG       = "assets/Sia_semi.png"

# ── States ───────────────────────────────────────────────────
STATE_IDLE     = "idle"
STATE_THINKING = "thinking"
STATE_TALKING  = "talking"
STATE_GREETING = "greeting"


class VideoCharacterWidget(QWidget):
    """
    Sia ka main animated widget.
    - Video mode: idle.mp4 / thinking.mp4 loop (black bg → transparent via Win32)
    - Sprite mode: PNG frames for talking lip sync
    - Fallback: agar video missing ho to sirf PNG use karo
    """

    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_state   = STATE_IDLE
        self.amplitude       = 0.0
        self.base_x          = 0
        self.base_y          = 0
        self._video_available = False
        self._greeting_done  = False
        self._loop_video     = True

        # ── Window flags: frameless, always on top, transparent ──
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")

        # ── UI setup ─────────────────────────────────────────────
        self._setup_ui()

        # ── Timers ───────────────────────────────────────────────
        # Breathing / position animation — 30fps
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_position)
        self._anim_timer.start(33)

        # Lip sync timer (talking state) — 30fps
        self._lipsync_timer = QTimer(self)
        self._lipsync_timer.timeout.connect(self._update_lipsync)

        # Random blink timer (sprite fallback only)
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)
        self._blink_timer.start(random.randint(3000, 5000))

        self._is_blinking = False

    # ════════════════════════════════════════════════════════════
    # UI SETUP
    # ════════════════════════════════════════════════════════════

    def _setup_ui(self):
        """Video widget + sprite label dono setup karo."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget: video ya sprite ek waqt ek
        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("background: black;")  # black → transparent via Win32
        layout.addWidget(self._stack)

        # ── Video player ─────────────────────────────────────────
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: black;")
        self._player = QMediaPlayer(self)
        self._player.setVideoOutput(self._video_widget)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._stack.addWidget(self._video_widget)   # index 0

        # ── Sprite label (fallback + talking) ────────────────────
        self._sprite_label = QLabel()
        self._sprite_label.setAlignment(Qt.AlignCenter)
        self._sprite_label.setStyleSheet("background: transparent;")
        self._stack.addWidget(self._sprite_label)   # index 1

        # ── Load PNGs ────────────────────────────────────────────
        self._px_idle = self._load_pixmap(IDLE_PNG)
        self._px_semi = self._load_pixmap(SEMI_PNG)

        # ── Check video files ─────────────────────────────────────
        self._video_available = (
            os.path.exists(IDLE_VIDEO) and
            os.path.exists(THINKING_VIDEO)
        )

        if self._video_available:
            print("[Sia] Video files mili — video mode active")
        else:
            print("[Sia] Video files nahi mili — sprite fallback active")
            self._show_sprite()

    def _load_pixmap(self, path):
        """PNG load karo, agar missing ho to None return karo."""
        if os.path.exists(path):
            return QPixmap(path)
        print(f"[Sia] PNG missing: {path}")
        return None

    # ════════════════════════════════════════════════════════════
    # WIN32 — BLACK → TRANSPARENT
    # ════════════════════════════════════════════════════════════

    def showEvent(self, event):
        """Window show hone ke baad Win32 colorkey set karo."""
        super().showEvent(event)
        try:
            hwnd = int(self.winId())

            # Extended style: layered + tool window
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_LAYERED
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            # Black color = transparent
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(0, 0, 0),   # pure black → transparent
                0,
                win32con.LWA_COLORKEY
            )
            print("[Sia] Win32 colorkey set — black background transparent hai")
        except Exception as e:
            print(f"[Sia] Win32 colorkey error: {e}")

    # ════════════════════════════════════════════════════════════
    # STATE MACHINE
    # ════════════════════════════════════════════════════════════

    def set_state(self, state):
        """
        State switch karo.
        idle | thinking | talking | greeting
        """
        if state == self.current_state and state != STATE_TALKING:
            return

        self.current_state = state
        self.state_changed.emit(state)
        print(f"[Sia] State -> {state}")

        if state == STATE_IDLE:
            self._lipsync_timer.stop()
            self._play_video(IDLE_VIDEO, loop=True)

        elif state == STATE_THINKING:
            self._lipsync_timer.stop()
            self._play_video(THINKING_VIDEO, loop=True)

        elif state == STATE_TALKING:
            self._lipsync_timer.start(33)
            # Video band karo, sprite pe jaao
            self._player.stop()
            self._show_sprite(self._px_idle)

        elif state == STATE_GREETING:
            self._lipsync_timer.stop()
            self._greeting_done = False
            self._play_video(IDLE_VIDEO, loop=False)  # ek baar

    def on_amplitude(self, amp):
        """Voice amplitude receive karo (0.0 – 1.0)."""
        self.amplitude = max(0.0, min(1.0, amp))

    def on_emotion(self, emotion):
        """Gemini emotion tag ke hisaab se react karo."""
        emotion = emotion.lower().strip()
        if emotion == "thinking":
            self.set_state(STATE_THINKING)
        elif emotion in ("happy", "surprised", "concerned", "default"):
            # Future: brightness ya scale effect laga sakte ho
            pass

    # ════════════════════════════════════════════════════════════
    # VIDEO HELPERS
    # ════════════════════════════════════════════════════════════

    def _play_video(self, path, loop=True):
        """Video load karke play karo."""
        if not self._video_available:
            self._show_sprite(self._px_idle)
            return
        try:
            self._loop_video = loop
            self._stack.setCurrentIndex(0)   # video widget show karo
            url = QUrl.fromLocalFile(os.path.abspath(path))
            self._player.setMedia(QMediaContent(url))
            self._player.play()
        except Exception as e:
            print(f"[Sia] Video play error: {e}")
            self._show_sprite(self._px_idle)

    def _on_media_status(self, status):
        """Video end hone par loop karo ya idle pe wapas jaao."""
        if status == QMediaPlayer.EndOfMedia:
            if self.current_state == STATE_GREETING:
                if not self._greeting_done:
                    self._greeting_done = True
                    self.set_state(STATE_IDLE)
            elif self._loop_video:
                # Seamless loop — glitch free
                self._player.setPosition(0)
                self._player.play()

    # ════════════════════════════════════════════════════════════
    # SPRITE HELPERS
    # ════════════════════════════════════════════════════════════

    def _show_sprite(self, pixmap=None):
        """Sprite label show karo."""
        self._stack.setCurrentIndex(1)
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                self._sprite_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self._sprite_label.setPixmap(scaled)

    def _update_lipsync(self):
        """Amplitude ke hisaab se mouth frame switch karo."""
        if self.current_state != STATE_TALKING:
            return
        try:
            if self.amplitude >= 0.3 and self._px_semi:
                self._show_sprite(self._px_semi)
            else:
                self._show_sprite(self._px_idle)
        except Exception as e:
            print(f"[Sia] Lipsync error: {e}")

    def _do_blink(self):
        """Random blink — sirf sprite mode mein useful."""
        if self.current_state == STATE_TALKING:
            self._blink_timer.setInterval(random.randint(3000, 5000))
            return
        try:
            self._is_blinking = True
            QTimer.singleShot(150, self._end_blink)
        except Exception:
            pass
        self._blink_timer.setInterval(random.randint(3000, 5000))

    def _end_blink(self):
        self._is_blinking = False

    # ════════════════════════════════════════════════════════════
    # BREATHING ANIMATION
    # ════════════════════════════════════════════════════════════

    def _update_position(self):
        """Sine wave se subtle breathing motion — video ke upar overlay."""
        try:
            t = time.time()
            y_offset = int(math.sin(t * 0.8) * 3)   # 3px up-down
            x_offset = int(math.sin(t * 0.3) * 1)   # 1px left-right
            self.move(self.base_x + x_offset, self.base_y + y_offset)
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════
    # POSITIONING
    # ════════════════════════════════════════════════════════════

    def set_base_position(self, x, y):
        """Base position set karo — breathing iske around hogi."""
        self.base_x = x
        self.base_y = y
        self.move(x, y)

HAS_QT_MULTIMEDIA = True

class LipSyncManager:
    """Bridge Edge-TTS waveform amplitude to VideoCharacterWidget."""

    def __init__(self, character_widget: VideoCharacterWidget) -> None:
        self.character = character_widget
        self._history: list[float] = []

    def on_audio_amplitude(self, value: float) -> None:
        amp = max(0.0, min(1.0, float(value)))
        self._history.append(amp)
        self._history = self._history[-8:]
        smooth = sum(self._history) / len(self._history)
        self.character.on_amplitude(smooth)

    def feed_from_envelope(self, envelope: list[float], step_ms: int = 33) -> None:
        idx = 0
        def tick() -> None:
            nonlocal idx
            if idx >= len(envelope):
                self.character.on_amplitude(0.0)
                return
            self.on_audio_amplitude(envelope[idx])
            idx += 1
            QTimer.singleShot(step_ms, tick)
        tick()

import re
from typing import Tuple

class EmotionDetector:
    """Parses emotion tags and maps user/assistant text to visual state."""

    TAG_RE = re.compile(r"\[EMOTION:(happy|thinking|surprised|concerned|default)\]", re.IGNORECASE)
    LEGACY_RE = re.compile(r"^\s*\[(IDLE|SMILE|HAPPY|SAD|CONFUSED|SURPRISED|THINKING)\]", re.IGNORECASE)
    LEGACY_MAP = {
        "idle": "default",
        "smile": "happy",
        "happy": "happy",
        "sad": "concerned",
        "confused": "thinking",
        "surprised": "surprised",
        "thinking": "thinking",
    }

    @classmethod
    def extract_tag(cls, text: str) -> Tuple[str, str]:
        msg = text or ""
        m = cls.TAG_RE.search(msg)
        if m:
            emotion = m.group(1).lower()
            cleaned = cls.TAG_RE.sub("", msg, count=1).strip()
            return emotion, cleaned

        m2 = cls.LEGACY_RE.search(msg)
        if m2:
            legacy = m2.group(1).lower()
            emotion = cls.LEGACY_MAP.get(legacy, "default")
            cleaned = cls.LEGACY_RE.sub("", msg, count=1).strip()
            return emotion, cleaned

        return "default", msg.strip()

    @staticmethod
    def infer_from_user_text(user_text: str) -> str:
        t = (user_text or "").lower()
        if any(k in t for k in ["thank", "shukriya", "awesome", "great", "love you"]):
            return "happy"
        if any(k in t for k in ["what", "really", "seriously", "unexpected", "kya?!"]):
            return "surprised"
        if any(k in t for k in ["sad", "dukhi", "depressed", "tension", "anxious", "hurt"]):
            return "concerned"
        return "default"
