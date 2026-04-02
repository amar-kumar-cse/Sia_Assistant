import os
import tempfile
import time
import atexit
import glob
from typing import Optional, Tuple
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    print("⚠️  Vision Engine: GEMINI_API_KEY not found")

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
    Analyzes an image using Gemini 2.0 Flash multimodal API.
    """
    if not client:
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

        # Send image + text to Gemini (using new google-genai SDK)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[vision_prompt, img]
        )
        
        result = response.text.strip()
        print(f"👁️ Vision analysis complete")
        
        # Clean up temp image
        try:
            os.remove(image_path)
        except:
            pass
        
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
