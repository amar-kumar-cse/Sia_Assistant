import os
import tempfile
import time
import atexit
import glob
import ctypes
from typing import Optional, Tuple
from PIL import Image
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

def _load_all_api_keys() -> list[str]:
    keys: list[str] = []
    base = os.getenv("GEMINI_API_KEY", "")
    for part in base.split(","):
        key = part.strip()
        if key and "your_" not in key.lower() and len(key) > 10:
            keys.append(key)
    for i in range(2, 6):
        extra = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if extra and "your_" not in extra.lower() and len(extra) > 10:
            keys.append(extra)
    return keys


_VISION_MODELS = [
    os.getenv("GEMINI_VISION_PRIMARY_MODEL", "gemini-1.5-flash"),
    os.getenv("GEMINI_VISION_FALLBACK_MODEL", "gemini-1.5-pro"),
    os.getenv("GEMINI_VISION_LAST_MODEL", "gemini-2.0-flash"),
]

_VISION_KEYS = _load_all_api_keys()
_VISION_KEY_BLOCKED_UNTIL: dict[str, float] = {}
_VISION_MODEL_BLOCKED_UNTIL: dict[str, float] = {}
_VISION_COOLDOWN_SECONDS = 1800
_MODEL_NOT_FOUND_COOLDOWN_SECONDS = 21600

if not genai:
    print("⚠️ Vision Engine: google-genai package not installed")
elif not _VISION_KEYS:
    print("⚠️ Vision Engine: GEMINI_API_KEY not found")

def _cleanup_temp_files():
    """Clean up temporary screenshot files on exit."""
    try:
        pattern = os.path.join(tempfile.gettempdir(), "sia_*.png")
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
            except Exception:
                pass  # Ignore cleanup errors
    except Exception:
        pass

atexit.register(_cleanup_temp_files)


def _is_quota_error(error: Exception) -> bool:
    err = str(error).lower()
    return any(x in err for x in ("429", "resource_exhausted", "quota", "rate limit"))


def _is_model_not_found_error(error: Exception) -> bool:
    err = str(error).lower()
    return "404" in err or "not found" in err or "unsupported model" in err


def _seconds_until_next_vision_retry(now: Optional[float] = None) -> int:
    now = now or time.time()
    times = [ts for ts in _VISION_KEY_BLOCKED_UNTIL.values() if ts > now]
    if not times:
        return 0
    return max(0, int(min(times) - now))


