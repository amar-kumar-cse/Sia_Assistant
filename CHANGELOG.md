# Changelog

All notable changes to **Sia Assistant** will be documented in this file.

## [2.0.0] - 2026-08-03

### 🚀 Code Architecture & Engineering
- Added formal thread-safe `AvatarStateMachine` (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`).
- Added injectable `ConfigManager` and OS Credential Manager (`keyring`) integration.
- Upgraded SQLite engine to WAL mode (`PRAGMA journal_mode=WAL`) with re-entrant `RLock` thread safety.
- Modernized packaging with `pyproject.toml` and `requirements-dev.txt`.

### 🔒 Security & Privacy
- Added prompt injection sanitization for screen/OCR observations (`<untrusted_screen_observation>`).
- Implemented sensitive process App Exclusion List (`1Password`, `Bitwarden`, `KeePass`, banking browsers).
- Added visual active recording badge indicator on overlay during screen capture.
- Enforced strict path traversal protection using `pathlib.Path.resolve()` root boundary checks.
- Implemented 30-day automated memory retention cleanup policy (`cleanup_retention_policy`).

### 🧠 AI & Performance
- Added local Ollama model fallback for privacy-first offline mode (`SIA_LOCAL_ONLY`).
- Added response cache manager (`cache_manager.py`) using SHA256 query hashes with TTL expiration.
- Implemented sliding-window context truncation to manage history token budget.

### 🎙️ Voice & Avatar UX
- Added instant **Barge-In / Interrupt** capability to stop speech playback cleanly.
- Added multi-monitor coordinate detection and positioning support.
- Connected avatar state machine listeners for smooth 300ms video cross-fades.

### 🧪 Testing & CI
- Created offline mock providers (`MockGeminiProvider`, `MockVoiceEngine`).
- Added GitHub Actions CI pipeline (`.github/workflows/ci.yml`).
