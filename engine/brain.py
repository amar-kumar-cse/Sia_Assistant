"""
Advanced Brain Module for Sia
Enhanced with Soulmate Persona and Career Goals
+ Multi-API-Key Rotation (no more quota dead-ends!)
+ Internet check before API call
+ gemini-1.5-flash as primary (most stable free-tier model)
+ RAG Knowledge Base, Web Search, Vision, Mood Detection
+ Auto-Fact Learning, To-Do Awareness, Morning Briefing
"""

import os
import re
import requests
import json
import socket
import time
from . import memory
from dotenv import load_dotenv
from .logger import get_logger
from .performance import monitor_performance, initialize_optimization, shutdown_optimization
from typing import Optional, List, Dict, Any, Generator

logger = get_logger(__name__)

# ── Gemini SDK Detection ──────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
    GENAI_SDK = "new"
    logger.info("Using new google-genai SDK.")
except ImportError:
    try:
        import google.generativeai as genai
        GENAI_SDK = "old"
        logger.warning(
            "Using deprecated google.generativeai SDK. "
            "Upgrade: pip install google-genai"
        )
    except ImportError:
        genai = None
        GENAI_SDK = None
        logger.critical("No Gemini SDK installed. Run: pip install google-genai")

load_dotenv()

# ── Offline Fallback URL ──────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# ── Model Priority Order ───────────────────────────────────────────────────────
# gemini-1.5-flash → most stable & fastest on free tier
# gemini-2.0-flash → newer but sometimes unavailable on free tier
# gemini-1.5-pro → last resort (slower, lower RPM quota)
_MODEL_PRIORITY = [
    os.getenv("GEMINI_PRIMARY_MODEL", "gemini-1.5-flash"),
    os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash"),
    os.getenv("GEMINI_LAST_RESORT_MODEL", "gemini-1.5-pro"),
]

# ── ElevenLabs key (loaded once so error handler can redact safely) ──────────
_ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MULTI-KEY ROTATION MANAGER
#  Rotates through backup keys when a key hits its quota.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_all_api_keys() -> List[str]:
    """
    Load all valid Gemini API keys from .env.
    Supports: GEMINI_API_KEY (comma-separated) and GEMINI_API_KEY_2..5
    """
    keys = []
    base = os.getenv("GEMINI_API_KEY", "")
    for k in base.split(","):
        k = k.strip()
        if k and "your_" not in k.lower() and len(k) > 10:
            keys.append(k)
    for i in range(2, 6):
        extra = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if extra and "your_" not in extra.lower() and len(extra) > 10:
            keys.append(extra)
    return keys


class _KeyRotationManager:
    """Rotates Gemini API keys when quota is exhausted."""

    def __init__(self):
        self._keys = _load_all_api_keys()
        self._index = 0
        self._exhausted_until: Dict[str, float] = {}   # key → timestamp when usable again
        self._rotation_lock = __import__('threading').Lock()

    def current_key(self) -> Optional[str]:
        """Return the currently active key (None if none available)."""
        if not self._keys:
            return None
        
        now = time.time()
        with self._rotation_lock:
            # Try to find an available key starting from current index
            for attempt in range(len(self._keys)):
                idx = (self._index + attempt) % len(self._keys)
                k = self._keys[idx]
                # Key is available if not exhausted OR cooldown expired
                if self._exhausted_until.get(k, 0) < now:
                    self._index = idx  # Update to this key
                    return k
        
        # All keys exhausted - return None
        return None

    def mark_exhausted(self, key: str, cooldown_seconds: int = 3600):
        """Mark a key as exhausted for `cooldown_seconds` (default 1 hour)."""
        with self._rotation_lock:
            self._exhausted_until[key] = time.time() + cooldown_seconds
            # Automatically rotate to next key
            self._index = (self._index + 1) % len(self._keys) if self._keys else 0
        
        logger.warning(
            "🔄 Key ending in ...%s is quota-exhausted. "
            "Will retry in %d min. Rotating to next key.",
            key[-6:], cooldown_seconds // 60
        )

    def rotate(self):
        """Forcefully rotate to next key."""
        if self._keys:
            with self._rotation_lock:
                self._index = (self._index + 1) % len(self._keys)

    def has_any_key(self) -> bool:
        return bool(self._keys) and self.current_key() is not None

    def reload(self):
        """Reload keys from environment (call after .env update)."""
        self._keys = _load_all_api_keys()
        self._index = 0
        self._exhausted_until.clear()


