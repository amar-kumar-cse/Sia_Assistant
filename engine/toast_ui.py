import sys
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect

class ToastNotification(QWidget):
    """A floating, transparent visual alert that disappears after 5 seconds."""
    
    def __init__(self, message, duration=5000, parent=None):
        super().__init__(parent)
        
        # Frameless, Always on Top, Borderless, Tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.duration = duration
        
        # Styling
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(message)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 35, 230);
                color: #00FFCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: bold;
                padding: 15px 25px;
                border-radius: 12px;
                border: 1px solid rgba(0, 255, 204, 0.4);
            }
        """)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.adjustSize()
        
        # Position at Bottom Right
        screen = QApplication.primaryScreen().geometry()
        self.start_x = screen.width() - self.width() - 40
        self.start_y = screen.height() - self.height() - 80
        
        self.move(self.start_x, self.start_y)
        
        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        # Fade In
        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(500)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        
        # Fade Out Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.start_fade_out)
        
    def show_toast(self):
        self.show()
        self.fade_in_anim.start()
        self.timer.start(self.duration)
        
    def start_fade_out(self):
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(1000)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.finished.connect(self.close)
        self.fade_out_anim.start()

def show_toast(message, duration=5000):
    """Helper function to create and show a toast from anywhere."""
    # Only works if QApplication exists
    if QApplication.instance():
        toast = ToastNotification(message, duration)
        toast.show_toast()
        # Keep reference to prevent GC
        QApplication.instance()._current_toast = toast
    else:
        print("[Toast Fallback]:", message)
