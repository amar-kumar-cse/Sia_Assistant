# 🔧 SIA ASSISTANT: PRACTICAL FIX GUIDE
**Implement These 6 Critical Fixes Today**

---

## FIX #1: Race Condition in Memory.py 🔴

### ❌ BEFORE (Buggy):
```python
# engine/memory.py - Lines 102-110
_memory_cache = None
_context_cache = None
_cache_timestamp = None

def load_memory() -> Dict[str, Any]:
    global _memory_cache, _cache_timestamp
    
    # ❌ BUG: Race condition here!
    if _memory_cache is not None and _cache_timestamp:
        if time.time() - _cache_timestamp < 5:
            return _memory_cache.copy()  # Shallow copy, still unsafe
```

### ✅ AFTER (Fixed):
```python
# engine/memory.py
import threading
import copy

_memory_cache = None
_context_cache = None
_cache_timestamp = None
_cache_lock = threading.Lock()  # ✅ Add lock

def load_memory() -> Dict[str, Any]:
    global _memory_cache, _cache_timestamp, _cache_lock
    
    with _cache_lock:  # ✅ Acquire lock
        # Now safe to read
        if _memory_cache is not None and _cache_timestamp:
            if time.time() - _cache_timestamp < 5:
                return copy.deepcopy(_memory_cache)  # ✅ Deep copy
    
    # ... rest of function
```

**Where to add**: Add `_cache_lock = threading.Lock()` near the top with other globals  
**Time to fix**: 5 minutes  

---

## FIX #2: SQLite Connection Leaks 🔴

### ❌ BEFORE (Buggy):
```python
# engine/memory.py - Lines 67-71
def _get_db() -> sqlite3.Connection:
    """Returns an active SQLite connection."""
    conn = sqlite3.connect(DB_PATH)  # ❌ No timeout, no cleanup guarantee
    conn.row_factory = sqlite3.Row
    return conn

# Then used like:
with _db_lock, _get_db() as conn:  # ❌ Can fail if exception in context
    # operations
```

### ✅ AFTER (Fixed):
```python
# engine/memory.py
def _get_db() -> sqlite3.Connection:
    """Returns an active SQLite connection with proper settings."""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=5.0,  # ✅ Wait max 5s for lock
        check_same_thread=False  # ✅ Allow multi-threaded use
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # ✅ WAL mode for concurrency
    conn.execute("PRAGMA synchronous=NORMAL")  # ✅ Better performance
    return conn

# Usage stays same but now safer
```

**Where to change**: `_get_db()` function in memory.py  
**Time to fix**: 3 minutes  

---

## FIX #3: Infinite Loop in Wake Word Detection 🔴

### ❌ BEFORE (Buggy):
```python
# engine/listen_engine.py - Lines 55-75
def _listen_loop(recognizer, source, wake_word, timeout_seconds=2, phrase_limit=3):
    print(f"👂 Waiting for '{wake_word}'...")
    try:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
    except Exception as e:
        logger.warning(f"⚠️ Noise adjustment failed: {e}")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while consecutive_errors < max_consecutive_errors:  # ❌ Infinite loop!
        try:
            audio = recognizer.listen(source, timeout=timeout_seconds, phrase_time_limit=phrase_limit)
            consecutive_errors = 0  # Reset only on success
            try:
                text = recognizer.recognize_google(audio).lower()
                # ... process text ...
            except sr.UnknownValueValue:
                pass
            except sr.RequestError:
                pass
        except sr.WaitTimeoutError:
            pass  # ❌ NEVER incremented! Infinite loop here
        except Exception as e:
            print(f"⚠️ Wake word error: {e}")
            pass  # ❌ NEVER incremented!
```

