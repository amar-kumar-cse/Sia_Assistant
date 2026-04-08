import os
import requests
import pygame
import io
import time
from dotenv import load_dotenv
import tempfile
import subprocess
import hashlib
import sys
import threading
import math
import random
from typing import Optional, Callable, Dict
from .logger import get_logger

logger = get_logger(__name__)

# Track the active edge-tts subprocess so we can kill it on interrupt
_active_subprocess = None
_active_subprocess_lock = threading.Lock()

# Get config with error handling
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

CACHE_DIR = None
try:
    import config
    CACHE_DIR = config.config.CACHE_DIR
except ImportError as e:
    print(f"⚠️ Config import failed: {e}")
    CACHE_DIR = os.path.join(BASE_DIR, "cache")
    os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize pygame with enhanced error handling
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    logger.info("✅ Pygame mixer initialized with enhanced settings")
except pygame.error as e:
    logger.error(f"❌ Pygame init failed: {e}")
    # Create enhanced dummy mixer with better fallback
    class EnhancedDummyMixer:
        def __init__(self):
            self._playing = False
        def get_busy(self):
            return self._playing
        def load(self, *args):
            return self
        def play(self, *args):
            self._playing = True
            logger.warning("⚠️ Using dummy audio playback")
            return self
        def stop(self, *args):
            self._playing = False
        def music(self):
            return self
    pygame.mixer = EnhancedDummyMixer()
    pygame.time.Clock = lambda: type('obj', (object,), {'tick': lambda x: None})()

# Load environment variables
load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
MODEL_ID = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2")

