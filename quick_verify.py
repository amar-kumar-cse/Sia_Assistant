"""
quick_verify.py — Sia Assistant ko start karne se pehle sab check karo
Run: python quick_verify.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

PASS = "  [OK] "
FAIL = "  [!!] "
WARN = "  [??] "

errors = 0

print("=" * 55)
print("   SIA ASSISTANT - Pre-flight Check")
print("=" * 55)

# ── 1. Python Version ──────────────────────────────────────
print("\n[1] Python Version")
ver = sys.version_info
if ver >= (3, 10):
    print(f"{PASS} Python {ver.major}.{ver.minor}.{ver.micro}")
else:
    print(f"{FAIL} Python {ver.major}.{ver.minor} — 3.10+ chahiye!")
    errors += 1

# ── 2. Required Libraries ──────────────────────────────────
print("\n[2] Required Libraries")
libs = [
    ("PyQt5", "PyQt5"),
    ("google.generativeai", "google-generativeai"),
    ("edge_tts", "edge-tts"),
    ("speech_recognition", "SpeechRecognition"),
    ("pyaudio", "pyaudio"),
    ("dotenv", "python-dotenv"),
    ("numpy", "numpy"),
    ("soundfile", "soundfile"),
    ("mss", "mss"),
    ("PIL", "Pillow"),
]
for mod, pkg in libs:
    try:
        __import__(mod)
        print(f"{PASS} {pkg}")
    except ImportError:
        print(f"{FAIL} {pkg} — install karo: pip install {pkg}")
        errors += 1

# win32 optional but recommended
try:
    import win32gui  # noqa: F401
    print(f"{PASS} pywin32")
except ImportError:
    print(f"{WARN} pywin32 nahi hai — click-through ctypes fallback use karega")

# ── 3. Asset Files ─────────────────────────────────────────
print("\n[3] Asset Files")
required_assets = [
    "sia_idle.png",
    "Sia_closed.png",
    "Sia_semi.png",
    "Sia_open.png",
]
for fname in required_assets:
    fpath = ASSETS / fname
    if fpath.exists():
        size_kb = fpath.stat().st_size // 1024
        print(f"{PASS} {fname}  ({size_kb} KB)")
    else:
        print(f"{FAIL} {fname} — MISSING in assets/ folder!")
        errors += 1

optional_assets = ["idle.mp4", "thinking.mp4"]
for fname in optional_assets:
    fpath = ASSETS / fname
    if fpath.exists():
        print(f"{PASS} {fname}  (optional video)")
    else:
        print(f"{WARN} {fname} — optional, PNG fallback use hoga")

# ── 4. .env File & API Keys ────────────────────────────────
print("\n[4] .env Configuration")
env_path = ROOT / ".env"
if env_path.exists():
    print(f"{PASS} .env file exists")
    from dotenv import load_dotenv
    load_dotenv(env_path)

    key1 = os.environ.get("GEMINI_API_KEY", "").strip()
    key2 = os.environ.get("GEMINI_API_KEY_2", "").strip()
    key3 = os.environ.get("GEMINI_API_KEY_3", "").strip()

    keys_found = sum(bool(k) for k in [key1, key2, key3])
    if keys_found == 0:
        print(f"{FAIL} Koi bhi GEMINI_API_KEY nahi mili — .env set karo!")
        errors += 1
    else:
        print(f"{PASS} {keys_found} Gemini API key(s) found")
        if key1:
            print(f"       KEY_1: {key1[:12]}...")
        if key2:
            print(f"       KEY_2: {key2[:12]}...")
        if key3:
            print(f"       KEY_3: {key3[:12]}...")
else:
    print(f"{FAIL} .env file nahi mili root mein!")
    errors += 1

# ── 5. Temp Folder ─────────────────────────────────────────
print("\n[5] Temp Folder")
temp = ROOT / "temp"
temp.mkdir(exist_ok=True)
print(f"{PASS} temp/ folder ready")

# ── 6. Memory DB ───────────────────────────────────────────
print("\n[6] Database")
db = ROOT / "memory.db"
if db.exists():
    size_kb = db.stat().st_size // 1024
    print(f"{PASS} memory.db exists ({size_kb} KB)")
else:
    print(f"{WARN} memory.db nahi hai — pehli run par auto-create hoga")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 55)
if errors == 0:
    print("[READY]  Sab theek hai! Run karo: python main.py")
else:
    print(f"[FAIL]   {errors} error(s) mili. Upar dekho aur fix karo pehle.")
print("=" * 55)
