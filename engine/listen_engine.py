import speech_recognition as sr
import sys
import time
from typing import Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Check if speech recognition is available
try:
    sr.Recognizer
except AttributeError:
    print("❌ SpeechRecognition library not properly installed")
    print("Install with: pip install SpeechRecognition pyaudio")

# ✅ ENHANCED: Retry configuration for robustness
MAX_RECOGNITION_RETRIES = 3
RETRY_DELAY = 0.5  # seconds
    
def listen_for_wake_word(wake_word="sia", source=None, max_retries=3):
    """
    Continuously listens for the wake word 'Sia' with retry mechanism.
    Returns True when wake word is detected.
    
    Args:
        wake_word: The word to detect (default: "sia")
        source: Microphone source (optional)
        max_retries: Number of retries on failure (default: 3)
    """
    recognizer = sr.Recognizer()
    # ✅ CRITICAL FIX: Restored standard threshold to prevent noise-loops
    recognizer.energy_threshold = 300  # Default 300 is best for general use
    recognizer.pause_threshold = 0.6  # Slightly longer pause
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.10  # More responsive
    
    # If source is not provided, open a new one
    context_manager = source if source else sr.Microphone()
    
    # If we created the context manager, we need to enter it
    if source is None:
        retry_count = 0
        while retry_count < max_retries:
            try:
                with context_manager as src:
                    return _listen_loop(recognizer, src, wake_word)
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Microphone access error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    print(f"⏳ Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("💡 Tip: Check microphone permissions or connect a microphone")
                    return False
    else:
        return _listen_loop(recognizer, source, wake_word)

def _listen_loop(recognizer, source, wake_word, timeout_seconds=2, phrase_limit=3):
    """Enhanced listening loop with better error handling."""
    print(f"👂 Waiting for '{wake_word}'...")
    try:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
    except Exception as e:
        logger.warning(f"⚠️ Noise adjustment failed: {e}")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while consecutive_errors < max_consecutive_errors:
        try:
            audio = recognizer.listen(source, timeout=timeout_seconds, phrase_time_limit=phrase_limit)
            consecutive_errors = 0  # Reset on successful audio capture
            try:
                # Use faster/lower accuracy model for wake word if possible, 
                # but Google is fine for now.
                text = recognizer.recognize_google(audio).lower()
                print(f"heard: {text}")
                wake_aliases = [wake_word.lower(), "siya", "see ya", "shia", "sya", "cia", "shea"]
                if any(alias in text for alias in wake_aliases):
                    print("⚡ Wake word detected!")
                    return True
            except sr.UnknownValueError:
                # ✅ FIX #3: Increment error counter
                consecutive_errors += 1
                logger.debug(f"Unclear audio, retry {consecutive_errors}/{max_consecutive_errors}")
            except sr.RequestError as req_e:
                # ✅ FIX #3: Increment error counter
                consecutive_errors += 1
                logger.warning(f"Google API error: {req_e}, retry {consecutive_errors}/{max_consecutive_errors}")
        except sr.WaitTimeoutError:
            # ✅ FIX #3: THIS WAS THE BUG - timeout was never counted!
            consecutive_errors += 1
            logger.debug(f"Timeout waiting for speech, retry {consecutive_errors}/{max_consecutive_errors}")
        except Exception as e:
            # ✅ FIX #3: Count all other errors too
            consecutive_errors += 1
            logger.error(f"Wake word loop error: {e}, retry {consecutive_errors}/{max_consecutive_errors}")
    
    # ✅ FIX #3: Exit loop gracefully instead of infinite loop
    logger.warning(f"Max consecutive errors ({max_consecutive_errors}) reached in wake word detection")
    return False

def listen(use_whisper=False, max_retries=MAX_RECOGNITION_RETRIES):
    """
    Listens to the microphone with enhanced error handling and retry logic.
    
    Args:
        use_whisper (bool): Default False (Google STT is faster)
        max_retries (int): Number of retries on failure
        
    Returns:
        str or None: Recognized text or None if failed
    """
    recognizer = sr.Recognizer()
    
    # ✅ ENHANCED: Optimized microphone settings for sensitivity but rejecting raw noise
    recognizer.energy_threshold = 300  # Standard (300) to prevent looping on PC fan noise
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.05
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.2
    recognizer.non_speaking_duration = 0.3
    
    for attempt in range(max_retries):
        try:
            with sr.Microphone() as source:
                logger.debug(f"🎤 Listening... (attempt {attempt + 1}/{max_retries})")
                print("🎤 Listening...")
                
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    logger.warning(f"⏱️ Timeout: No speech detected (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    return None
        except Exception as e:
            logger.error(f"❌ Microphone error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("⏳ Retrying...")
                time.sleep(RETRY_DELAY)
                continue
            print("💡 Tip: Check if microphone is connected and not in use by another app")
            return None

        try:
            logger.debug("⚡ Recognizing audio...")
            print("⚡ Recognizing...")
            if use_whisper:
                try:
                    logger.debug("🧠 Using local Whisper model...")
                    print("🧠 Using local Whisper model...")
                    text = recognizer.recognize_whisper(audio, model="base")
                except Exception as whisper_err:
                    logger.warning(f"⚠️ Whisper failed: {whisper_err}. Falling back to Google...")
                    print("⚠️ Falling back to Google Speech Recognition...")
                    text = recognizer.recognize_google(audio)
            else:
                text = recognizer.recognize_google(audio)
            
            logger.info(f"✅ Heard: {text}")
            print(f"✅ Heard: {text}")
            return text
        except sr.UnknownValueError:
            logger.warning(f"❌ Could not understand audio (attempt {attempt + 1}/{max_retries})")
            print("❌ Could not understand audio")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None
        except sr.RequestError as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                logger.error(f"⚠️  Google STT quota exhausted (attempt {attempt + 1}): {e}")
                print("⚠️  Google STT limit hit — will retry after short wait")
                time.sleep(5)
            elif "connection" in err_str or "network" in err_str:
                logger.error(f"❌ Network error for STT (attempt {attempt + 1}): {e}")
                print("❌ Internet connection problem — check your Wi-Fi")
            else:
                logger.error(f"❌ STT recognition service error (attempt {attempt + 1}): {e}")
                print(f"❌ Recognition error: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
            print(f"❌ Speech recognition failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None
    
    logger.error(f"❌ All {max_retries} attempts failed")
    return None


def listen_with_vad():
    """
    Advanced listening with Voice Activity Detection.
    Experimental - requires webrtcvad library.
    """
    try:
        import webrtcvad
    except ImportError:
        print("⚠️ webrtcvad not installed. Using standard listen().")
        return listen()
    
    recognizer = sr.Recognizer()
    vad = webrtcvad.Vad(2)  # Aggressiveness 2 (0-3, higher = more aggressive)
    
    # Even more sensitive settings for VAD mode
    recognizer.energy_threshold = 300  # Using standard to avoid false VAD triggers
    recognizer.pause_threshold = 0.5  # Slightly longer to capture complete phrases
    
    try:
        with sr.Microphone(sample_rate=16000) as source:
            print("🎤 VAD Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            
            try:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                return None
    except Exception as e:
        print(f"❌ VAD Microphone error: {e}")
        return None
    
    try:
        text = recognizer.recognize_google(audio)
        print(f"✅ VAD Heard: {text}")
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"❌ VAD error: {e}")
        return None

