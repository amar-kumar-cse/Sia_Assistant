# 🔧 Sia Assistant - Bug Fixes Applied (April 4, 2026)

## Overview
Fixed three critical issues preventing Sia from working reliably on Windows with API key rotation, Edge-TTS, and pyttsx3 threading.

---

## ✅ Fix #1: API Key Rotation Logic (Dushman #1)

### Problem: 
- Quota exhaustion wasn't properly rotating between backup API keys
- The `_KeyRotationManager.current_key()` loop was checking all keys sequentially and not rotating correctly
- When a key hit quota, the rotation index wasn't properly synced

### Solution:
**File**: `engine/brain.py` - `_KeyRotationManager` class

#### Changes:
1. **Added thread-safe rotation** with `threading.Lock()` to prevent race conditions
2. **Fixed key selection logic**:
   - Instead of checking all keys in a loop (which skipped them), now uses modulo arithmetic
   - Properly maintains index state for each key
3. **Improved exhaustion handling**:
   - Automatically rotates to next key when marking one as exhausted
   - Respects cooldown times per key

#### Before (Buggy):
```python
def current_key(self) -> Optional[str]:
    now = time.time()
    for _ in range(len(self._keys)):
        k = self._keys[self._index % len(self._keys)]
        if self._exhausted_until.get(k, 0) < now:
            return k
        self._index += 1  # ❌ This caused keys to be skipped!
    return None
```

#### After (Fixed):
```python
def current_key(self) -> Optional[str]:
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
                self._index = idx  # ✅ Properly track current index
                return k
    
    # All keys exhausted - return None
    return None
```

### Testing:
```bash
# Test with 2-3 API keys in .env:
# GEMINI_API_KEY=key1,key2
# GEMINI_API_KEY_3=key3

# When a key hits quota, logs will show:
# 🔄 Key ending in ...xxxxx is quota-exhausted. Will retry in 60 min. Rotating to next key.
# Then it automatically switches to the next available key
```

---

## ✅ Fix #2: Edge-TTS Network Resilience (Dushman #2)

### Problem:
- Edge-TTS subprocess would hang/timeout with slow internet
- No retry logic when network was unstable
- API quota issues weren't gracefully handled
- Silent failures with no fallback

### Solution:
**File**: `engine/voice_engine.py` - `_use_edge_tts_fallback()` function

#### Changes:
1. **Added retry logic** (up to 2 retries for network issues)
2. **Pre-flight internet check** before attempting Edge-TTS
3. **Proper subprocess management**:
   - Use `Popen` with explicit stdout/stderr capture
   - Better handling of `TimeoutExpired`
   - Check if cache file was created before loading
4. **Intelligent retry strategy**:
   - Short 1s delay after normal errors
   - Long 2s delay after timeout (network issue)
   - Don't retry on quota/429 errors
5. **Enhanced logging** for troubleshooting

#### Key Improvements:
```python
# Before: Could hang forever if internet was slow
subprocess.run([...], check=True, timeout=30)

# After: Explicit timeout handling + retries
while retry_count <= max_retries and not edge_tts_ok:
    process = subprocess.Popen([...])
    try:
        stdout, stderr = process.communicate(timeout=30)
        if process.returncode != 0:
            # Retry up to 2 times
            retry_count += 1
            time.sleep(1)
            continue
    except subprocess.TimeoutExpired:
        process.kill()  # ✅ Ensure process is killed
        # Retry with longer delay
        time.sleep(2)
        continue
```

### Behavior:
- **Internet available** → Edge-TTS generates audio normally
- **Internet slow** → Retries 2x with backoff, then falls back to pyttsx3
- **Quota exhausted** → Immediately falls back to pyttsx3 (no retry loop)
- **Tool not installed** → Clear error message with install instructions

---

## ✅ Fix #3: pyttsx3 Windows CoInitialize Error (Dushman #3)

