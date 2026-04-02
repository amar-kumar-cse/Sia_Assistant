"""
Sia Weather Widget - Floating Desktop Weather Pop-up
Glassmorphism-style transparent widget with live weather data.
"""

import math
import time
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QThread, pyqtSignal
)
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QLinearGradient,
    QPainterPath, QPen, QBrush, QRadialGradient
)


class WeatherFetchThread(QThread):
    """Background thread to fetch weather data."""
    data_ready = pyqtSignal(dict)

    def __init__(self, city, parent=None):
        super().__init__(parent)
        self.city = city

    def run(self):
        """Fetch weather data from wttr.in (no API key needed)."""
        data = {
            "city": self.city,
            "temp": "--",
            "condition": "Loading...",
            "humidity": "--",
            "wind": "--",
            "icon": "🌤️",
            "feels_like": "--",
        }
        try:
            import requests
            # wttr.in provides free weather data in JSON
            url = f"https://wttr.in/{self.city}?format=j1"
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Sia-Assistant"})
            if resp.status_code == 200:
                j = resp.json()
                current = j.get("current_condition", [{}])[0]
                data["temp"] = current.get("temp_C", "--")
                data["feels_like"] = current.get("FeelsLikeC", "--")
                data["humidity"] = current.get("humidity", "--")
                data["wind"] = current.get("windspeedKmph", "--")
                desc = current.get("weatherDesc", [{}])
                data["condition"] = desc[0].get("value", "Unknown") if desc else "Unknown"

                # Map condition to emoji icon
                cond_lower = data["condition"].lower()
                if "sun" in cond_lower or "clear" in cond_lower:
                    data["icon"] = "☀️"
                elif "cloud" in cond_lower or "overcast" in cond_lower:
                    data["icon"] = "☁️"
                elif "rain" in cond_lower or "drizzle" in cond_lower:
                    data["icon"] = "🌧️"
                elif "thunder" in cond_lower or "storm" in cond_lower:
                    data["icon"] = "⛈️"
                elif "snow" in cond_lower:
                    data["icon"] = "❄️"
                elif "fog" in cond_lower or "mist" in cond_lower or "haze" in cond_lower:
                    data["icon"] = "🌫️"
                elif "partly" in cond_lower:
                    data["icon"] = "⛅"
                else:
                    data["icon"] = "🌤️"
        except Exception as e:
            data["condition"] = f"Error: {str(e)[:40]}"
            data["icon"] = "❓"

        self.data_ready.emit(data)


class WeatherWidget(QWidget):
    """
    Floating glassmorphism weather widget for desktop.
    Semi-transparent, always-on-top, auto-closes after 15 seconds.
    """

    def __init__(self, city="Roorkee", parent=None):
        super().__init__(parent)
        self.city = city
        self.tick = 0.0

        # Window flags: frameless, on-top, transparent
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 240)

        # State
        self.weather_data = None

        # Build UI
        self._build_ui()

        # Position: top-right corner of screen
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 30, 60)

        # Fetch weather data
        self.fetch_thread = WeatherFetchThread(city)
        self.fetch_thread.data_ready.connect(self._on_data_ready)
        self.fetch_thread.start()

        # Animation timer for subtle glow pulse
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._anim_tick)
        self.anim_timer.start(50)

        # Auto-close after 15 seconds
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self._fade_close)
        self.close_timer.start(15000)

    def _build_ui(self):
        """Create the internal labels (painted over in paintEvent)."""
        # We'll draw everything in paintEvent for full control
        pass

    def _on_data_ready(self, data):
        """Weather data received from background thread."""
        self.weather_data = data
        self.update()

    def _anim_tick(self):
        """Subtle animation for glow effect."""
        self.tick += 0.1
        self.update()

    def _fade_close(self):
        """Smoothly fade out and close."""
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(self.close)
        self.anim.start()

    def paintEvent(self, event):
        """Custom glassmorphism painting."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # ── Glass background ──
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 20, 20)

        # Gradient background (dark blue-purple glass)
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor(20, 20, 60, 210))
        bg.setColorAt(0.5, QColor(30, 25, 70, 200))
        bg.setColorAt(1.0, QColor(15, 15, 45, 220))
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1.5))
        painter.drawPath(path)

        # Pulsing inner glow
        glow_alpha = int(20 + 10 * math.sin(self.tick * 2))
        inner = QRadialGradient(w * 0.3, h * 0.3, w * 0.6)
        inner.setColorAt(0.0, QColor(100, 150, 255, glow_alpha))
        inner.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(inner))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        if not self.weather_data:
            # Loading state
            font = QFont("Segoe UI", 16, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255, 200))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, f"⏳ Loading weather for {self.city}...")
            painter.end()
            return

        d = self.weather_data

        # ── Header: City + Close btn ──
        header_font = QFont("Segoe UI", 13, QFont.Bold)
        painter.setFont(header_font)
        painter.setPen(QColor(0, 255, 204, 230))
        painter.drawText(20, 25, f"📍 {d['city']}")

        # Close X
        painter.setPen(QColor(255, 100, 100, 180))
        close_font = QFont("Segoe UI", 14, QFont.Bold)
        painter.setFont(close_font)
        painter.drawText(w - 35, 25, "✕")

        # ── Big icon + temperature ──
        icon_font = QFont("Segoe UI Emoji", 42)
        painter.setFont(icon_font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 95, d["icon"])

        temp_font = QFont("Segoe UI", 36, QFont.Bold)
        painter.setFont(temp_font)
        painter.setPen(QColor(255, 255, 255, 250))
        painter.drawText(90, 95, f"{d['temp']}°C")

        # ── Condition ──
        cond_font = QFont("Segoe UI", 12)
        painter.setFont(cond_font)
        painter.setPen(QColor(200, 200, 255, 200))
        painter.drawText(90, 115, d["condition"])

        # ── Details row ──
        detail_font = QFont("Segoe UI", 11)
        painter.setFont(detail_font)
        painter.setPen(QColor(180, 200, 255, 200))

        y_detail = 155
        # Feels like
        painter.drawText(20, y_detail, f"🌡️ Feels: {d['feels_like']}°C")
        # Humidity
        painter.drawText(175, y_detail, f"💧 Humidity: {d['humidity']}%")

        y_detail += 28
        # Wind
        painter.drawText(20, y_detail, f"💨 Wind: {d['wind']} km/h")

        # ── Sia branding ──
        brand_font = QFont("Segoe UI", 9)
        painter.setFont(brand_font)
        painter.setPen(QColor(0, 255, 204, 120))
        painter.drawText(20, h - 15, "Sia Weather Widget ❤️")

        # ── Auto-close countdown ──
        remaining = max(0, 15 - int(self.tick / 2))
        painter.drawText(w - 80, h - 15, f"⏱️ {remaining}s")

        painter.end()

    def mousePressEvent(self, event):
        """Close on click anywhere, or support dragging."""
        # Check if click is on close button area
        if event.x() > self.width() - 45 and event.y() < 35:
            self.close()
        else:
            # Enable dragging
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """Drag the widget."""
        if hasattr(self, '_drag_pos'):
            self.move(event.globalPos() - self._drag_pos)
