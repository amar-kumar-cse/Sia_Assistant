"""Avatar frame rendering widget with alpha blending and breathing scale."""

from __future__ import annotations

from typing import Dict

from PyQt5.QtCore import Qt, pyqtProperty
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QLabel


class AvatarFrameWidget(QLabel):
    """QLabel-based avatar renderer using transparent pixmap compositing."""

    def __init__(self, frame_map: Dict[str, QPixmap], parent=None) -> None:
        super().__init__(parent)
        self.frame_map = frame_map
        self.current_from = "idle"
        self.current_to = "idle"
        self.current_alpha = 255
        self._breath_scale = 1.0
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    @pyqtProperty(float)
    def breath_scale(self) -> float:
        return self._breath_scale

    @breath_scale.setter
    def breath_scale(self, val: float) -> None:
        self._breath_scale = val
        self.render_current_frame()

    def set_blend(self, frame_from: str, frame_to: str, alpha: int) -> None:
        self.current_from = frame_from
        self.current_to = frame_to
        self.current_alpha = max(0, min(255, int(alpha)))
        self.render_current_frame()

    def render_current_frame(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        canvas = QPixmap(self.width(), self.height())
        canvas.fill(Qt.transparent)

        px_from = self.frame_map.get(self.current_from) or self.frame_map.get("idle")
        px_to = self.frame_map.get(self.current_to) or self.frame_map.get("idle")
        if px_from is None or px_to is None:
            return

        p = QPainter(canvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        p.translate(w / 2.0, h / 2.0)
        p.scale(self._breath_scale, self._breath_scale)
        p.translate(-w / 2.0, -h / 2.0)

        p.setOpacity((255 - self.current_alpha) / 255.0)
        p.drawPixmap(0, 0, px_from.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        p.setOpacity(self.current_alpha / 255.0)
        p.drawPixmap(0, 0, px_to.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        p.end()

        self.setPixmap(canvas)