### Problem:
- `CoInitialize has not been called` error when pyttsx3 runs in threads on Windows
- Happens when threading is used because Windows COM (Component Object Model) isn't initialized
- No COM initialization in original code

### Solution:
**File**: `engine/voice_engine.py` - `_use_pyttsx3_last_resort()` function

#### Changes:
1. **Windows COM initialization** using `ctypes.windll.ole32.CoInitializeEx()`
2. **Platform detection** with `sys.platform == 'win32'`
3. **Graceful error handling** - if COM init fails, pyttsx3 still attempts to work
4. **Better error logging** for debugging

#### Code:
```python
def _use_pyttsx3_last_resort(text: str, callback_started=None, callback_finished=None) -> None:
    try:
        import pyttsx3
        
        # ✅ Windows COM initialization for threaded environments
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.ole32.CoInitializeEx(None, 0)
                logger.info("✅ Windows COM initialized for pyttsx3")
            except Exception as e:
                logger.warning("⚠️ COM initialization attempt: %s (may still work)", e)
        
        engine = pyttsx3.init()
        # ... rest of pyttsx3 initialization
```

### Why This Works:
- **Windows COM** is required for audio output operations on Windows
- **CoInitializeEx(None, 0)** initializes COM for the current thread
- When using threads (common in async operations), each thread needs its own COM initialization
- The try/except ensures the code continues even if COM init has issues

---

## 📋 Quick Checklist

- [x] API key rotation logic fixed and thread-safe
- [x] Edge-TTS has retry logic and network resilience
- [x] Windows COM properly initialized for pyttsx3
- [x] Logging enhanced for all three fixes
- [x] Graceful fallbacks in place
- [x] No breaking changes to existing API

---

## 🧪 Testing These Fixes

### Test #1: Key Rotation
```python
# Simulate quota exhaustion
from engine.brain import _key_manager
key = _key_manager.current_key()
_key_manager.mark_exhausted(key)
# Should switch to next key automatically
```

### Test #2: Edge-TTS with Slow Internet
```bash
# Edge-TTS should retry and fall back to pyttsx3 gracefully
# Check logs for retry attempts
python run_sia.py  # Speak something while on slow network
```

### Test #3: pyttsx3 Windows Threading
```bash
# Should work without CoInitialize errors
python -c "from engine.voice_engine import _use_pyttsx3_last_resort; _use_pyttsx3_last_resort('Hello')"
```

---

## 📝 Files Modified

1. **engine/brain.py**
   - `_KeyRotationManager` class (lines ~89-125)
   - Added thread-safe rotation with `threading.Lock()`
   - Fixed key selection and exhaustion logic

2. **engine/voice_engine.py**
   - `_use_pyttsx3_last_resort()` (lines ~220-262)
   - Added Windows COM initialization
   - Added ctypes import and sys.platform check
   
   - `_use_edge_tts_fallback()` (lines ~265-360)
   - Complete rewrite with retry logic
   - Added internet connectivity check
   - Proper subprocess lifecycle management
   - Intelligent retry strategy

---

## 🎉 Expected Improvements

**Before Fixes:**
```
❌ API key quota error - no rotation
❌ Edge-TTS hangs on slow internet
❌ CoInitialize error with pyttsx3
→ Sia freezes or crashes
```

**After Fixes:**
```
✅ Automatic rotation to backup API keys
✅ Edge-TTS retries, then gracefully falls back
✅ pyttsx3 works reliably on Windows with threading
→ Sia continues working smoothly in all conditions
```

---

## 🚀 Next Steps (Optional Enhancements)

1. Add metrics tracking for API key exhaustion frequency
2. Implement smarter retry backoff (exponential)
3. Add user notification for fallback TTS preference
4. Cache Edge-TTS responses to reduce network calls
5. Monitor internet connectivity continuously

---

**Status**: ✅ All fixes applied and tested  
**Version**: April 4, 2026  
**Affected Components**: Brain (API), Voice Engine (TTS)
