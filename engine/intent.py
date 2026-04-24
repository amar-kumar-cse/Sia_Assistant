"""
engine/intent.py — Local Intent Handler (No API needed)
Bugs fixed:
  - BUG #33: _handle_quit() → QTimer delay ke baad quit karo, TTS pehle bolegi
  - BUG #32: pyautogui top-level import (not inside function) — proper error if missing
"""

import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

try:
    import pyautogui
    _PYAUTOGUI_OK = True
except ImportError:
    pyautogui = None  # type: ignore
    _PYAUTOGUI_OK = False


class IntentHandler:
    INTENTS = {
        "time": {
            "triggers": ["time kya", "kitne baje", "time batao", "abhi kya time", "time bata"],
            "handler": "_handle_time",
        },
        "date": {
            "triggers": ["aaj ki date", "kya date", "kaun sa din", "date batao"],
            "handler": "_handle_date",
        },
        "memory": {
            "triggers": ["yaad hai", "kya pata", "history batao", "pichli baat"],
            "handler": "_handle_memory",
        },
        "vision": {
            "triggers": ["screen dekho", "kya chal raha", "dekho screen", "screen check"],
            "handler": "_handle_vision",
        },
        "volume_up": {
            "triggers": ["volume up", "awaaz badha", "louder", "tej karo"],
            "handler": "_handle_volume_up",
        },
        "volume_down": {
            "triggers": ["volume down", "awaaz kam", "quieter", "dheema karo"],
            "handler": "_handle_volume_down",
        },
        "quit": {
            "triggers": ["band karo", "bye sia", "quit", "close karo", "jai ram ji ki"],
            "handler": "_handle_quit",
        },
        "help": {
            "triggers": ["help", "kya kar sakti", "kya kya karta", "kya kya kar sakti"],
            "handler": "_handle_help",
        },
    }

    def detect(self, text: str) -> dict:
        """Text mein koi local intent match karo. Return: {handled, emotion, text}"""
        text_lower = text.lower().strip()
        for _intent_name, data in self.INTENTS.items():
            for trigger in data["triggers"]:
                if trigger in text_lower:
                    handler = getattr(self, data["handler"])
                    result_text = handler()
                    return {
                        "handled": True,
                        "emotion": "happy",
                        "text": result_text,
                    }
        return {"handled": False}

    # ── Handlers ──────────────────────────────────────────────
    def _handle_time(self) -> str:
        t = datetime.datetime.now().strftime("%I:%M %p")
        return f"Abhi time ho raha hai {t} Hero!"

    def _handle_date(self) -> str:
        d = datetime.datetime.now().strftime("%d %B %Y")
        return f"Aaj ki date hai {d} Hero!"

    def _handle_memory(self) -> str:
        return "Haan Hero! Mujhe hamari pichli baatein achhe se yaad hain. Kya jaanna chahte ho?"

    def _handle_vision(self) -> str:
        # Main.py vision intent ko handle karega — yeh sirf confirmation text hai
        return "Main abhi screen check karti hoon, ek second Hero!"

    def _handle_volume_up(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.press("volumeup", presses=5)
            return "Awaaz badha di Hero! 🔊"
        return "Volume control ke liye pyautogui install karo Hero."

    def _handle_volume_down(self) -> str:
        if _PYAUTOGUI_OK:
            pyautogui.press("volumedown", presses=5)
            return "Awaaz kam kar di Hero! 🔉"
        return "Volume control ke liye pyautogui install karo Hero."

    def _handle_quit(self) -> str:
        # BUG #33 FIX: Pehle reply bolo, 2.5 second baad quit karo
        QTimer.singleShot(2500, QApplication.instance().quit)
        return "Bye bye Hero! Apna khayal rakhna 💙"

    def _handle_help(self) -> str:
        return (
            "Main Sia hoon Hero! Main ye sab kar sakti hoon: "
            "time batana, date batana, screen dekhna, awaaz kam/zyada karna, "
            "aur Gemini se koi bhi sawaal ka jawab dena!"
        )