def get_vision_status() -> dict:
    """
    Returns current cloud-vision health for UI.
    mode: cloud | fallback
    """
    now = time.time()

    if not genai:
        return {
            "mode": "fallback",
            "cloud_enabled": False,
            "status_text": "📷 Vision Offline (SDK missing)",
            "status_color": "red",
            "reason": "sdk_missing",
            "retry_seconds": 0,
        }

    if not _VISION_KEYS:
        return {
            "mode": "fallback",
            "cloud_enabled": False,
            "status_text": "📷 Vision Offline (No key)",
            "status_color": "red",
            "reason": "no_key",
            "retry_seconds": 0,
        }

    available_keys = [k for k in _VISION_KEYS if _VISION_KEY_BLOCKED_UNTIL.get(k, 0) <= now]
    if available_keys:
        return {
            "mode": "cloud",
            "cloud_enabled": True,
            "status_text": "📷 Vision Cloud Ready",
            "status_color": "green",
            "reason": "ok",
            "retry_seconds": 0,
        }

    retry_seconds = _seconds_until_next_vision_retry(now)
    mins = max(1, retry_seconds // 60) if retry_seconds else 1
    return {
        "mode": "fallback",
        "cloud_enabled": False,
        "status_text": f"📷 Vision Offline ({mins}m)",
        "status_color": "yellow",
        "reason": "quota_cooldown",
        "retry_seconds": retry_seconds,
    }


def _active_window_title() -> str:
    """Best-effort active window title for local fallback context."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Unknown window"
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()
        return title if title else "Unknown window"
    except Exception:
        return "Unknown window"


def _local_screen_fallback(image_path: str) -> str:
    """Fallback when cloud vision is unavailable due quota/network."""
    try:
        img = Image.open(image_path)
        w, h = img.size
    except Exception:
        w, h = (0, 0)
    title = _active_window_title()
    return (
        f"[CONFUSED] API limit hit ho gayi, full visual analysis abhi possible nahi hai. "
        f"Lekin active window '{title}' dikh rahi hai, screen size approx {w}x{h}. "
        "Chaaho toh main error text/stacktrace paste karne pe turant fix de dungi."
    )


def _safe_remove(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def capture_screen() -> Optional[str]:
    """
    Captures a screenshot of the entire screen.
    Returns the path to the saved screenshot image.
    """
    try:
        from PIL import ImageGrab
        
        screenshot = ImageGrab.grab()
        
        # Save to temp directory
        temp_path = os.path.join(tempfile.gettempdir(), f"sia_screen_{int(time.time())}.png")
        screenshot.save(temp_path, "PNG")
        
        print(f"📸 Screenshot captured: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return None


def capture_active_window() -> Optional[str]:
    """
    Captures a screenshot of the currently active window only.
    Returns the path to the saved screenshot image.
    """
    try:
        from PIL import ImageGrab
        import platform
        
        bbox = None
        if platform.system() == 'Windows':
            try:
                import ctypes
                from ctypes.wintypes import RECT
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                rect = RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                bbox = (rect.left, rect.top, rect.right, rect.bottom)
            except Exception:
                pass
                
        screenshot = ImageGrab.grab(bbox=bbox)
        temp_path = os.path.join(tempfile.gettempdir(), f"sia_window_{int(time.time())}.png")
        screenshot.save(temp_path, "PNG")
        
        print(f"📸 Window captured: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"❌ Window capture failed: {e}")
        return None


def capture_webcam() -> Optional[str]:
    """
    Captures a single frame from the default webcam.
    Returns the path to the saved image.
    """
    try:
        import cv2
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Webcam not available")
            return None
        
        # Let camera warm up
        time.sleep(0.5)
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("❌ Failed to capture webcam frame")
            return None
        
        # Save to temp
        temp_path = os.path.join(tempfile.gettempdir(), f"sia_webcam_{int(time.time())}.png")
        cv2.imwrite(temp_path, frame)
        
        print(f"📷 Webcam capture saved: {temp_path}")
        return temp_path
        
    except ImportError:
        print("⚠️ OpenCV not installed. Run: pip install opencv-python")
        return None
    except Exception as e:
        print(f"❌ Webcam capture failed: {e}")
        return None


def analyze_image(image_path: str, question: str = "Is mein kya dikh raha hai? Describe in Hinglish.") -> str:
    """
    Analyzes an image using Gemini multimodal API with key/model fallback.
    """
    if not genai:
        return "Arre Hero, vision engine setup missing hai (google-genai install karo)! 😅"

    if not _VISION_KEYS:
        return "Arre Hero, vision ke liye GEMINI_API_KEY chahiye! 😅"
    
    if not image_path or not os.path.exists(image_path):
        return "Image nahi mili, Hero! Screenshot lene mein problem hui. 😔"
    
    try:
        # Open and prepare image
        img = Image.open(image_path)
        
        # Build prompt for Sia's persona
        vision_prompt = f"""You are Sia, Amar Kumar's personal AI coding assistant. You speak in a friendly Hinglish (Hindi + English mix).
Analyze this image and answer the user's question in your style. Be extremely helpful for coding tasks. 
If there's a code error visible, act as a Senior Software Engineer: explain it and provide the exact fix.

If there's a code error visible, explain what the error means and suggest a fix.
If there's a general scene, describe what you see.

Start your response with an emotion tag like [SMILE], [HAPPY], [CONFUSED], etc.

User's question: {question}

Respond as Sia in Hinglish:"""

        # Multi-key + multi-model fallback to avoid vision downtime on quota hits.
        result: Optional[str] = None
        last_error: Optional[Exception] = None
        now = time.time()

        available_keys = [k for k in _VISION_KEYS if _VISION_KEY_BLOCKED_UNTIL.get(k, 0) <= now]
        if not available_keys:
            fallback = _local_screen_fallback(image_path)
            _safe_remove(image_path)
            return fallback

        for key in available_keys:
            client = genai.Client(api_key=key)
            for model in _VISION_MODELS:
                if _VISION_MODEL_BLOCKED_UNTIL.get(model, 0) > time.time():
                    continue
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[vision_prompt, img]
                    )
                    if response and getattr(response, "text", None):
                        result = response.text.strip()
                        break
                except Exception as model_error:
                    last_error = model_error
                    if _is_quota_error(model_error):
                        _VISION_KEY_BLOCKED_UNTIL[key] = time.time() + _VISION_COOLDOWN_SECONDS
                        _VISION_MODEL_BLOCKED_UNTIL[model] = time.time() + _VISION_COOLDOWN_SECONDS
                    elif _is_model_not_found_error(model_error):
                        _VISION_MODEL_BLOCKED_UNTIL[model] = time.time() + _MODEL_NOT_FOUND_COOLDOWN_SECONDS
                    continue
            if result:
                break

        if not result:
            fallback = _local_screen_fallback(image_path)
            _safe_remove(image_path)
            return fallback

        print(f"👁️ Vision analysis complete")
        
        # Clean up temp image
        _safe_remove(image_path)
        
        return result
        
    except Exception as e:
        print(f"❌ Vision analysis failed: {e}")
        return f"[CONFUSED] Arre yaar, image analyze karne mein dikkat aa gayi: {str(e)[:50]}... 😔"


def analyze_screen(question: str = "Meri screen pe kya hai? Describe karo.") -> str:
    """
    One-shot function: Captures screen and analyzes it.
    """
    screen_path = capture_screen()
    if not screen_path:
        return "[CONFUSED] Screenshot nahi le paayi Hero, kuch problem hai! 😔"
    
    return analyze_image(screen_path, question)


def analyze_active_window(question: str = "Is window mein kya hai? Describe karo.") -> str:
    """
    One-shot function: Captures the active window and analyzes it.
    """
    window_path = capture_active_window()
    if not window_path:
        return "[CONFUSED] Active window ka screenshot nahi le paayi Hero! 😔"
    
    return analyze_image(window_path, question)


def analyze_webcam(question: str = "Kya dikh raha hai camera mein?") -> str:
    """
    One-shot function: Captures webcam and analyzes it.
    """
    webcam_path = capture_webcam()
    if not webcam_path:
        return "[SAD] Webcam se image nahi mili, shayad camera connected nahi hai. 😔"
    
    return analyze_image(webcam_path, question)


def analyze_error_on_screen() -> str:
    """
    Special function to detect and explain errors on screen.
    """
    return analyze_screen(
        question="""Look at this screenshot carefully like a Senior Software Engineer.
        1. Identify the code, IDE, or terminal environment.
        2. Spot the exact syntax error, warning, traceback, or logical bug visible.
        3. Explain what the error means in short, friendly Hinglish.
        4. Give the exact corrected code snippet to fix it.
        
        If there's no error, just summarize what code or app is on the screen concisely."""
    )


def analyze_selected_region(bbox: Optional[Tuple[int, int, int, int]] = None) -> str:
    """
    Captures a specific area of the screen for faster/focused analysis.
    bbox is a tuple (left, top, right, bottom).
    """
    try:
        from PIL import ImageGrab
        
        # If no bbox provided, grab whole screen as fallback
        screenshot = ImageGrab.grab(bbox=bbox)
        
        temp_path = os.path.join(tempfile.gettempdir(), f"sia_region_{int(time.time())}.png")
        screenshot.save(temp_path, "PNG")
        
        return analyze_image(temp_path, "Is specific part mein kya code ya text likha hai? Samajhao.")
    except Exception as e:
        return f"❌ Region analysis failed: {e}"


def monitor_screen_for_errors(interval: int = 30) -> bool:
    """
    Background thread concept: periodically checks screen for errors.
    """
    def _monitor():
        print(f"👁️ Started background screen monitoring (interval={interval}s)...")
        while True:
            # Placeholder for lightweight local check
            time.sleep(interval)
            
    import threading
    t = threading.Thread(target=_monitor, daemon=True)
    t.start()
    return True
