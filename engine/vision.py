"""
engine/vision.py — Screen Capture + Gemini Vision Analysis
Bugs fixed:
  - BUG #34: Hamesha KEY_1 use karta tha → ab rotation logic add kiya
  - BUG #35: mss BGRX → numpy se correct RGB conversion
"""

import os
from pathlib import Path

import google.generativeai as genai
import numpy as np
from PIL import Image

try:
    import mss
    _MSS_OK = True
except ImportError:
    mss = None  # type: ignore
    _MSS_OK = False

# Temp folder ensure karo
_TEMP_DIR = Path(__file__).parent.parent / "temp"
_TEMP_DIR.mkdir(exist_ok=True)
_SCREEN_PATH = str(_TEMP_DIR / "screen.png")


class VisionEngine:
    def __init__(self, memory):
        self.memory = memory
        # BUG #34 FIX: Keys rotate karo — sirf KEY_1 pe depend mat raho
        self._keys = [
            os.environ.get("GEMINI_API_KEY", ""),
            os.environ.get("GEMINI_API_KEY_2", ""),
            os.environ.get("GEMINI_API_KEY_3", ""),
        ]
        self._keys = [k.strip() for k in self._keys if k.strip()]
        self._key_idx = 0

    def _get_key(self) -> str | None:
        if not self._keys:
            return None
        return self._keys[self._key_idx % len(self._keys)]

    def _next_key(self):
        self._key_idx = (self._key_idx + 1) % max(len(self._keys), 1)

    def _capture_screen(self) -> Image.Image | None:
        """Screen capture karo PIL Image mein."""
        if not _MSS_OK:
            print("[Vision] mss library not installed.")
            return None
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                shot = sct.grab(monitor)
                # BUG #35 FIX: numpy se correct BGRA→RGB conversion
                arr = np.array(shot)          # shape: (H, W, 4) BGRA
                rgb = arr[:, :, [2, 1, 0]]   # BGRA → RGB (swap B & R)
                return Image.fromarray(rgb, "RGB")
        except Exception as exc:
            print(f"[Vision] Screen capture failed: {exc}")
            return None

    def capture_and_analyze(self) -> str:
        """Screen capture karo + Gemini Vision se analyze karo."""
        img = self._capture_screen()
        if img is None:
            return "Screen capture mein problem aagayi Hero."

        # Save karo temp mein
        try:
            img.save(_SCREEN_PATH)
        except Exception as exc:
            print(f"[Vision] Image save failed: {exc}")
            return "Screen save nahi ho paya Hero."

        # BUG #34 FIX: Keys rotate karo
        for _attempt in range(len(self._keys) or 1):
            key = self._get_key()
            if not key:
                return "Vision ke liye koi Gemini API key nahi mili Hero."

            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    "Screen par kya ho raha hai? 2-3 lines mein simple Hinglish mein batao.",
                    Image.open(_SCREEN_PATH),
                ])
                result = response.text.strip()
                self.memory.save_vision(result)
                return result

            except Exception as exc:
                err = str(exc).lower()
                if "429" in err or "quota" in err or "resource_exhausted" in err:
                    self._next_key()
                    continue
                print(f"[Vision] Gemini error: {exc}")
                return "Vision analysis mein error aagaya Hero."

        return "Saari API keys ki limit ho gayi Hero. Thodi der baad try karo."