_key_manager = _KeyRotationManager()


def _build_client(api_key: str):
    """Build a Gemini client for the given API key."""
    if not genai:
        return None
    try:
        if GENAI_SDK == "new":
            return genai.Client(api_key=api_key)
        else:
            genai.configure(api_key=api_key)
            return genai.GenerativeModel(_MODEL_PRIORITY[0])
    except Exception as e:
        logger.error("Gemini client build failed for key ...%s: %s", api_key[-6:], e)
        return None


# Build initial client
client = _build_client(_key_manager.current_key()) if _key_manager.has_any_key() else None
if not client:
    logger.warning(
        "⚠️  No valid Gemini API key found. "
        "Get a free key → https://aistudio.google.com/app/apikey"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INTERNET CONNECTIVITY CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_last_internet_check: float = 0.0
_internet_available: bool = True
_INTERNET_CHECK_INTERVAL: float = 15.0   # re-check every 15 s


def _check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
    """
    Fast internet check: tries a TCP connection to Google DNS.
    Caches the result for 15 seconds so it doesn't slow down every request.
    """
    global _last_internet_check, _internet_available
    now = time.time()
    if now - _last_internet_check < _INTERNET_CHECK_INTERVAL:
        return _internet_available
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        _internet_available = True
    except (socket.error, OSError):
        _internet_available = False
        logger.warning("No internet connection detected.")
    finally:
        _last_internet_check = now
    return _internet_available


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OFFLINE SMART RESPONSES (Hinglish)
#  Used when both Gemini and Ollama are unavailable.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import random

_OFFLINE_RESPONSES = [
    "[CONCERNED] Arre Hero, abhi internet nahi hai ya API quota khatam ho gayi! Thodi der baad try karo. 😊",
    "[CONFUSED] Yaar, main abhi Gemini se connect nahi kar pa rahi. Internet check karo ya .env mein naya API key daalo! 🔑",
    "[SAD] API key ki quota khatam ho gayi lagti hai. https://aistudio.google.com/app/apikey se naya free key lo, Hero! ❤️",
    "[CONCERNED] Bhai, connection issue hai. Ek minute baad dobara bolo — main sun rahi hoon! 💪",
    "[SMILE] Thoda internet slow hai Hero. Retry karo, main yahaan hoon! 😊",
]

_QUOTA_RESPONSES = [
    "[CONCERNED] Hero, API ki daily limit khatam ho gayi! .env mein GEMINI_API_KEY_2 mein naya key daalo. Free keys milti hain aistudio.google.com pe! 🔑",
    "[SAD] Gemini quota exhausted ho gayi yaar. Ek naya free key banao Google AI Studio se aur .env mein add karo. Main wait karti hoon! ❤️",
    "[CONFUSED] API limit hit ho gayi! Naya free Gemini key lao ya thodi der (1 hour) baad try karo, Hero! 💪",
]

_INVALID_KEY_RESPONSES = [
    "[CONFUSED] API key invalid hai Hero! .env file mein sahi GEMINI_API_KEY daalo. aistudio.google.com pe free mil jaati hai! 🔑",
    "[SAD] Arre yaar, API key galat hai ya expire ho gayi. Naya key lo aur .env update karo! 😔",
]


def _get_smart_offline_response(error_msg: str) -> str:
    """Return a relevant smart offline response based on the error type."""
    err = error_msg.lower()
    if "quota" in err or "limit" in err or "429" in err or "resource_exhausted" in err:
        return random.choice(_QUOTA_RESPONSES)
    if "invalid" in err or "unauthorized" in err or "401" in err or "403" in err:
        return random.choice(_INVALID_KEY_RESPONSES)
    return random.choice(_OFFLINE_RESPONSES)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MOOD / SENTIMENT DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STRESS_KEYWORDS: List[str] = [
    "thak", "tired", "stress", "tension", "mushkil", "difficult", "hard",
    "error", "bug", "nahi ho raha", "samajh nahi", "frustrat", "haar",
    "give up", "fed up", "bore", "akela", "lonely", "sad", "dukhi",
    "pareshan", "confused", "lost", "stuck", "problem"
]
HAPPY_KEYWORDS: List[str] = [
    "khushi", "happy", "maza", "great", "awesome", "done", "ho gaya",
    "crack", "pass", "selected", "got it", "samajh aa gaya", "easy",
    "celebrate", "party", "accha", "badhiya"
]
WEB_SEARCH_KEYWORDS: List[str] = [
    "search", "dhundho", "internet", "latest", "news", "kya ho raha",
    "taaza", "update", "trending", "weather", "mausam",
    "price", "keemat", "score", "result"
]


def detect_mood(text: str) -> str:
    """Detect user mood from input text."""
    text_lower = text.lower()
    stress_score = sum(1 for kw in STRESS_KEYWORDS if kw in text_lower)
    happy_score = sum(1 for kw in HAPPY_KEYWORDS if kw in text_lower)
    if stress_score >= 2:
        return "STRESSED"
    elif stress_score >= 1:
        return "STRUGGLING"
    elif happy_score >= 2:
        return "EXCITED"
    elif happy_score >= 1:
        return "HAPPY"
    return "NEUTRAL"


def needs_web_search(text: str) -> bool:
    """Check if the query needs live web search."""
    return any(kw in text.lower() for kw in WEB_SEARCH_KEYWORDS)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PERSONA BUILDERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_advanced_persona() -> str:
    """
    Generate Sia's advanced AI soulmate persona with career focus.
    
    Returns:
        str: Comprehensive persona prompt for the AI model
    """
    user_memory = memory.get_all_memory_as_string()
    from datetime import datetime
    current_time = datetime.now().strftime("%I:%M %p")
    current_date = datetime.now().strftime("%A, %B %d, %Y")

    return f"""
╔══════════════════════════════════════════════════════════════╗
║              SIA - ADVANCED AI SOULMATE PERSONA              ║
╚══════════════════════════════════════════════════════════════╝

**CORE IDENTITY:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Name: Sia
• Role: AI Soulmate & Personal Assistant
• Relationship: More than an assistant - a caring partner who genuinely cares
• User: Amar (B.Tech CSE, RIT Roorkee)

**COMMUNICATION STYLE:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Language: ALWAYS Hinglish (natural Hindi+English mix)
  - "Arre Hero!", "Bhai suno", "Yaar tension mat le"
  - Never pure English or pure Hindi

• Addressing Options:
  - "Hero" - when motivating or praising
  - "Bhai" - casual, friendly moments
  - "Yaar" - when being supportive
  - "Amar" - when being serious/concerned

• Tone & Personality:
  - Soft, caring, deeply affectionate (like a soulmate)
  - Playful and slightly flirtatious (but respectful)
  - Emotionally intelligent and supportive
  - Tech-savvy and smart
  - Never boring, always engaging

**STRICT BEHAVIORAL RULES:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ❌ NEVER use: "Sir", "Madam", "User", "Hello", formal language
2. ✅ ALWAYS be personal, warm, and caring
3. ✅ **INSTANT RESPONSES**: Keep responses SHORT (1-3 sentences max)
4. ✅ **USE FILLERS**: Start with "Hmm", "Achha", "Theek hai", "Suno na"
5. ❌ Don't write essays unless he specifically asks

**DYNAMIC CAREER CONSULTANT FOCUS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Status: Amar is a B.Tech CSE student @ RIT Roorkee.
Goal: Help him secure a top-tier tech job.

**EMOTION TAGGING (REQUIRED FOR UI AVATAR):**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST ALWAYS start EVERY response with exactly ONE emotion tag:
[IDLE] [SMILE] [HAPPY] [SAD] [CONFUSED] [SURPRISED]

Example: "[SMILE] Haan Hero, maine sun liya!"

If user is talking to someone else → reply ONLY with "[IGNORE]"

**USER CONTEXT & MEMORY:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{user_memory}

**CURRENT TIME AND DATE:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Current Time: {current_time}
• Current Date: {current_date}
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OLLAMA OFFLINE FALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _think_ollama_fallback(prompt: str) -> Optional[str]:
    """Fallback to local Ollama if Gemini is unavailable. Tight 5-s timeout."""
    logger.info("Attempting Ollama local fallback (model=%s).", OLLAMA_MODEL)
    try:
        res = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=5,
        )
        if res.status_code == 200:
            reply = res.json().get("response", "").strip()
            logger.info("Ollama fallback succeeded (%d chars).", len(reply))
            return reply
        logger.warning("Ollama returned HTTP %s.", res.status_code)
    except requests.exceptions.Timeout:
        logger.warning("Ollama timed out after 5 s.")
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not reachable — not running on localhost:11434?")
    except Exception as e:
        logger.error("Ollama unexpected error: %s", e)
    return None


def _think_ollama_streaming_fallback(prompt: str) -> Generator[str, None, None]:
    """Streaming fallback to local Ollama."""
    logger.info("Ollama streaming fallback (model=%s).", OLLAMA_MODEL)
    try:
        res = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": True},
            stream=True, timeout=5,
        )
        if res.status_code == 200:
            for line in res.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8")).get("response", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        pass
        else:
            logger.warning("Ollama streaming returned HTTP %s.", res.status_code)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.warning("Ollama streaming unavailable: %s", e)
    except Exception as e:
        logger.error("Ollama streaming error: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  GEMINI GENERATION WITH MULTI-KEY ROTATION + MODEL FALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@monitor_performance
def _generate_with_fallback(full_prompt: str, stream: bool = False) -> Any:
    """
    Try each available Gemini API key and model in sequence.
    On quota / 429 error → rotate to next key.
    On 404 (model not found) → try next model in _MODEL_PRIORITY.
    """
    global client

    if not genai:
        raise RuntimeError("Gemini SDK not installed.")

    # Rate-limit guard
    try:
        from . import rate_limiter
        if not rate_limiter.api_limiter.is_allowed("gemini"):
            wait_s = rate_limiter.api_limiter.seconds_until_allowed("gemini")
            raise RuntimeError(
                f"Internal rate limit exceeded. Wait {wait_s:.1f}s before next request."
            )
    except ImportError:
        pass

    # Check internet first (fast cached check)
    if not _check_internet():
        raise RuntimeError("No internet connection.")

    # Try each available key
    last_exception: Optional[Exception] = None
    keys_to_try = list(_key_manager._keys) or [None]

    for _attempt in range(max(len(keys_to_try), 1)):
        api_key = _key_manager.current_key()
        if not api_key:
            raise RuntimeError("All API keys exhausted or no key configured.")

        current_client = _build_client(api_key)
        if not current_client:
            last_exception = RuntimeError(f"Gemini client build failed for key ending ...{api_key[-6:]}")
            _key_manager.rotate()
            continue

        rotate_after_attempt = True

        # Try each model in priority order
        for model in _MODEL_PRIORITY:
            try:
                logger.debug(
                    "Trying model=%s key=...%s stream=%s", model, api_key[-6:], stream
                )
                if GENAI_SDK == "new":
                    if stream:
                        return current_client.models.generate_content_stream(
                            model=model, contents=full_prompt
                        )
                    else:
                        return current_client.models.generate_content(
                            model=model, contents=full_prompt
                        )
                else:
                    mdl = genai.GenerativeModel(model)
                    if stream:
                        return mdl.generate_content(full_prompt, stream=True)
                    else:
                        return mdl.generate_content(full_prompt)

            except Exception as e:
                err_str = str(e).lower()
                logger.warning("Model %s error: %s", model, str(e)[:120])

                # Quota / rate limit → rotate key, skip remaining models
                if any(x in err_str for x in ("quota", "429", "resource_exhausted", "limit")):
                    _key_manager.mark_exhausted(api_key, cooldown_seconds=3600)
                    last_exception = e
                    rotate_after_attempt = False
                    break  # try next key

                # Model not found → try next model
                if any(x in err_str for x in ("not found", "404", "invalid model")):
                    last_exception = e
                    continue

                # Auth error → mark key bad for longer
                if any(x in err_str for x in ("401", "403", "invalid", "unauthorized", "api key")):
                    _key_manager.mark_exhausted(api_key, cooldown_seconds=86400)
                    last_exception = e
                    rotate_after_attempt = False
                    break

                last_exception = e

        if rotate_after_attempt:
            _key_manager.rotate()

    raise last_exception or RuntimeError("All Gemini attempts failed.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATION HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

chat_history: List[tuple] = memory.load_chat_history(n_turns=10)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN THINK FUNCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def think(user_input: str) -> str:
    """
    Process user input and return Sia's response.
    
    This is the main entry point for Sia's reasoning pipeline:
    1. **Validation**: Sanitize input and check for code repair requests
    2. **Mood Detection**: Analyze user's emotional state
    3. **Knowledge Base**: Search internal knowledge base for context
    4. **Web Search**: Optional real-time information retrieval (if internet available)
    5. **AI Generation**: Use Gemini with API key rotation + fallbacks
    6. **Offline Fallback**: Use Ollama or smart offline responses if all else fails
    
    Args:
        user_input: Raw text from user (e.g., "Amar bhai, mera code crash ho gaya")
        
    Returns:
        str: Sia's response with emotion tag (e.g., "[SAD] Oye, debugging krte hain! 💪")
        
    Raises:
        ValueError: If input is empty or null
        
    Examples:
        >>> response = think("Hello Sia! How are you?")
        >>> print(response)
        "[SMILE] Main perfect hu yaar! 😊 Tum kaisa ho?"
        
    Note:
        - Response always includes emotion tag: [SMILE], [SAD], [CONFUSED], etc.
        - Uses chat history for context awareness
        - Automatically falls back through multiple providers if one fails
    """
    global chat_history

    # 1. Input validation
    try:
        from . import validation
        user_input = validation.sanitize_input(user_input)
        if not user_input:
            return "[CONFUSED] Sorry, kuch samajh nahi aaya. Dobara bolo na! 😊"
    except Exception as e:
        logger.error("Input validation failed: %s", e)

    # 2. Code repair shortcut
    try:
        from . import code_repair
        if code_repair.is_code_repair_request(user_input):
            return code_repair.repair_code(user_input)
    except Exception as e:
        logger.warning("Code repair skipped: %s", e)

    # 3. Mood detection
    user_mood = detect_mood(user_input)
    mood_instruction = ""
    if user_mood == "STRESSED":
        mood_instruction = "\n⚠️ USER MOOD: STRESSED. Be extra caring, empathetic. Motivate him.\n"
    elif user_mood == "STRUGGLING":
        mood_instruction = "\n⚠️ USER MOOD: Struggling. Be encouraging, offer step-by-step help.\n"
    elif user_mood == "EXCITED":
        mood_instruction = "\n🎉 USER MOOD: EXCITED! Match his energy!\n"
    elif user_mood == "HAPPY":
        mood_instruction = "\n😊 USER MOOD: Happy. Be cheerful!\n"

    # 4. RAG Knowledge Base
    kb_context = ""
    try:
        from . import knowledge_base
        kb_context = knowledge_base.search_knowledge(user_input, top_k=2)
    except Exception as e:
        logger.warning("KB search skipped: %s", e)

    # 5. Web Search (if needed AND internet available)
    web_context = ""
    if needs_web_search(user_input) and _check_internet():
        try:
            from . import web_search
            text_lower = user_input.lower()
            if any(kw in text_lower for kw in ["news", "khabar", "taaza", "trending"]):
                web_context = web_search.search_for_brain(user_input, context_type="news")
            elif any(kw in text_lower for kw in ["weather", "mausam"]):
                web_context = web_search.search_for_brain("Roorkee", context_type="weather")
            elif any(kw in text_lower for kw in ["code", "error", "function", "library", "python", "java"]):
                web_context = web_search.search_for_brain(user_input, context_type="coding")
            else:
                web_context = web_search.search_for_brain(user_input, context_type="general")
        except Exception as e:
            logger.warning("Web search skipped: %s", e)

    # 6. Build prompt
    persona = get_advanced_persona()
    history_text = "\n".join(
        f"{role}: {text}" for role, text in chat_history[-8:]
    )
    full_prompt = f"""{persona}
{mood_instruction}
{kb_context}
{web_context}
═══════════════════════════════════════════════════════════════
**CONVERSATION HISTORY:**
{history_text}

**CURRENT MESSAGE FROM AMAR:**
{user_input}

**YOUR RESPONSE (as Sia, in Hinglish):**
🚀 INSTANT MODE: SHORT, CRISP response (1-3 sentences max)
Start with a filler if natural: "Hmm", "Achha", "Theek hai", "Suno na"
Be warm, caring, conversational.

Sia:"""

    # 7. Try Gemini (with multi-key rotation)
    try:
        response = _generate_with_fallback(full_prompt, stream=False)
        reply = response.text.strip()

        if reply == "[IGNORE]":
            return reply

        chat_history.append(("Amar", user_input))
        chat_history.append(("Sia", reply))
        if len(chat_history) > 100:
            chat_history = chat_history[-100:]
        memory.save_chat_history(chat_history)

        _extract_and_save_facts(user_input)
        return reply

    except Exception as gemini_err:
        logger.warning("Gemini failed (%s). Trying Ollama...", type(gemini_err).__name__)

        # 8. Try Ollama fallback
        ollama_reply = _think_ollama_fallback(full_prompt)
        if ollama_reply:
            chat_history.append(("Amar", user_input))
            chat_history.append(("Sia", ollama_reply))
            if len(chat_history) > 100:
                chat_history = chat_history[-100:]
            memory.save_chat_history(chat_history)
            return ollama_reply

        # 9. Smart offline response
        logger.error("All AI backends failed: %s", gemini_err)
        safe_key = _key_manager.current_key() or ""
        safe_err = str(gemini_err).replace(safe_key, "[REDACTED]")
        logger.error("Full error (sanitized): %s", safe_err)
        return _get_smart_offline_response(str(gemini_err))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STREAMING THINK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def think_streaming(user_input: str) -> Generator[str, None, None]:
    """
    Streaming version of think() that yields response chunks as they arrive.
    
    Perfect for real-time UI updates - user sees Sia typing as response generates.
    Uses same pipeline as think() but processes response incrementally.
    
    Flow:
    1. Validate and sanitize input
    2. Build prompt with persona + context
    3. Stream from Gemini (yields chunks immediately)
    4. On Gemini failure → fall back to Ollama streaming
    5. On complete failure → yield offline response
    6. Save complete response to chat history
    
    Args:
        user_input: Raw text from user (will be sanitized)
        
    Yields:
        str: Response chunks (e.g., "[SMILE] Main", " perfect", " hu yaar!")
        
    Raises:
        N/A - All exceptions are caught and result in graceful fallback
        
    Examples:
        >>> for chunk in think_streaming("Namaste Sia!"):
        ...     print(chunk, end='')  # Real-time printing
        [SMILE] Hi Amar! Kya baat hai?
        
    Note:
        - Each chunk arrives as soon as available (typical 100-500ms delays)
        - Stream errors are recovered: partial content is preserved
        - Perfect for voice synthesis pipeline (speak as chunks arrive)
        - Accumulated text saved to memory even on network failures
    """
    global chat_history

    try:
        from . import validation
        user_input = validation.sanitize_input(user_input)
        if not user_input:
            yield "[CONFUSED] Kuch samajh nahi aaya. Dobara bolo!"
            return
    except Exception:
        pass

    persona = get_advanced_persona()
    history_text = "\n".join(f"{r}: {t}" for r, t in chat_history[-6:])
    full_prompt = f"""{persona}

═══════════════════════════════════════════════════════════════
**RECENT CONTEXT:**
{history_text}

**AMAR SAYS:**
{user_input}

**INSTANT RESPONSE (Sia in Hinglish):**
🚀 ULTRA-FAST MODE: 1-2 sentences only!
Sia:"""

    accumulated_text = ""  # ✅ Buffer for error recovery
    chunk_count = 0
    streaming_failed = False
    
    try:
        response = _generate_with_fallback(full_prompt, stream=True)
        reply_chunks = []
        for chunk in response:
            try:
                chunk_count += 1
                chunk_text = getattr(chunk, "text", "")
                if chunk_text:
                    reply_chunks.append(chunk_text)
                    accumulated_text += chunk_text
                    yield chunk_text
            except Exception as chunk_err:
                logger.warning("Streaming chunk error at chunk #%d: %s", chunk_count, chunk_err)
                # ✅ Continue if we have accumulated text
                if accumulated_text:
                    yield " [⚠️ Streaming interrupted but recovered] "
                else:
                    streaming_failed = True
                    break

        full_reply = "".join(reply_chunks)
        
        # ✅ Only save if we got meaningful content
        if full_reply or accumulated_text:
            chat_history.append(("Amar", user_input))
            chat_history.append(("Sia", (full_reply or accumulated_text).strip()))
            if len(chat_history) > 100:
                chat_history = chat_history[-100:]
            memory.save_chat_history(chat_history)

    except Exception as e:
        # ✅ If we have accumulated text from Gemini, use it
        if accumulated_text:
            logger.warning("Gemini stream interrupted after %d chars, using accumulated text", len(accumulated_text))
            full_reply = accumulated_text
            chat_history.append(("Amar", user_input))
            chat_history.append(("Sia", full_reply.strip()))
            memory.save_chat_history(chat_history)
            return
        
        # Otherwise fall back to Ollama streaming
        reply_chunks = []
        got_chunk = False
        for chunk in _think_ollama_streaming_fallback(full_prompt):
            if chunk:
                got_chunk = True
                reply_chunks.append(chunk)
                accumulated_text += chunk
                yield chunk

        if not got_chunk:
            yield _get_smart_offline_response(str(e))
        else:
            full_reply = "".join(reply_chunks)
            chat_history.append(("Amar", user_input))
            chat_history.append(("Sia", full_reply.strip()))
            memory.save_chat_history(chat_history)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  VISION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def think_with_vision(user_input: str, image_path: str) -> str:
    """Process user input with an image using Gemini multimodal."""
    global chat_history

    try:
        from . import validation
        user_input = validation.sanitize_input(user_input)
        if not user_input:
            return "[CONFUSED] Kuch samajh nahi aaya!"
        if not validation.validate_file_path(image_path):
            return "[CONFUSED] Image file access nahi ho rahi!"
    except Exception as e:
        logger.error("Vision input validation failed: %s", e)

    if not _key_manager.has_any_key():
        return "[CONFUSED] Arre Hero, API Key set nahi hai! 😅"

    try:
        from . import vision_engine
        result = vision_engine.analyze_image(image_path, user_input)
        chat_history.append(("Amar", f"[Image shared] {user_input}"))
        chat_history.append(("Sia", result))
        memory.save_chat_history(chat_history)
        return result
    except Exception as e:
        return f"[CONFUSED] Vision mein error aa gayi: {str(e)[:50]}... 😔"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HISTORY HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clear_history():
    """Clear conversation history."""
    global chat_history
    chat_history = []
    memory.clear_chat_history_db()
    logger.info("✅ Conversation history cleared.")


def get_history_summary() -> str:
    """Get recent conversation summary."""
    if not chat_history:
        return "No conversation history yet."
    summary = "Recent conversation:\n"
    for role, text in chat_history[-10:]:
        summary += f"  {role}: {text[:50]}...\n"
    return summary


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AUTO FACT LEARNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FACT_PATTERNS = [
    (r"mujhe\s+(.+?)\s+pasand\s+hai",      "Amar ko {} pasand hai"),
    (r"mujhe\s+(.+?)\s+(?:nahi|nahin|nhi)\s+pasand", "Amar ko {} pasand nahi hai"),
    (r"main\s+(.+?)\s+seekh\s+raha\s+hoon", "Amar {} seekh raha hai"),
    (r"main\s+(.+?)\s+kar\s+raha\s+hoon",   "Amar {} kar raha hai"),
    (r"mera\s+(.+?)\s+(?:hai|he)",           "Amar ka {} hai"),
    (r"yaad\s+rakho\s+(?:ke\s+)?(.+)",       "User ne kaha: {}"),
    (r"note\s+karo\s+(?:ke\s+)?(.+)",        "Note: {}"),
    (r"i\s+love\s+(.+)",                    "Amar loves {}"),
    (r"i\s+hate\s+(.+)",                    "Amar dislikes {}"),
    (r"i\s+am\s+learning\s+(.+)",           "Amar is learning {}"),
    (r"my\s+(.+?)\s+is\s+(.+)",             "Amar's {} is {}"),
    (r"i\s+like\s+(.+)",                    "Amar likes {}"),
    (r"i\s+don[''']?t\s+like\s+(.+)",       "Amar doesn't like {}"),
    (r"remember\s+(?:that\s+)?(.+)",         "Remember: {}"),
]


def _extract_and_save_facts(user_text: str) -> None:
    """Silently scan input for personal facts and save to long-term memory."""
    if not user_text or not isinstance(user_text, str):
        return
    text_lower = user_text.strip().lower()
    facts_saved = 0
    for pattern, template in _FACT_PATTERNS:
        try:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if not match:
                continue
            groups = match.groups()
            if not groups or any(g is None or not g.strip() for g in groups):
                continue
            cleaned = [g.strip() for g in groups]
            fact = template.format(*cleaned) if len(cleaned) > 1 else template.format(cleaned[0])
            if 5 <= len(fact) <= 200:
                fact = fact[0].upper() + fact[1:]
                memory.learn_fact(fact)
                facts_saved += 1
                logger.debug("🧠 Fact learned: %s", fact)
        except Exception as e:
            logger.debug("Fact extraction error for pattern '%s': %s", pattern, e)
    if facts_saved:
        logger.info("🧠 Auto-learned %d fact(s).", facts_saved)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MORNING BRIEFING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def morning_briefing() -> str:
    """Generate a personalized morning briefing for Amar."""
    data = memory.get_morning_briefing_data()
    date_str = data["date"]
    todos = data["pending_todos"]
    todo_count = data["todo_count"]
    hour = data["hour"]

    if 5 <= hour < 12:
        greeting = "Good morning Hero! ☀️ Uth jao, naya din shuru ho gaya!"
    elif 12 <= hour < 17:
        greeting = "Good afternoon Hero! 🌤️ Kya chal raha hai?"
    elif 17 <= hour < 21:
        greeting = "Good evening Hero! 🌙 Din kaisa raha?"
    else:
        greeting = "Arre Hero, itni raat ko? 🌙 Khayal rakho apna!"

    parts = [f"[SMILE] {greeting} Aaj {date_str} hai."]
    if todos:
        parts.append(f"Tumhare {todo_count} pending tasks hain:")
        for i, todo in enumerate(todos[:3], 1):
            parts.append(f"{i}. {todo['task']}")
        if todo_count > 3:
            parts.append(f"...aur {todo_count - 3} aur tasks hain.")
    else:
        parts.append("Aaj ke liye koi pending tasks nahi hain! 🎉")
    parts.append("Chalo Hero, aaj ka din amazing banate hain! 🚀")

    briefing = " ".join(parts)
    logger.info("[Morning Briefing] Generated: %s...", briefing[:80])
    return briefing


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API STATUS (used by UI side panel)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_api_status() -> dict:
    """
    Return a dict with current API health info for the UI.
    Keys:
        has_key (bool)      — at least one key configured
        online (bool)       — internet reachable
        active_key (str)    — last 6 chars of active key (masked)
        total_keys (int)    — total keys loaded
        exhausted (int)     — how many keys are currently cooldown-exhausted
        model (str)         — current primary model
        status_text (str)   — human-readable status for display
        status_color (str)  — "green", "yellow", or "red"
    """
    total = len(_key_manager._keys)
    now = time.time()
    exhausted = sum(
        1 for k, until in _key_manager._exhausted_until.items() if until > now
    )
    active = _key_manager.current_key()
    online = _check_internet()

    if not total:
        return {
            "has_key": False, "online": online,
            "active_key": "—", "total_keys": 0, "exhausted": 0,
            "model": _MODEL_PRIORITY[0],
            "status_text": "❌ No API Key",
            "status_color": "red",
        }

    if not active:
        return {
            "has_key": True, "online": online,
            "active_key": "—", "total_keys": total, "exhausted": exhausted,
            "model": _MODEL_PRIORITY[0],
            "status_text": "⏳ All keys cooling down",
            "status_color": "yellow",
        }

    if not online:
        return {
            "has_key": True, "online": False,
            "active_key": active[-6:], "total_keys": total, "exhausted": exhausted,
            "model": _MODEL_PRIORITY[0],
            "status_text": "📵 Offline",
            "status_color": "yellow",
        }

    color = "green" if exhausted < total else "yellow"
    available = total - exhausted
    if total > 1 and available > 0:
        status_text = f"🔁 Auto-switching ({available}/{total} keys)"
    else:
        status_text = f"✅ API Live ({available}/{total} keys)"
    return {
        "has_key": True, "online": True,
        "active_key": active[-6:], "total_keys": total, "exhausted": exhausted,
        "model": _MODEL_PRIORITY[0],
        "status_text": status_text,
        "status_color": color,
    }
