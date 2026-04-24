"""
engine/wake_word.py — Continuous Background Wake Word Detection
Bugs fixed:
  - BUG #28: stop() → quit() + wait() taaki thread properly terminate ho
  - BUG #29: adjust_for_ambient_noise 1s → 0.3s (startup delay kam karo)
"""

import os
import speech_recognition as sr
from PyQt5.QtCore import QThread, pyqtSignal


class WakeWordDetector(QThread):
    detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True

        # .env se wake words load karo
        words_env = os.environ.get("WAKE_WORDS", "hey sia,sia,hello sia,helo sia")
        self.triggers = [w.strip().lower() for w in words_env.split(",") if w.strip()]

    def run(self):
        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            # BUG #29 FIX: 0.3s kaafi hai — 1s startup delay tha pehle
            r.adjust_for_ambient_noise(source, duration=0.3)

            while self.running:
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=3)
                    text = r.recognize_google(audio, language="hi-IN").lower()

                    if any(trigger in text for trigger in self.triggers):
                        self.detected.emit()

                except sr.WaitTimeoutError:
                    # Normal — timeout ke baad loop continue karo
                    continue
                except sr.UnknownValueError:
                    # Samjha nahi — ignore
                    continue
                except Exception as exc:
                    # Network error etc — log karo par crash mat karo
                    print(f"[WakeWord] Error: {exc}")
                    continue

    def stop(self):
        # BUG #28 FIX: running flag + proper thread termination
        self.running = False
        self.quit()
        self.wait(2000)  # Max 2 sec wait karo