# ✅ FIX #4: Thread-safe voice state management
class VoiceState:
    """Atomic voice state management for thread-safe operations."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._is_streaming = False
        self._start_time: Optional[float] = None
        self._duration = 0.0
    
    def set_speaking(self, state: bool) -> None:
        """Set speaking state atomically."""
        with self._lock:
            self._is_speaking = state
            if state:
                self._start_time = time.time()
            else:
                if self._start_time:
                    self._duration = time.time() - self._start_time
    
    def get_speaking(self) -> bool:
        """Get speaking state atomically."""
        with self._lock:
            return self._is_speaking
    
    def get_duration(self) -> float:
        """Get current speech duration."""
        with self._lock:
            if self._is_speaking and self._start_time:
                return time.time() - self._start_time
            return self._duration
    
    def set_streaming(self, state: bool) -> None:
        """Set streaming state atomically."""
        with self._lock:
            self._is_streaming = state
    
    def get_streaming(self) -> bool:
        """Get streaming state atomically."""
        with self._lock:
            return self._is_streaming

# Create global instance
_voice_state = VoiceState()

# ✅ FIX #4: Keep old API for backward compatibility
def _set_speaking_state(state: bool):
    """Thread-safe setter for is_speaking global state."""
    _voice_state.set_speaking(state)

def _get_speaking_state() -> bool:
    """Thread-safe getter for is_speaking global state."""
    return _voice_state.get_speaking()

# ━━━━━━ Emotion-Adaptive Voice Settings ━━━━━━
# Uses Microsoft Edge TTS for natural, human-like voice
# hi-IN-SwaraNeural = female Hindi voice (most natural sounding)
# Optimized rate/pitch for each emotion to sound like a real person
EMOTION_VOICE_MAP = {
    "IDLE":      {"rate": "+0%",   "pitch": "+5Hz",   "voice": "hi-IN-SwaraNeural"},
    "SMILE":     {"rate": "+3%",   "pitch": "+15Hz",  "voice": "hi-IN-SwaraNeural"},
    "HAPPY":     {"rate": "+8%",   "pitch": "+25Hz",  "voice": "hi-IN-SwaraNeural"},
    "EXCITED":   {"rate": "+12%",  "pitch": "+35Hz",  "voice": "hi-IN-SwaraNeural"},
    "SAD":       {"rate": "-8%",   "pitch": "-15Hz",  "voice": "hi-IN-SwaraNeural"},
    "CONFUSED":  {"rate": "-3%",   "pitch": "+8Hz",   "voice": "hi-IN-SwaraNeural"},
    "SURPRISED": {"rate": "+8%",   "pitch": "+40Hz",  "voice": "hi-IN-SwaraNeural"},
    "ANGRY":     {"rate": "+3%",   "pitch": "-8Hz",   "voice": "hi-IN-SwaraNeural"},
    "STRESSED":  {"rate": "-3%",   "pitch": "-3Hz",   "voice": "hi-IN-SwaraNeural"},
}

def _get_emotion_settings(emotion: Optional[str]) -> Dict[str, str]:
    """Get voice settings for the given emotion."""
    emotion = (emotion or "IDLE").upper().strip()
    return EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP["IDLE"])

def speak(text: str, emotion: Optional[str] = None, callback_started: Optional[Callable[[], None]] = None, callback_finished: Optional[Callable[[], None]] = None) -> None:
    """
    Synthesize speech and play audio with emotion-aware voice settings.
    
    Pipeline: Check cache → Select TTS engine → Generate audio → Play with callbacks
    
    Args:
        text: Speech text to synthesize
        emotion: Emotional tone (happy, sad, angry, confused, etc.)
        callback_started: Called when playback starts
        callback_finished: Called when playback finishes
        
    Returns:
        None
        
    Note:
        - Caches synthesized audio to avoid redundant API calls
        - Falls back: ElevenLabs → Edge-TTS → Offline
        - Thread-safe via VoiceState class
        - Non-blocking with optional callbacks
    """
    emo_settings = _get_emotion_settings(emotion)
    
    # Generate Cache Key based on text and emotion
    raw_key = f"{text}_{emo_settings['voice']}_{emo_settings['rate']}_{emo_settings['pitch']}"
    text_hash = hashlib.md5(raw_key.encode('utf-8')).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{text_hash}.mp3")
    
    # Check Cache First
    if os.path.exists(cache_path):
        _voice_state.set_speaking(True)
        if callback_started: callback_started()
        
        try:
            pygame.mixer.music.load(cache_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"Cache play error: {e}")
            
        _voice_state.set_speaking(False)
        if callback_finished: callback_finished()
        return

    # Decide on TTS Engine
    use_edge_tts = False
    if not ELEVENLABS_API_KEY or "your_elevenlabs_api_key" in ELEVENLABS_API_KEY:
        use_edge_tts = True
    elif len(text) < 50:
        use_edge_tts = True
        print(f"[Offline TTS Optimized]: Short response ({len(text)} chars)")

    # No Cache - Generate using Fallback or ElevenLabs
    if use_edge_tts:
        _use_edge_tts_fallback(text, emo_settings, cache_path, callback_started, callback_finished)
        return

    # ElevenLabs Generation
    # Rate limiting
    try:
        try:
            from .rate_limiter import voice_limiter
        except ImportError:
            from rate_limiter import voice_limiter
        if not voice_limiter.is_allowed("elevenlabs"):
            logger.warning("Voice API rate limit exceeded. Falling back to Edge-TTS.")
            _use_edge_tts_fallback(text, emo_settings, cache_path, callback_started, callback_finished)
            return
    except ImportError:
        logger.warning("Rate limiter not available")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Save to Cache
            with open(cache_path, "wb") as f:
                f.write(response.content)
                
            _voice_state.set_speaking(True)
            if callback_started: callback_started()
            
            pygame.mixer.music.load(cache_path)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            _voice_state.set_speaking(False)
            if callback_finished: callback_finished()
                
        else:
            print(f"⚠️ ElevenLabs Error [{response.status_code}]: {response.text}")
            print("🔄 Falling back to Edge-TTS...")
            _use_edge_tts_fallback(text, emo_settings, cache_path, callback_started, callback_finished)
            
    except Exception as e:
        print(f"❌ Voice generation failed with ElevenLabs: {e}")
        print("🔄 Falling back to Edge-TTS...")
        _use_edge_tts_fallback(text, emo_settings, cache_path, callback_started, callback_finished)


def _use_pyttsx3_last_resort(text: str, callback_started=None, callback_finished=None) -> None:
    """
    100% offline, no-internet TTS using pyttsx3.
    Last resort when both ElevenLabs and Edge-TTS fail.
    Works instantly — no subprocess, no network.
    
    ⚠️ On Windows with threading: Properly initializes COM to avoid CoInitialize errors.
    """
    try:
        import pyttsx3
        
        # Windows COM initialization for threaded environments
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.ole32.CoInitializeEx(None, 0)
                logger.info("✅ Windows COM initialized for pyttsx3")
            except Exception as e:
                logger.warning("⚠️ COM initialization attempt: %s (may still work)", e)
        
        engine = pyttsx3.init()
        
        # Try to find a Hindi or natural-sounding voice
        voices = engine.getProperty('voices')
        chosen = None
        for v in voices:
            name_lower = v.name.lower()
            if any(k in name_lower for k in ('hindi', 'zira', 'hazel', 'helen')):
                chosen = v.id
                break
        
        if chosen:
            engine.setProperty('voice', chosen)
        
        engine.setProperty('rate', 155)     # Comfortable speaking pace
        engine.setProperty('volume', 0.92)
        
        _set_speaking_state(True)
        if callback_started:
            callback_started()
        
        engine.say(text)
        engine.runAndWait()
        
    except ImportError:
        logger.error("[Sia pyttsx3]: Not installed. Run: pip install pyttsx3")
        print("[Sia pyttsx3]: Not installed. Run: pip install pyttsx3")
    except Exception as e:
        logger.error("[Sia pyttsx3]: Last-resort TTS failed: %s", e)
        print(f"[Sia pyttsx3]: Last-resort TTS failed: {e}")
    finally:
        _set_speaking_state(False)
        if callback_finished:
            callback_finished()


def _use_edge_tts_fallback(text, emo_settings, cache_path, callback_started, callback_finished):
    """
    Fallback to edge-tts with network resilience.
    Handles slow internet, quota exhaustion, and subprocess timeouts gracefully.
    If edge-tts fails → pyttsx3 last resort.
    """
    print(f"[Sia (Edge-TTS) Fallback]: {text[:50]}...")
    logger.info("Attempting Edge-TTS for text: %s...", text[:50])
    
    _set_speaking_state(True)
    if callback_started:
        callback_started()

    edge_tts_ok = False
    retry_count = 0
    max_retries = 2  # Retry up to 2 times for network issues
    
    while retry_count <= max_retries and not edge_tts_ok:
        try:
            voice = emo_settings["voice"]
            rate = emo_settings["rate"]
            pitch = emo_settings["pitch"]
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

            # Add internet check before attempting edge-tts
            try:
                import socket
                socket.setdefaulttimeout(2)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
                logger.info("✅ Internet connectivity confirmed for Edge-TTS")
            except (socket.error, OSError):
                logger.warning("⚠️ Internet unavailable - Edge-TTS will likely fail")

            logger.debug("Running edge-tts: voice=%s rate=%s pitch=%s", voice, rate, pitch)
            
            # Run edge-tts with proper timeout handling
            global _active_subprocess
            process = subprocess.Popen(
                ["edge-tts", "--voice", voice,
                 "--rate", rate, "--pitch", pitch,
                 "--text", text, "--write-media", cache_path],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            with _active_subprocess_lock:
                _active_subprocess = process
            
            try:
                stdout, stderr = process.communicate(timeout=30)
                
                if process.returncode != 0:
                    logger.error("Edge-TTS failed with return code %d: %s", process.returncode, stderr.decode()[:200])
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.info("🔄 Retrying Edge-TTS (attempt %d/%d)...", retry_count, max_retries)
                        time.sleep(1)  # Brief delay before retry
                        continue
                    else:
                        raise RuntimeError(f"Edge-TTS failed: {stderr.decode()[:100]}")
                
                # Verify cache file was created
                if not os.path.exists(cache_path):
                    logger.error("Edge-TTS didn't create cache file: %s", cache_path)
                    raise RuntimeError("Cache file not created by Edge-TTS")
                
                # Try to play the audio
                logger.info("✅ Edge-TTS succeeded, loading audio from %s", cache_path)
                pygame.mixer.music.load(cache_path)
                pygame.mixer.music.play()
                
                # Wait for playback
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                edge_tts_ok = True
                logger.info("✅ Audio playback completed successfully")
                
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning("⏱️ Edge-TTS timed out after 30s (likely network or quota issue)")
                if retry_count < max_retries:
                    retry_count += 1
                    logger.info("🔄 Retrying after timeout (attempt %d/%d)...", retry_count, max_retries)
                    time.sleep(2)  # Longer delay after timeout
                    continue
                else:
                    raise RuntimeError("Edge-TTS timed out multiple times")

        except FileNotFoundError:
            logger.error("edge-tts command not found - is it installed? pip install edge-tts")
            print("[Sia]: edge-tts not found. Install: pip install edge-tts")
            break
        except subprocess.CalledProcessError as e:
            logger.error("Edge-TTS CalledProcessError: %s", e)
            if retry_count < max_retries:
                retry_count += 1
                logger.info("🔄 Retrying after process error (attempt %d/%d)...", retry_count, max_retries)
                time.sleep(1)
                continue
            break
        except Exception as e:
            logger.error("Edge-TTS unexpected error: %s", str(e)[:200])
            if "quota" in str(e).lower() or "429" in str(e).lower():
                logger.warning("⚠️ API Quota/Rate limit detected - Edge-TTS skipping further retries")
                break  # Don't retry on quota errors
            if retry_count < max_retries:
                retry_count += 1
                logger.info("🔄 Retrying after error (attempt %d/%d)...", retry_count, max_retries)
                time.sleep(1)
                continue
            break

    _set_speaking_state(False)
    if callback_finished:
        callback_finished()

    # If edge-tts failed → pyttsx3 last resort (re-triggers callbacks)
    if not edge_tts_ok:
        logger.warning("❌ Edge-TTS exhausted. Falling back to pyttsx3...")
        print("[Sia]: Edge-TTS failed — switching to offline pyttsx3...")
        _use_pyttsx3_last_resort(text, callback_started, callback_finished)


def stop() -> None:
    """Stops any currently playing audio AND kills any pending edge-tts subprocess."""
    global _active_subprocess
    
    # Kill edge-tts process if running
    with _active_subprocess_lock:
        if _active_subprocess and _active_subprocess.poll() is None:
            try:
                _active_subprocess.kill()
                logger.info("[Voice Interrupt] edge-tts process killed.")
            except Exception as e:
                logger.warning(f"[Voice Interrupt] subprocess kill failed: {e}")
        _active_subprocess = None
    
    # Stop Pygame mixer immediately
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass
    
    _set_speaking_state(False)
    _voice_state.set_streaming(False)

def get_speaking_state() -> bool:
    """Returns current speaking state."""
    return _get_speaking_state()


def get_audio_frequency() -> float:
    """
    Returns a pseudo-audio frequency/RMS value (0.0 to 1.0) 
    representing the current voice amplitude.
    Since pygame.mixer.music streams decoded MP3 directly to the soundcard,
    we use a high-frequency time-based composite wave to simulate speech energy
    when the engine is actively speaking.
    """
    if not _get_speaking_state():
        return 0.0
    
    # Rapidly fluctuating value based on time to simulate phoneme energy
    t = time.time() * 12.0  # syllable pacing
    # composite wave imitating speech bursts
    energy = (math.sin(t) + math.sin(t * 2.3) + math.sin(t * 3.7)) / 3.0
    # Normalize 0 to 1 with some randomness
    energy = max(0.0, energy * 0.5 + 0.5)
    return energy * random.uniform(0.6, 1.0)

def estimate_speech_duration(text: str) -> float:
    """
    Estimates speech duration based on text length.
    Average speaking rate: ~150 words per minute = 2.5 words per second
    """
    word_count = len(text.split())
    estimated_duration = (word_count / 2.5)  # seconds
    return estimated_duration


def speak_chunk(text_chunk: str, is_first_chunk: bool = False) -> None:
    """
    Speak a text chunk with minimal latency.
    Optimized for streaming - starts playing immediately.
    
    Args:
        text_chunk: Short text segment to speak
        is_first_chunk: If True, sets speaking state
    """
    
    if not ELEVENLABS_API_KEY or "your_elevenlabs_api_key" in ELEVENLABS_API_KEY:
        print(f"[Sia Chunk (Fallback)]: {text_chunk}")
        try:
             temp_file = os.path.join(tempfile.gettempdir(), "sia_chunk.mp3")
             CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
             subprocess.run(
                 ["edge-tts", "--voice", "hi-IN-SwaraNeural",
                  "--text", text_chunk, "--write-media", temp_file],
                 check=True, creationflags=CREATE_NO_WINDOW, timeout=30
             )
             pygame.mixer.music.load(temp_file)
             pygame.mixer.music.play()
             while pygame.mixer.music.get_busy():
                 pygame.time.Clock().tick(10)
        except Exception as e:
            pass
        return

    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # Optimized settings for speed
    data = {
        "text": text_chunk,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.3,  # Lower for faster streaming
            "similarity_boost": 0.6,
            "optimize_streaming_latency": 4,  # Max optimization
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        
        if response.status_code == 200:
            audio_data = io.BytesIO(response.content)
            
            # Set speaking state on first chunk
            if is_first_chunk:
                _set_speaking_state(True)
                _voice_state.set_streaming(True)
            
            # Play immediately
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            
            # Wait for this chunk to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        else:
            print(f"⚠️ Chunk synthesis failed [{response.status_code}]")
            
    except Exception as e:
        print(f"❌ Chunk error: {e}")


def finish_streaming() -> None:
    """Call this when streaming is complete."""
    _set_speaking_state(False)
    _voice_state.set_streaming(False)


def speak_async(text: str, on_start: Optional[Callable[[], None]] = None, on_finish: Optional[Callable[[], None]] = None) -> None:
    """Non-blocking speech synthesis. Runs in a background thread."""
    import threading
    def _run():
        if on_start:
            on_start()
        speak(text)
        if on_finish:
            on_finish()
    threading.Thread(target=_run, daemon=True).start()
