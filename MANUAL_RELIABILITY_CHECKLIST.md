# Manual Reliability & Hardware Failure Checklist

This checklist documents manual testing procedures for environmental, hardware, and physical failures that cannot be fully automated in CI/CD unit tests.

---

## 1. Microphone Hardware Disconnection
- [ ] **Procedure**: Start Sia, speak a wake word, then immediately disconnect the USB microphone / disable mic driver mid-sentence.
- [ ] **Expected Result**: `listen_engine.py` catches `PyAudio` / `Microphone` access exception, logs error to `sia.log`, displays toast "Microphone connection lost", and returns to idle state without crashing PyQt6 application.

---

## 2. Audio Output / Speaker Disconnection
- [ ] **Procedure**: Trigger Sia voice response (`think` -> `speak`), then unplug headphones or change default audio output device mid-speech.
- [ ] **Expected Result**: `voice_engine.py` handles audio device error, falls back to silent display / offline TTS engine, and resets `VoiceState` cleanly.

---

## 3. Physical Network Interruption
- [ ] **Procedure**: Turn off Wi-Fi / disconnect Ethernet while Sia is processing a complex query or streaming a response.
- [ ] **Expected Result**: Hard timeout triggers within configured `timeout_seconds`, `safe_sync_call` or `safe_async_call` returns domain fallback message ("Internet connection drop ho gaya"), avatar returns to idle state, and UI remains responsive.

---

## 4. System Hibernation & Resume
- [ ] **Procedure**: Put the PC to sleep with Sia running in background, then resume after 1 minute.
- [ ] **Expected Result**: Background loops (`ProactiveEngine`, `WakeWordListener`) resume automatically or log warning without freezing PyQt6 event loop or exhausting CPU.

---

## 5. Corrupted `memory.db` SQLite Database
- [ ] **Procedure**: Manually corrupt `memory.db` header bytes while app is shut down, then launch `main.py`.
- [ ] **Expected Result**: `_init_db()` catches `DatabaseError`, logs critical notice, re-initializes fresh database structure, and displays recovery toast notice to user.
