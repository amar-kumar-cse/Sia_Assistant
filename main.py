"""
Sia AI — Main Application Entry Point (PyQt6 FINAL)
====================================================
- PyQt6 + qasync event loop
- All engines wired together
- Graceful fallbacks for missing engine modules
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import QObject

import qasync

# ── Engine imports with graceful fallbacks ───────────────────────
from engine.brain import GeminiBrain
from engine.proactive import ProactiveEngine

try:
    from engine.memory import SiaMemory
except ImportError:
    class SiaMemory:
        def get_recent(self, n): return []
        def save(self, u, s, e): pass

try:
    from engine.voice import SiaVoice
except ImportError:
    from PyQt6.QtCore import pyqtSignal
    class SiaVoice(QObject):
        speaking_done = pyqtSignal()
        def __init__(self): super().__init__()
        def speak(self, text, amplitude_callback=None):
            print(f"[VoiceFallback] {text}")
            self.speaking_done.emit()
        def stop(self): pass

try:
    from engine.intent import IntentHandler
except ImportError:
    class IntentHandler:
        def detect(self, text): return {"handled": False}

try:
    from engine.wake_word import WakeWordDetector, SpeechRecognizer
except ImportError:
    from PyQt6.QtCore import pyqtSignal
    class WakeWordDetector(QObject):
        detected = pyqtSignal()
        def __init__(self): super().__init__()
        def start(self): pass
    class SpeechRecognizer(QObject):
        result = pyqtSignal(str)
        error  = pyqtSignal()
        def __init__(self): super().__init__()
        def start(self): pass

# ── Overlay (PyQt6) ──────────────────────────────────────────────
from overlay import SiaOverlay


# ════════════════════════════════════════════════════════════════
class SiaApp(QObject):
    def __init__(self):
        super().__init__()

    # ── Signal wiring ────────────────────────────────────────────

    def _connect_signals(self):
        self.wake_detector.detected.connect(self.on_wake_word)
        self.proactive.comment_ready.connect(
            lambda text, emotion: asyncio.ensure_future(
                self._respond(text, emotion))
        )

    # ── Boot sequence ────────────────────────────────────────────

    async def boot(self):
        print("[Boot] Starting Sia AI...")
        load_dotenv()
        os.makedirs("temp", exist_ok=True)

        # 1. Engines
        self.memory  = SiaMemory()
        self.brain   = GeminiBrain()
        self.voice   = SiaVoice()
        self.intent  = IntentHandler()
        self.proactive = ProactiveEngine(self.brain, self.memory)

        # 2. UI
        self.overlay   = SiaOverlay()
        self.character = self.overlay.character
        self.bubble    = self.overlay.bubble

        # 3. Wake word
        self.wake_detector = WakeWordDetector()
        self._connect_signals()

        # 4. Show + fade in
        self.overlay.show()
        self.character.show()
        self.character.fade_in(800)

        # 5. Boot greeting
        await asyncio.sleep(0.8)
        greeting = "Namaste Hero! 🙏 Main Sia hoon. Batao kya kaam hai?"
        self.bubble.show_message(greeting, "normal")
        self.character.set_state("talking")
        await self._wait_speak(greeting)
        self.character.set_state("idle")

        # 6. Start wake word detection
        self.wake_detector.start()
        print("[Boot] Sia ready — listening for 'Hey Sia'")

    # ── Helpers ──────────────────────────────────────────────────

    async def _wait_speak(self, text: str):
        """Speak text and await completion via asyncio.Event."""
        done = asyncio.Event()

        def _on_done():
            done.set()

        self.voice.speaking_done.connect(_on_done)
        self.voice.speak(text, amplitude_callback=self.character.on_amplitude)
        await done.wait()
        try:
            self.voice.speaking_done.disconnect(_on_done)
        except Exception:
            pass

    # ── Wake word → speech recognition ───────────────────────────

    def on_wake_word(self):
        print("[Sia] Wake word detected!")
        self.character.set_state("listening")
        self.bubble.show_message("Sun rahi hoon Hero...", "listening")

        self.recognizer = SpeechRecognizer()
        self.recognizer.result.connect(
            lambda text: asyncio.ensure_future(self.on_speech(text)))
        self.recognizer.error.connect(self.on_speech_error)
        self.recognizer.start()

    # ── Speech → intent / Gemini ──────────────────────────────────

    async def on_speech(self, text: str):
        print(f"[User] {text}")
        intent = self.intent.detect(text)

        if intent.get("handled"):
            await self._respond(intent["text"], intent.get("emotion", "happy"))
        else:
            self.character.set_state("thinking")
            self.bubble.show_message("Soch rahi hoon...", "thinking")

            history  = self.memory.get_recent(10)
            loop     = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.brain.get_response(text, history))

            self.memory.save(text, response["text"], response["emotion"])
            await self._respond(response["text"], response["emotion"])

    # ── Respond (TTS + animation) ─────────────────────────────────

    async def _respond(self, text: str, emotion: str = "default"):
        print(f"[Sia] [{emotion}] {text}")
        self.character.on_emotion(emotion)
        self.character.set_state("talking")
        self.bubble.show_message(text, "normal")
        await self._wait_speak(text)
        self.character.set_state("idle")

    # ── Error handler ─────────────────────────────────────────────

    def on_speech_error(self):
        self.bubble.show_message("Sunai nahi diya Hero, dobara bolna 🎙️", "error")
        self.character.set_state("idle")


# ════════════════════════════════════════════════════════════════
def main():
    # High-DPI support (PyQt6 handles it automatically, but explicit is safer)
    app = QApplication(sys.argv)
    app.setApplicationName("Sia AI Assistant")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    sia = SiaApp()

    with loop:
        loop.run_until_complete(sia.boot())
        loop.run_forever()


if __name__ == "__main__":
    main()
