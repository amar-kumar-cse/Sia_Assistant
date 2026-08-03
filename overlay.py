"""
Sia AI — Main Overlay Window (PyQt6 FINAL)
==========================================
- Full-screen transparent PyQt6 QMainWindow
- Win32 WS_EX_TRANSPARENT for click-through (icons still clickable)
- Hosts SiaCharacterWidget + SiaChatBubble
- System Tray with Toggle / Mute / Quit
"""

import sys
import win32gui
import win32con

from PyQt6.QtWidgets  import (QMainWindow, QApplication, QSystemTrayIcon,
                               QMenu, QWidget)
from PyQt6.QtCore     import Qt, QTimer
from PyQt6.QtGui      import QPainter, QColor, QIcon, QAction

from character_widget import SiaCharacterWidget
from chat_bubble      import SiaChatBubble


class SiaOverlay(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ── 1. Transparent full-screen window ─────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        screen = QApplication.primaryScreen().size()
        self.sw, self.sh = screen.width(), screen.height()
        self.setGeometry(0, 0, self.sw, self.sh)

        # ── 2. Position constants ──────────────────────────────────
        self.CHAR_X   = self.sw - 380
        self.CHAR_Y   = self.sh - 560
        self.BUBBLE_X = self.CHAR_X - 340
        self.BUBBLE_Y = self.CHAR_Y + 200

        # ── 3. Character widget ────────────────────────────────────
        self.character = SiaCharacterWidget()   # top-level (not child)
        self.character.base_x = self.CHAR_X
        self.character.base_y = self.CHAR_Y
        # ── 5. Vision Observation Active Badge State ─────────────────────────────
        self._vision_active = False
        self._vision_pulse = 0

        # ── 6. System tray ─────────────────────────────────────────
        self._setup_tray()

        # ── 7. Apply click-through after show ─────────────────────
        QTimer.singleShot(200, self._apply_click_through)

    def set_vision_indicator(self, active: bool):
        """Toggle active visual indicator for screen recording/observation."""
        self._vision_active = active
        self.update()

    def set_target_screen(self, screen_index: int = 0):
        """Multi-monitor support: reposition Sia overlay to designated screen index."""
        screens = QApplication.screens()
        if 0 <= screen_index < len(screens):
            geo = screens[screen_index].geometry()
            self.sw, self.sh = geo.width(), geo.height()
            self.setGeometry(geo.left(), geo.top(), self.sw, self.sh)
            self.CHAR_X = geo.left() + self.sw - 380
            self.CHAR_Y = geo.top() + self.sh - 560
            self.BUBBLE_X = self.CHAR_X - 340
            self.BUBBLE_Y = self.CHAR_Y + 200
            self.character.base_x = self.CHAR_X
            self.character.base_y = self.CHAR_Y
            self.character.move(self.CHAR_X, self.CHAR_Y)
            self.bubble.move(self.BUBBLE_X, self.BUBBLE_Y)

    # ── Win32 click-through ──────────────────────────────────────────

    def _apply_click_through(self):
        """Overlay itself is click-through; character widget is NOT (separate window)."""
        self.show()
        hwnd = int(self.winId())
        ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        ex |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
        print("[Overlay] Click-through applied — desktop icons remain clickable")

    # ── System Tray ──────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = QIcon("assets/sia_idle.png")
        if not icon.isNull():
            self.tray.setIcon(icon)

        menu = QMenu()

        act_toggle = QAction("Toggle Sia", self)
        act_toggle.triggered.connect(self._toggle_character)
        menu.addAction(act_toggle)

        act_mute = QAction("Mute", self)
        act_mute.triggered.connect(self._toggle_mute)
        menu.addAction(act_mute)

        menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _toggle_character(self):
        if self.character.isVisible():
            self.character.hide()
        else:
            self.character.show()
            self.character.fade_in(400)

    def _toggle_mute(self):
        # Future: Connect to SiaVoice mute toggle
        pass

    # ── Paint — keep fully transparent ──────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if getattr(self, '_vision_active', False):
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            # Red glowing indicator dot at top right of Sia's area
            p.setBrush(QColor(255, 50, 50, 220))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(self.CHAR_X + 320, self.CHAR_Y + 10, 14, 14)


    # ── Show both windows ────────────────────────────────────────────

    def show(self):
        super().show()
        self.character.show()
