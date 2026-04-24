"""
Sia AI — Video-Driven Character Widget (PyQt6 300ms Cross-Fade)
================================================================
- 100% transparent, frameless, and click-through window
- QMediaPlayer playing WebM videos with native alpha transparency
- Dual-player technique with 300ms cross-fade (opacity transition)
- Hardware accelerated Qt6 Multimedia
"""

import os
import ctypes

import win32gui
import win32api
import win32con

from PyQt6.QtWidgets  import (QWidget, QStackedWidget,
                               QVBoxLayout, QGraphicsOpacityEffect)
from PyQt6.QtMultimedia import (QMediaPlayer, QAudioOutput)
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore     import (Qt, QUrl, QPropertyAnimation,
                               QEasingCurve, pyqtSignal, QTimer)


# ── Asset paths ──────────────────────────────────────────────────
VIDEO_IDLE    = "assets/idle.webm"
VIDEO_TALKING = "assets/talking.webm"
VIDEO_THINK   = "assets/thinking.webm"

W, H = 350, 500          # Widget pixel size


class _VideoLayer(QWidget):
    """One QVideoWidget + one QMediaPlayer combo with opacity effect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(W, H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._vw = QVideoWidget(self)
        self._vw.setFixedSize(W, H)
        self._vw.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._vw.setStyleSheet("background: transparent;")
        layout.addWidget(self._vw)

        self._player = QMediaPlayer(self)
        self._audio  = QAudioOutput(self)
        self._audio.setVolume(0.0)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._vw)

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)

    def load(self, path: str):
        self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))

    def play(self):
        self._player.play()

    def stop(self):
        self._player.stop()

    def connect_end(self, slot):
        self._player.mediaStatusChanged.connect(
            lambda s: slot() if s == QMediaPlayer.MediaStatus.EndOfMedia else None
        )

    def set_opacity(self, value: float):
        self._effect.setOpacity(value)

    @property
    def opacity_effect(self):
        return self._effect

    @property
    def player(self) -> QMediaPlayer:
        return self._player


class SiaCharacterWidget(QWidget):
    """
    Video-driven Sia character with 300ms cross-fades.
    """

    state_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Window setup (Frameless, Transparent, Tool) ──────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(W, H)
        self.setStyleSheet("background: transparent;")

        # ── Positions (Pinned to bottom-right) ───────────────────
        screen = self.screen().size()
        self.base_x = screen.width() - W - 40
        self.base_y = screen.height() - H - 60
        self.move(self.base_x, self.base_y)

        self.state = "idle"
        self._next_video: str | None = None

        # ── Build dual-layer video UI ────────────────────────────
        self._layer_a = _VideoLayer(self)
        self._layer_b = _VideoLayer(self)
        
        # We don't use QStackedWidget so we can show both layers simultaneously during crossfade
        self._layer_a.setGeometry(0, 0, W, H)
        self._layer_b.setGeometry(0, 0, W, H)
        
        self._layer_a.show()
        self._layer_b.hide()
        
        self._active_layer = 0   # 0 = a, 1 = b
        self._crossfade_anim = None

        QTimer.singleShot(150, self._init_video)
        print("[Sia Video Engine] Initialized")

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_click_through()

    def _apply_click_through(self):
        try:
            hwnd = int(self.winId())
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
            print("[Sia Video Engine] Click-through activated.")
        except Exception as e:
            print(f"[Sia Video Engine] Win32 error: {e}")

    def _init_video(self):
        if not os.path.exists(VIDEO_IDLE):
            print(f"[Sia Video Engine] ERROR: {VIDEO_IDLE} not found.")
            return

        self._layer_a.connect_end(self._on_layer_a_end)
        self._layer_b.connect_end(self._on_layer_b_end)

        self._layer_a.load(VIDEO_IDLE)
        self._layer_a.play()

    def _on_layer_a_end(self):
        if self._active_layer == 0:
            if self._next_video:
                self._crossfade_to(self._layer_b, self._next_video)
                self._next_video = None
            else:
                self._layer_a.player.setPosition(0)
                self._layer_a.play()

    def _on_layer_b_end(self):
        if self._active_layer == 1:
            if self._next_video:
                self._crossfade_to(self._layer_a, self._next_video)
                self._next_video = None
            else:
                self._layer_b.player.setPosition(0)
                self._layer_b.play()

    def _crossfade_to(self, target_layer: _VideoLayer, path: str):
        """Perform a 300ms cross-fade to the target layer."""
        if not os.path.exists(path):
            return

        current_layer = self._layer_a if target_layer is self._layer_b else self._layer_b
        
        target_layer.load(path)
        target_layer.set_opacity(0.0)
        target_layer.show()
        target_layer.play()

        # Fade in new layer
        self._anim_in = QPropertyAnimation(target_layer.opacity_effect, b"opacity")
        self._anim_in.setDuration(300)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Fade out old layer
        self._anim_out = QPropertyAnimation(current_layer.opacity_effect, b"opacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Stop old layer after fade
        self._anim_out.finished.connect(current_layer.stop)
        self._anim_out.finished.connect(current_layer.hide)

        self._anim_in.start()
        self._anim_out.start()

        self._active_layer = 1 if target_layer is self._layer_b else 0

    def _request_video_switch(self, path: str):
        """Immediately switch to new video using 300ms cross-fade."""
        if self._active_layer == 0:
            self._crossfade_to(self._layer_b, path)
        else:
            self._crossfade_to(self._layer_a, path)

    def set_state(self, state: str):
        if state == self.state and state not in ("talking",):
            return
            
        self.state = state
        self.state_changed.emit(state)

        if state in ("idle", "listening", "greeting"):
            self._request_video_switch(VIDEO_IDLE)
        elif state == "thinking":
            self._request_video_switch(VIDEO_THINK)
        elif state == "talking":
            self._request_video_switch(VIDEO_TALKING)

    def fade_in(self, duration: int = 800):
        # Master fade in on startup
        self._master_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._master_effect)
        self._fade_anim = QPropertyAnimation(self._master_effect, b"opacity")
        self._fade_anim.setDuration(duration)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def on_amplitude(self, amp: float):
        # Audio lipsync no longer needed, video handles it
        pass

    def on_emotion(self, emotion: str):
        pass
