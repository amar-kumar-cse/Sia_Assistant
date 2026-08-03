# Contributing to Sia Assistant

Thank you for your interest in contributing to **Sia Assistant**!

## 🛠️ Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/AmarKumar-hub-ai/Sia_Assistant.git
   cd Sia_Assistant
   ```

2. Set up virtual environment and install development dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-dev.txt
   pip install -e .
   ```

3. Run unit test suite:
   ```bash
   pytest tests/ -v
   ```

## 📐 Code Guidelines

- Keep UI logic decoupled from core engine services.
- Always use `AvatarStateMachine` transitions for avatar visual state changes.
- Ensure all database accesses use `_db_lock` (`RLock`) and operate within SQLite WAL mode.
- Avoid committing raw API keys in `.env` files; use `KeychainManager`.
