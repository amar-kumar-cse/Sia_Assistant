# Sia AI Assistant (FINAL VERSION)

Sia is an advanced AI Desktop Assistant designed to look and act like a video character. It runs natively on Windows, with a transparent background, dynamic figure-8 breathing animations, lip-syncing, and proactive screen awareness.

## Features
- **Transparent UI**: Uses Win32 API to create a true transparent click-through window without borders.
- **Dynamic Animation**: PNG-based figure-8 breathing, slight head tilt, and scale-pulse lip syncing.
- **Smart Brain**: Gemini 1.5 Pro integration with robust API key rotation.
- **Voice & Wake Word**: Edge-TTS integration and localized "Hey Sia" wake-word detection.
- **Proactive Engine**: Periodically analyzes your screen to give short, witty, and contextual Hinglish comments.

## Setup Instructions

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Environment Variables**
Copy `.env.example` to `.env` and fill in your Gemini API keys.
```bash
cp .env.example .env
```

3. **Assets Directory**
Make sure the `assets/` folder contains the following:
- `sia_idle.png`
- `Sia_semi.png`
- `Sia_open.png`
- `sia_blink.png`
- (Optional) `idle.mp4` & `thinking.mp4`

4. **Run the App**
```bash
python main.py
```

## Structure
- `character_widget.py`: The visual heart of Sia (Breathing, Lip Sync, Win32 transparency).
- `overlay.py`: The click-through main window and system tray.
- `chat_bubble.py`: Glassmorphism chat UI.
- `engine/brain.py`: LLM logic and Key Rotation.
- `engine/proactive.py`: Screen awareness loops.
- `main.py`: `qasync` async event loop connecting everything.