### ✅ AFTER (Fixed):
```python
# engine/listen_engine.py
def _listen_loop(recognizer, source, wake_word, timeout_seconds=2, phrase_limit=3):
    """Enhanced listening loop with proper error counting."""
    print(f"👂 Waiting for '{wake_word}'...")
    try:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
    except Exception as e:
        logger.warning(f"⚠️ Noise adjustment failed: {e}")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while consecutive_errors < max_consecutive_errors:
        try:
            audio = recognizer.listen(
                source, 
                timeout=timeout_seconds, 
                phrase_time_limit=phrase_limit
            )
            consecutive_errors = 0  # ✅ Reset on success
            
            try:
                text = recognizer.recognize_google(audio).lower()
                print(f"heard: {text}")
                wake_aliases = [wake_word.lower(), "siya", "see ya", "shia", "sya", "cia", "shea"]
                if any(alias in text for alias in wake_aliases):
                    print("⚡ Wake word detected!")
                    return True
                    
            except sr.UnknownValueError:
                consecutive_errors += 1  # ✅ Count as error
                logger.debug(f"Unclear audio, retry {consecutive_errors}/{max_consecutive_errors}")
                
            except sr.RequestError as req_e:
                consecutive_errors += 1  # ✅ Count as error
                logger.warning(f"Google API error: {req_e}, retry {consecutive_errors}/{max_consecutive_errors}")
                
        except sr.WaitTimeoutError:
            consecutive_errors += 1  # ✅ COUNT TIMEOUT AS ERROR!
            logger.debug(f"Timeout waiting for speech, retry {consecutive_errors}/{max_consecutive_errors}")
            
        except Exception as e:
            consecutive_errors += 1  # ✅ COUNT ALL ERRORS!
            logger.error(f"Wake word loop error: {e}, retry {consecutive_errors}/{max_consecutive_errors}")
    
    logger.warning(f"Max consecutive errors ({max_consecutive_errors}) reached in wake word detection")
    return False  # ✅ Exit loop gracefully
```

**Where to change**: `_listen_loop()` function in engine/listen_engine.py  
**Time to fix**: 10 minutes  

---

## FIX #4: Global State Race Conditions in Voice Engine 🔴

### ❌ BEFORE (Buggy):
```python
# engine/voice_engine.py - Lines 50-63
_speaking_lock = threading.Lock()
is_speaking = False  # ❌ Global, non-atomic
is_streaming = False
speech_start_time = None
speech_duration = 0

def _set_speaking_state(state: bool):
    """Thread-safe setter for is_speaking global state."""
    global is_speaking
    with _speaking_lock:
        is_speaking = state

def _get_speaking_state() -> bool:
    """Thread-safe getter for is_speaking global state."""
    global is_speaking
    with _speaking_lock:
        return is_speaking

# BUT used incorrectly:
def speak(text, emotion=None, ...):
    _set_speaking_state(True)
    speech_start_time = time.time()  # ❌ Not protected
    speech_duration = 0  # ❌ Not protected
    
    # ... then later ...
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # ❌ is_speaking could change mid-loop
    
    speech_duration = time.time() - speech_start_time  # ❌ Race condition
```

### ✅ AFTER (Fixed):
```python
# engine/voice_engine.py
import threading
import time
from typing import Optional

class VoiceState:
    """Thread-safe voice state management."""
    
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

# Replace these functions:
def _set_speaking_state(state: bool):
    """✅ Now properly thread-safe."""
    _voice_state.set_speaking(state)

def _get_speaking_state() -> bool:
    """✅ Now properly thread-safe."""
    return _voice_state.get_speaking()

# Updated speak function:
def speak(text: str, emotion: Optional[str] = None, 
          callback_started: Optional[Callable[[], None]] = None,
          callback_finished: Optional[Callable[[], None]] = None) -> None:
    """Synthesizes speech and plays it."""
    # ... existing code ...
    
    _voice_state.set_speaking(True)  # ✅ Atomic operation
    if callback_started:
        callback_started()
    
    try:
        pygame.mixer.music.load(cache_path)
        pygame.mixer.music.play()
        
        # ✅ Safe loop - use atomic getter
        while _voice_state.get_speaking() and pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
    finally:
        _voice_state.set_speaking(False)  # ✅ Atomic operation
        if callback_finished:
            callback_finished()
```

**Where to add**: Create new `VoiceState` class at top of voice_engine.py, replace global variables  
**Time to fix**: 15 minutes  

