"""
Sia AI — Main Application Entry Point (PyQt6 FINAL)
====================================================
- PyQt6 + qasync event loop
- All engines wired together
- Graceful fallbacks for missing engine modules
- Permission Gate confirmation loop wired
- VoiceInterruptMonitor (barge-in) wired
- Continuous session (no repeat wake-word) wired
"""

import os
import sys
import traceback
import logging
import asyncio
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import QObject

import qasync

logger = logging.getLogger("sia.crash_guard")
_sia_app_instance = None

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Poore app ka last-line-of-defense.
    Koi bhi unhandled crash yahan pakda jaayega — app band NAHI hogi.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"UNHANDLED EXCEPTION:\n{error_details}")
    print(f"[CrashGuard] Caught unhandled exception: {exc_value}")

    # Show notification & reset state safely without crashing
    try:
        if _sia_app_instance and hasattr(_sia_app_instance, 'bubble'):
            _sia_app_instance.bubble.show_message("Sia ko thoda issue hua, main theek ho rahi hoon 🙂", "normal")
        if _sia_app_instance and hasattr(_sia_app_instance, 'character'):
            _sia_app_instance.character.set_state("idle")
    except Exception as recovery_err:
        print(f"[CrashGuard] Recovery notice error: {recovery_err}")

sys.excepthook = global_exception_handler

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
        global _sia_app_instance
        _sia_app_instance = self

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
        self._start_listening()

    def _start_listening(self):
        """Start a speech recognizer cycle."""
        self.recognizer = SpeechRecognizer()
        self.recognizer.result.connect(
            lambda text: asyncio.ensure_future(self.on_speech(text)))
        self.recognizer.error.connect(self.on_speech_error)
        self.recognizer.start()

    # ── Speech → intent / Gemini ──────────────────────────────────

    async def on_speech(self, text: str):
        print(f"[User] {text}")

        # ── [STEP 1 FIX] Confirmation Gate Interceptor ───────────
        # If a destructive action is pending confirmation, intercept FIRST
        # before any other intent / Gemini processing.
        try:
            from engine.actions import _pending_confirmation, _consume_confirmation
            if _pending_confirmation.get("action") is not None:
                text_lower = text.lower().strip()
                # Confirm triggers (Hinglish + English)
                if any(kw in text_lower for kw in [
                    "confirm", "haan", "ha", "yes", "kar do", "karo", "ok", "okay",
                    "proceed", "theek hai", "bilkul"
                ]):
                    result = _consume_confirmation(True)
                    if result:
                        await self._respond(f"✅ {result}", "happy")
                    else:
                        await self._respond("✅ Action execute ho gayi Hero!", "happy")
                    self._maybe_continue_session()
                    return
                # Cancel triggers (Hinglish + English)
                elif any(kw in text_lower for kw in [
                    "cancel", "nahi", "na", "no", "ruk", "ruko", "mat karo", "band karo", "stop"
                ]):
                    result = _consume_confirmation(False)
                    await self._respond(result or "✅ Action cancel kar diya Hero.", "happy")
                    self._maybe_continue_session()
                    return
        except Exception as gate_err:
            print(f"[ConfirmInterceptor] Warning: {gate_err}")

        # ── Normal intent / Gemini flow ──────────────────────────
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

        # ── [STEP 4 FIX] Mark active session for follow-up window ─
        self._maybe_continue_session()

    def _maybe_continue_session(self):
        """After Sia responds, mark active session so user doesn't need wake word for 5s."""
        try:
            from engine.listen_engine import set_active_session, is_in_continuous_session
            set_active_session()
            # Schedule a follow-up listen cycle after response finishes
            asyncio.ensure_future(self._follow_up_listen())
        except Exception:
            pass

    async def _follow_up_listen(self):
        """After Sia speaks, wait briefly then auto-listen within continuous session window."""
        try:
            from engine.listen_engine import is_in_continuous_session
            # Wait for Sia to finish speaking
            await asyncio.sleep(0.3)
            if is_in_continuous_session():
                print("[ContinuousSession] Auto-listening for follow-up (no wake word needed)...")
                self._start_listening()
        except Exception as e:
            print(f"[ContinuousSession] Warning: {e}")

    # ── Respond (TTS + animation) ─────────────────────────────────

    async def _respond(self, text: str, emotion: str = "default"):
        print(f"[Sia] [{emotion}] {text}")
        self.character.on_emotion(emotion)
        self.character.set_state("talking")
        self.bubble.show_message(text, "normal")

        # ── [STEP 4 FIX] Start barge-in monitor while speaking ────
        interrupt_monitor = None
        try:
            from engine.listen_engine import VoiceInterruptMonitor
            interrupt_monitor = VoiceInterruptMonitor(
                interrupt_callback=self.voice.stop,
                is_speaking_fn=getattr(self.voice, 'get_speaking_state', lambda: True),
            )
            interrupt_monitor.start()
        except Exception:
            pass  # Graceful fallback if pyaudio not available

        await self._wait_speak(text)

        if interrupt_monitor:
            try:
                interrupt_monitor.stop()
            except Exception:
                pass

        self.character.set_state("idle")

    # ── Error handler ─────────────────────────────────────────────

    def on_speech_error(self):
        self.bubble.show_message("Sunai nahi diya Hero, dobara bolna 🎙️", "error")
        self.character.set_state("idle")


# ── App-wide crash safety net ─────────────────────────────────────
try:
    from utils.reliability import global_exception_handler, asyncio_exception_handler, register_crash_guard_callbacks
    sys.excepthook = global_exception_handler
except ImportError:
    pass


# ════════════════════════════════════════════════════════════════
def main():
    # High-DPI support
    app = QApplication(sys.argv)
    app.setApplicationName("Sia AI Assistant")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    sia = SiaApp()

    # Wire UI notification & avatar reset callbacks to reliability crash guard
    def _ui_notify(msg: str):
        if hasattr(sia, 'bubble') and sia.bubble:
            sia.bubble.show_message(msg, "normal")

    def _avatar_reset():
        if hasattr(sia, 'character') and sia.character:
            sia.character.set_state("idle")

    try:
        register_crash_guard_callbacks(ui_notify_fn=_ui_notify, avatar_reset_fn=_avatar_reset)
        loop.set_exception_handler(asyncio_exception_handler)
    except Exception:
        def handle_async_exception(loop, context):
            msg = context.get("exception", context.get("message"))
            print(f"⚠️ [SIA ASYNC GUARD] Unhandled async task exception caught: {msg}")
            _ui_notify("Sia task recovered from error.")
            _avatar_reset()
        loop.set_exception_handler(handle_async_exception)

    with loop:
        loop.run_until_complete(sia.boot())
        loop.run_forever()


if __name__ == "__main__":
    main()

