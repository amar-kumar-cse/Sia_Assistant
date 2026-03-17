import sys
import os
import threading
from PyQt5 import QtCore, QtGui, QtWidgets

# Backend imports
import brain
import voice_engine
import listen_engine

# Ensure high DPI scaling support
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class SiaAssistant(QtWidgets.QWidget):
    # Signal to update UI from background thread
    update_chat_signal = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()

        # --- Window Settings ---
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | # Border hatane ke liye
            QtCore.Qt.WindowStaysOnTopHint | # Hamesha sab apps ke upar
            QtCore.Qt.SubWindow # Taskbar clutter kam karne ke liye
        )
        
        # Transparency fix
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Window Size aur Position
        self.resize(400, 500)
        
        # Initial position - check screen size
        screen_geometry = QtWidgets.QApplication.primaryScreen().geometry()
        x = screen_geometry.width() - 450
        y = screen_geometry.height() - 600
        # Fallback if detection fails or manual override requested
        if x < 0 or y < 0:
            self.move(1450, 600)
        else:
            self.move(x, y)

        # --- UI Design ---
        self.layout = QtWidgets.QVBoxLayout(self)
        
        # Avatar
        self.avatar_label = QtWidgets.QLabel(self)
        self.movie = None
        
        # Load Animation/Image
        self.load_avatar()
        
        self.layout.addWidget(self.avatar_label, alignment=QtCore.Qt.AlignCenter)

        # Response Box
        self.chat_label = QtWidgets.QLabel("Sia: Hello Amar! Main taiyaar hoon. ❤️")
        self.chat_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 160); /* Deep dark transparent */
                color: #00FFCC; /* Neon cyan */
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                padding: 15px;
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 40);
            }
        """)
        self.chat_label.setWordWrap(True)
        self.layout.addWidget(self.chat_label)
        
        # --- Voice Loop Thread ---
        self.update_chat_signal.connect(self.update_chat_ui)
        self.running = True
        self.voice_thread = threading.Thread(target=self.voice_loop, daemon=True)
        self.voice_thread.start()

    def load_avatar(self):
        """Load avatar image or GIF safely."""
        gif_path = "assets/sia_idle.gif"
        png_path = "assets/sia_idle.png"
        
        if os.path.exists(gif_path):
            self.movie = QtGui.QMovie(gif_path)
            self.movie.setScaledSize(QtCore.QSize(300, 300))
            self.avatar_label.setMovie(self.movie)
            self.movie.start()
        elif os.path.exists("sia_animation.gif"):
            self.movie = QtGui.QMovie("sia_animation.gif")
            self.movie.setScaledSize(QtCore.QSize(300, 300))
            self.avatar_label.setMovie(self.movie)
            self.movie.start()
        elif os.path.exists(png_path):
            pixmap = QtGui.QPixmap(png_path)
            self.avatar_label.setPixmap(pixmap.scaled(300, 300, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            self.avatar_label.setText("No Avatar Found")
            self.avatar_label.setStyleSheet("color: white;")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = QtCore.QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def update_chat_ui(self, sender, message):
        self.chat_label.setText(f"{sender}: {message}")

    def voice_loop(self):
        """Threaded function for listening and speaking."""
        # Initial greeting
        # voice_engine.speak("Namaste Amar! Main taiyaar hoon.") 
        # Commented out initial speak to avoid annoyance on restart, can enable if needed
        self.update_chat_signal.emit("System", "Initialising...")
        
        while self.running:
            try:
                # 1. Wait for Wake Word
                self.update_chat_signal.emit("Sia", "💤 Waiting for 'Sia'...")
                
                # This blocks until "Sia" is heard
                if listen_engine.listen_for_wake_word():
                    # 2. Active Listen
                    self.update_chat_signal.emit("Sia", "👂 Listening...")
                    # Optional: Play a beep here if possible
                    
                    user_text = listen_engine.listen()
                    
                    if user_text:
                        # Show user text
                        self.update_chat_signal.emit("Amar", user_text)
                        
                        # Think
                        response = brain.think(user_text)
                        
                        # Show and Speak Response
                        self.update_chat_signal.emit("Sia", response)
                        voice_engine.speak(response)
                    else:
                        self.update_chat_signal.emit("Sia", "Kuch sunayi nahi diya...")
                        
            except Exception as e:
                print(f"Error in voice loop: {e}")
                self.update_chat_signal.emit("System", f"Error: {str(e)[:20]}")
                # Prevent infinite loop span if major error
                import time
                time.sleep(2)

    def closeEvent(self, event):
        self.running = False
        super().closeEvent(event)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    sia = SiaAssistant()
    sia.show()
    sys.exit(app.exec_())
