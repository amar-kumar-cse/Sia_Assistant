"""
quick_test.py — Sia Assistant Backend Verification Script
Run this to check all components before launching Sia.

Usage:
    python quick_test.py
"""

import os
import sys
import socket
import subprocess

# Add project root to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

PASS = "  ✅"
FAIL = "  ❌"
WARN = "  ⚠️ "
INFO = "  ℹ️ "

def section(title):
    print(f"\n{'━'*55}")
    print(f"  {title}")
    print(f"{'━'*55}")

def check_internet():
    section("1. Internet Connectivity")
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        print(f"{PASS} Internet connection OK")
        return True
    except OSError:
        print(f"{FAIL} No internet connection!")
        print(f"     Sia will use offline/Ollama fallback.")
        return False

def check_env():
    section("2. Environment Variables (.env)")
    from dotenv import load_dotenv
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key and "your_" not in gemini_key.lower() and len(gemini_key) > 10:
        print(f"{PASS} GEMINI_API_KEY is set (...{gemini_key[-6:]})")
    else:
        print(f"{FAIL} GEMINI_API_KEY is missing or is a placeholder!")
        print(f"     → Get a FREE key at: https://aistudio.google.com/app/apikey")
        print(f"     → Then update .env file GEMINI_API_KEY=<your_key>")

    # Check backup keys
    backup_keys = []
    for i in range(2, 6):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "")
        if k and "your_" not in k.lower() and len(k) > 10:
            backup_keys.append(k)
    if backup_keys:
        print(f"{PASS} {len(backup_keys)} backup Gemini key(s) configured (rotation enabled!)")
    else:
        print(f"{WARN} No backup Gemini keys. Add GEMINI_API_KEY_2 in .env for rotation.")

    eleven_key = os.getenv("ELEVENLABS_API_KEY", "")
    if eleven_key and "your_" not in eleven_key.lower():
        print(f"{PASS} ELEVENLABS_API_KEY is set (premium voice)")
    else:
        print(f"{INFO} ElevenLabs key not set → using free Edge-TTS (works fine!)")

def check_packages():
    section("3. Required Python Packages")
    packages = {
        "PyQt5": "PyQt5",
        "google.genai (new SDK)": "google-genai",
        "speech_recognition": "SpeechRecognition",
        "pygame": "pygame",
        "requests": "requests",
        "dotenv": "python-dotenv",
        "duckduckgo_search": "duckduckgo-search",
        "psutil": "psutil",
    }
    for module, pip_name in packages.items():
        try:
            __import__(module.split(".")[0].replace(" (new SDK)", "").replace("dotenv","dotenv"))
            print(f"{PASS} {module}")
        except ImportError:
            print(f"{FAIL} {module} not installed → pip install {pip_name}")

    # Edge-TTS binary check
    try:
        result = subprocess.run(["edge-tts", "--version"], capture_output=True, timeout=5)
        print(f"{PASS} edge-tts binary found")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"{WARN} edge-tts not found → pip install edge-tts (needed for offline voice)")

def check_gemini_api():
    section("4. Gemini API Connection Test")
    has_internet = True
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
    except OSError:
        has_internet = False

    if not has_internet:
        print(f"{WARN} Skipping API test (no internet)")
        return

    try:
        from engine.brain import _key_manager, _generate_with_fallback, _MODEL_PRIORITY

        if not _key_manager.has_any_key():
            print(f"{FAIL} No valid API keys found. Cannot test Gemini.")
            return

        print(f"     Testing with model: {_MODEL_PRIORITY[0]} ...")
        try:
            response = _generate_with_fallback("Reply only: OK", stream=False)
            text = response.text.strip()[:30]
            print(f"{PASS} Gemini API working! Response: '{text}'")
        except Exception as e:
            err = str(e)
            if "quota" in err.lower() or "429" in err.lower() or "resource_exhausted" in err.lower():
                print(f"{FAIL} API Quota EXHAUSTED!")
                print(f"     → Get a NEW free key: https://aistudio.google.com/app/apikey")
                print(f"     → Add to .env as GEMINI_API_KEY=<new_key>")
                print(f"     → Or add backup: GEMINI_API_KEY_2=<another_key>")
            elif "invalid" in err.lower() or "401" in err.lower():
                print(f"{FAIL} API Key is INVALID! Check your .env file.")
            elif "not found" in err.lower() or "404" in err.lower():
                print(f"{WARN} Model not available. Will auto-fallback to next model.")
            else:
                print(f"{FAIL} Gemini error: {err[:100]}")
    except Exception as e:
        print(f"{FAIL} Could not test Gemini: {e}")

def check_voice():
    section("5. Voice Engine (Edge-TTS)")
    try:
        result = subprocess.run(
            ["edge-tts", "--voice", "hi-IN-SwaraNeural",
             "--text", "Test", "--write-media", os.path.join(BASE_DIR, "cache", "test_voice.mp3")],
            capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            print(f"{PASS} Edge-TTS works! Hindi voice available.")
        else:
            print(f"{WARN} Edge-TTS ran but may have issues: {result.stderr.decode()[:80]}")
    except FileNotFoundError:
        print(f"{FAIL} edge-tts not installed → pip install edge-tts")
    except subprocess.TimeoutExpired:
        print(f"{FAIL} edge-tts timed out (network issue?)")
    except Exception as e:
        print(f"{WARN} Edge-TTS test error: {e}")

def check_assets():
    section("6. Assets (Character Images)")
    assets_dir = os.path.join(BASE_DIR, "assets")
    required = ["Sia_closed.png", "Sia_semi.png", "Sia_open.png"]
    optional = ["sia_idle.png", "sia_happy.png"]

    for fn in required:
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) // 1024
            print(f"{PASS} {fn} ({size_kb} KB)")
        else:
            print(f"{FAIL} {fn} MISSING — lip-sync won't work!")

    for fn in optional:
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            print(f"{PASS} {fn}")
        else:
            print(f"{INFO} {fn} optional, not found")

def check_memory_db():
    section("7. Memory Database")
    db_path = os.path.join(BASE_DIR, "memory.db")
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) // 1024
        print(f"{PASS} memory.db exists ({size_kb} KB)")
    else:
        print(f"{INFO} memory.db will be created on first run")

    try:
        from engine import memory
        facts = memory.get_recent_facts(3)
        print(f"{PASS} Memory module OK — {len(facts)} facts stored")
    except Exception as e:
        print(f"{WARN} Memory module warning: {e}")

def main():
    print("\n" + "═" * 55)
    print("  🎀 SIA ASSISTANT — Backend Verification")
    print("═" * 55)

    check_internet()
    check_env()
    check_packages()
    check_gemini_api()
    check_voice()
    check_assets()
    check_memory_db()

    print(f"\n{'═'*55}")
    print("  ✅ Verification complete!")
    print("  → If all checks pass, run: python sia_desktop.py")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
