"""
Sia AI — Glassmorphism Chat Bubble (PyQt6 FINAL)
=================================================
- Manually painted glass panel (no Qt stylesheets)
- 5 states: normal / listening / thinking / error / hidden
- Animated typing dots (thinking state)
- Fade-in on show
"""

from PyQt6.QtWidgets  import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore     import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui      import QPainter, QColor, QPen, QFont


class SiaChatBubble(QWidget):

    _STATE_COLORS = {
        "normal":    ("#FFFFFF", "Sia 💙"),
        "listening": ("#60A5FA", "Sia 🎙️"),
        "thinking":  ("#FCD34D", "Sia 🤔"),
        "error":     ("#F87171", "Sia ❤️"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(320)
        self.setMinimumHeight(80)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── layout ────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self._header = QLabel("Sia 💙", self)
        self._header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._header.setStyleSheet("color: white; background: transparent;")

        self._body = QLabel("", self)
        self._body.setFont(QFont("Segoe UI", 11))
        self._body.setStyleSheet("color: rgba(255,255,255,0.88); background: transparent;")
        self._body.setWordWrap(True)

        layout.addWidget(self._header)
        layout.addWidget(self._body)

        # ── typing dots (thinking) ────────────────────────────────
        self._dots_idx   = 0
        self._dots_timer = QTimer(self)
        self._dots_timer.setInterval(400)
        self._dots_timer.timeout.connect(self._tick_dots)

        # ── auto-hide ─────────────────────────────────────────────
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        # ── opacity anim ──────────────────────────────────────────
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

    # ── Public API ───────────────────────────────────────────────────

    def show_message(self, text: str, state: str = "normal"):
        self._dots_timer.stop()
        self._hide_timer.stop()

        color, label = self._STATE_COLORS.get(state, ("#FFFFFF", "Sia 💙"))
        self._header.setText(label)
        self._header.setStyleSheet(
            f"color: {color}; background: transparent; font-weight: bold;")

        if state == "thinking":
            self._body.setText(text or "Soch rahi hoon...")
            self._dots_idx = 0
            self._dots_timer.start()
        else:
            self._body.setText(text)
            if state in ("normal", "error"):
                self._hide_timer.start(7000)

        self.adjustSize()
        self._fade_in()

    # ── Internal ─────────────────────────────────────────────────────

    def _tick_dots(self):
        dots = ["•", "••", "•••"]
        self._body.setText(dots[self._dots_idx % 3])
        self._dots_idx += 1

    def _fade_in(self, ms: int = 250):
        self.show()
        anim = QPropertyAnimation(self._effect, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(float(self._effect.opacity()))
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim_in = anim  # keep reference

    def _fade_out(self, ms: int = 200):
        anim = QPropertyAnimation(self._effect, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim_out = anim

    # ── Glassmorphism paint ──────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        p.setBrush(QColor(8, 8, 20, 190))
        # Subtle border
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 22, 22)