---

## FIX #5: Input Validation in Desktop UI 🔴

### ❌ BEFORE (Buggy):
```python
# sia_desktop.py - Lines 200+
class ListenThread(QThread):
    text_recognized  = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_failed  = pyqtSignal()

    def run(self):
        self.listening_started.emit()
        text = listen_engine.listen()  # ❌ No validation!
        if text:
            self.text_recognized.emit(text)  # ❌ Could be anything!
        else:
            self.listening_failed.emit()

# Then brain receives it directly:
def on_text_recognized(self, text):  # No sanitization!
    from engine import brain
    response = brain.think(text)
```

### ✅ AFTER (Fixed):
```python
# sia_desktop.py
from engine.validation import sanitize_input
from engine.logger import get_logger

logger = get_logger("ListenThread")

class ListenThread(QThread):
    text_recognized  = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_failed  = pyqtSignal()

    def run(self):
        try:
            self.listening_started.emit()
            
            # ✅ Get raw text
            text = listen_engine.listen()
            
            if not text:  # ✅ Check for None/empty
                self.listening_failed.emit()
                return
            
            # ✅ Sanitize input
            try:
                sanitized_text = sanitize_input(text, max_length=500)
            except ValueError as e:
                logger.error(f"Input validation failed: {e}")
                self.listening_failed.emit()
                return
            
            if not sanitized_text:  # ✅ Empty after sanitization
                logger.warning(f"Text '{text[:50]}' was empty after sanitization")
                self.listening_failed.emit()
                return
            
            # ✅ Now emit safe text
            self.text_recognized.emit(sanitized_text)
            
        except PermissionError:
            logger.error("Microphone permission denied")
            self.listening_failed.emit()
        except Exception as e:
            logger.error(f"Listen thread error: {e}", exc_info=True)
            self.listening_failed.emit()

# Update receiver:
def on_text_recognized(self, text: str):
    """Called when user speech is recognized and validated."""
    try:
        # ✅ Text is already sanitized by ListenThread
        from engine import brain
        response = brain.think(text)
        
        if not response:
            response = "[CONFUSED] Sorry, kuch samajh nahi aaya"
        
        self.on_response_ready(response)
        
    except Exception as e:
        logger.error(f"Think operation failed: {e}", exc_info=True)
        self.on_response_ready("[CONFUSED] Arre, error ho gayi bhai!")
```

**Where to change**: `ListenThread.run()` in sia_desktop.py + receiver function  
**Time to fix**: 10 minutes  

---

## FIX #6: Resource Leaks in Streaming Manager 🔴

### ❌ BEFORE (Buggy):
```python
# engine/streaming_manager.py - Lines 38-50
def process_stream(self, text_generator: Generator, voice_callback: Callable):
    self.is_streaming = True
    self.should_stop = False
    
    # ❌ Daemon threads - no cleanup guarantee
    text_thread = threading.Thread(
        target=self._text_collector_thread,
        args=(text_generator,),
        daemon=True  # ❌ Problem!
    )
    
    voice_thread = threading.Thread(
        target=self._voice_synthesis_thread,
        args=(voice_callback,),
        daemon=True  # ❌ Problem!
    )
    
    text_thread.start()
    voice_thread.start()
    
    # ❌ No timeout - can hang forever!
    text_thread.join()
    voice_thread.join()
    
    self.is_streaming = False
```

