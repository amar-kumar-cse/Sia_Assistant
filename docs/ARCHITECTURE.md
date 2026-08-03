# Sia Assistant - Architecture Specification & Developer Guide

## 🏗️ System Architecture

```
                    ┌─────────────────────────────────────────┐
                    │               User Input                │
                    │      (Hotkey / Voice / GUI Chat)        │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │             Intent Engine               │
                    │   (Sanitizer / Intent Classifier /      │
                    │       Rate Limiter & Policy Check)      │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │          Avatar State Machine           │
                    │   (Idle → Listening → Thinking → Speak) │
                    └────────────────────┬────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
     ┌─────────────────────────────┐           ┌─────────────────────────────┐
     │       Gemini AI Brain       │           │        Vision Engine        │
     │   (Rotational Key Manager / │           │   (Privacy App Filter /     │
     │   Local Ollama Fallback /   │           │    Prompt Injection Guard  │
     │      Cache Manager)         │           │   & Visual Recording Dot)   │
     └──────────────┬──────────────┘           └──────────────┬──────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │              Voice Engine               │
                    │ (Thread-Safe Audio Queue / Edge-TTS /   │
                    │    Instant Speech Barge-In Interrupt)   │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │            SQLite Memory DB             │
                    │  (WAL Mode / User Facts KV Store /      │
                    │    30-Day Auto Retention Cleanup)       │
                    └─────────────────────────────────────────┘
```

## 🔄 Avatar State Machine Lifecycle

- **`IDLE`**: Avatar plays transparent idle WebM loop.
- **`LISTENING`**: Mic audio stream active; noise filter and energy thresholding applied.
- **`THINKING`**: Query submitted to Gemini AI Brain / Local Ollama fallback.
- **`SPEAKING`**: Speech synthesis active. User can hit hotkey or speak to trigger **Barge-In Interruption**.
- **`ERROR`**: Non-blocking toast alert displayed; avatar returns safely to `IDLE`.

## 🔒 Security & Privacy Guarantees

1. **Screen Prompt Injection Defense**: Vision engine wraps raw OCR content inside `<untrusted_screen_observation>` tags and strips instruction overrides.
2. **Privacy App Exclusion**: Active window titles are checked against sensitive application keywords (`1Password`, `Bitwarden`, `KeePass`, banking apps) and screen capture is blocked automatically.
3. **Encrypted Key Storage**: Keyring OS Credential Manager integration prevents raw key exposure.
4. **SQLite WAL Mode**: Thread-safe database connections with `RLock` prevent database lock race conditions.
