"""
Sia AI - Proactive Engine (FINAL VERSION)
Periodically analyzes the screen and makes smart comments.
"""

import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class ProactiveEngine(QObject):
    
    comment_ready = pyqtSignal(str, str)  # text, emotion
    
    def __init__(self, brain, memory):
        super().__init__()
        self.brain = brain
        self.memory = memory
        self.last_hash = None
        self.session_comments = 0
        self.MAX_COMMENTS = 3  # per session
        
        # Check har 3 minute mein (180000 ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_screen)
        self.timer.start(180000)
        print("[Proactive] Engine initialized, watching screen every 3 mins.")
    
    def check_screen(self):
        if self.session_comments >= self.MAX_COMMENTS:
            return
        
        try:
            # Screen capture
            image = self._capture()
            if not image:
                return
                
            # Hash check — sirf naya content
            h = hash(image.tobytes())
            if h == self.last_hash:
                return
            self.last_hash = h
            
            # Gemini se analyze
            prompt = """
            Screen par kya ho raha hai?
            Agar kuch interesting/helpful/funny ho to ek short Hinglish comment do.
            User ko 'Hero' kaho.
            1 line max. Agar normal/boring ho to sirf 'SKIP' likho.
            """
            
            # Run in a background thread ideally, but keeping it simple here
            # In a real app you'd use run_in_executor to not block GUI
            response = self.brain.analyze_screen(image, prompt)
            
            if response and 'SKIP' not in response.upper():
                self.session_comments += 1
                self.comment_ready.emit(response, 'default')
                print(f"[Proactive] Comment generated: {response}")
        
        except Exception as e:
            print(f"[Proactive] Error: {e}")
    
    def _capture(self):
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                # Capture the primary monitor
                shot = sct.grab(sct.monitors[1])
                return Image.frombytes(
                    'RGB',
                    (shot.width, shot.height),
                    shot.rgb
                )
        except Exception as e:
            print(f"[Proactive] Screen capture failed: {e}")
            return None