### ✅ AFTER (Fixed):
```python
# engine/streaming_manager.py
import threading
import logging

logger = logging.getLogger(__name__)

class StreamingManager:
    """Coordinates streaming from Gemini to ElevenLabs for instant responses."""
    
    def __init__(self):
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        self.is_streaming = False
        self.is_speaking = False
        self.should_stop = False
        
        self.on_chunk_received = None
        self.on_speaking_start = None
        self.on_speaking_end = None
        
        self.min_chunk_length = 20
        self.sentence_endings = r'[.!?।]'
        
        # ✅ Track threads
        self._text_thread: Optional[threading.Thread] = None
        self._voice_thread: Optional[threading.Thread] = None
    
    def process_stream(
        self, 
        text_generator: Generator, 
        voice_callback: Callable,
        timeout_seconds: int = 120  # ✅ Add timeout
    ) -> bool:
        """
        Main streaming pipeline coordinator.
        
        Args:
            text_generator: Generator yielding text chunks from Gemini
            voice_callback: Function to call with complete sentences for TTS
            timeout_seconds: Max time to allow for streaming
            
        Returns:
            True if completed successfully, False if timeout/error
        """
        self.is_streaming = True
        self.should_stop = False
        success = False
        
        try:
            # ✅ Create non-daemon threads for proper cleanup
            self._text_thread = threading.Thread(
                target=self._text_collector_thread,
                args=(text_generator,),
                name="StreamTextCollector",
                daemon=False  # ✅ Non-daemon
            )
            
            self._voice_thread = threading.Thread(
                target=self._voice_synthesis_thread,
                args=(voice_callback,),
                name="StreamVoiceSynthesis",
                daemon=False  # ✅ Non-daemon
            )
            
            self._text_thread.start()
            self._voice_thread.start()
            
            # ✅ Join with timeout
            logger.info(f"Starting stream processing (timeout={timeout_seconds}s)")
            
            self._text_thread.join(timeout=timeout_seconds)
            self._voice_thread.join(timeout=timeout_seconds)
            
            # ✅ Check if threads completed
            if self._text_thread.is_alive() or self._voice_thread.is_alive():
                logger.error("Stream threads did not complete within timeout")
                self.should_stop = True
                
                # ✅ Force cleanup
                self._text_thread.join(timeout=5)
                self._voice_thread.join(timeout=5)
                
                if self._text_thread.is_alive() or self._voice_thread.is_alive():
                    logger.error("Threads still alive after cleanup - possible deadlock")
                    return False
            else:
                success = True
                logger.info("Stream processing completed successfully")
            
        except Exception as e:
            logger.error(f"Stream processing error: {e}", exc_info=True)
            self.should_stop = True
        
        finally:
            self.is_streaming = False
            # ✅ Clear references
            self._text_thread = None
            self._voice_thread = None
            
            return success
    
    def stop_streaming(self) -> None:
        """Force stop streaming with cleanup."""
        logger.info("Stopping stream processing")
        self.should_stop = True
        
        # ✅ Wait for threads to finish
        if self._text_thread and self._text_thread.is_alive():
            self._text_thread.join(timeout=5)
        
        if self._voice_thread and self._voice_thread.is_alive():
            self._voice_thread.join(timeout=5)
        
        self.is_streaming = False
```

**Where to change**: Entire `process_stream()` method in streaming_manager.py  
**Time to fix**: 20 minutes  

---

## 🎯 APPLY THESE FIXES NOW

```bash
# Step 1: Backup current files
git add .
git commit -m "Checkpoint before critical fixes"

# Step 2: Apply fixes in this order:
# 1. memory.py races - _cache_lock and deepcopy
# 2. listen_engine.py - increment errors 
# 3. voice_engine.py - VoiceState class
# 4. sia_desktop.py - input validation
# 5. streaming_manager.py - timeouts and cleanup

# Step 3: Test each fix
python test_bug_fixes.py

# Step 4: Commit fixes
git commit -m "Fix: 6 critical issues (races, leaks, validation)"
```

---

## ✅ VERIFICATION CHECKLIST

- [ ] Memory cache is thread-safe with deep copy
- [ ] SQLite connections don't leak with WAL mode
- [ ] Wake word loop exits after max errors
- [ ] Voice state is atomic with VoiceState class
- [ ] Input text is sanitized before processing
- [ ] Streaming threads complete with timeout
- [ ] No infinite loops or hangs
- [ ] Error messages are consistent
- [ ] Logs show all critical paths

---

**Status**: All 6 fixes ready to apply  
**Total Implementation Time**: ~75 minutes  
**Complexity**: Medium  
**Risk**: Low (fixes are well-isolated)
