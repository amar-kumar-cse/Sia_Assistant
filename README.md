# 🤖 Sia — AI Desktop Assistant

> An intelligent AI-powered desktop assistant with a transparent "Ghost UI", real-time voice recognition, and proactive screen awareness — built entirely in Python.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini_1.5_Pro-4285F4?style=for-the-badge&logo=google&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-FF6B6B?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

---

## ✨ What is Sia?

Sia is a next-generation AI desktop assistant that lives on your screen as a transparent animated character. Unlike traditional chatbots, Sia watches your screen proactively, responds to voice commands, lip-syncs while speaking, and blends seamlessly into your desktop without blocking your workflow.

Think of it as **JARVIS for your Windows desktop** — but open source and built by a 2nd year CS student. 😄

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| 🪟 **Ghost UI** | True transparent window using Win32 API — no borders, no background, just Sia |
| 🧠 **Gemini 1.5 Pro Brain** | Powered by Google's LLM with automatic API key rotation for reliability |
| 🎤 **Voice Recognition** | Real-time "Hey Sia" wake-word detection for hands-free interaction |
| 🗣️ **Lip Sync** | Animated mouth movements synced with Edge-TTS speech output |
| 👁️ **Screen Awareness** | Proactive engine that analyzes your screen and gives contextual comments |
| 💨 **Breathing Animation** | Smooth figure-8 breathing animation with head tilt for lifelike feel |
| 🔄 **Async Architecture** | Built with `qasync` for smooth non-blocking UI and AI responses |

---

## 🛠️ Tech Stack

```
Language     : Python
AI/LLM       : Google Gemini 1.5 Pro
GUI          : CustomTkinter + Win32 API (ctypes)
Voice Input  : SpeechRecognition + Wake Word Detection
Voice Output : Edge-TTS (Microsoft Neural Voices)
Animation    : PNG-based frame animation + OpenCV
Architecture : Async event loop (qasync + asyncio)
```

---

## 📁 Project Structure

```
Sia_Assistant/
├── engine/
│   ├── brain.py          # LLM logic + Gemini API key rotation
│   └── proactive.py      # Screen awareness & proactive comment engine
├── analytics/            # Usage tracking and session analytics
├── assets/               # Character images (PNG frames)
│   ├── sia_idle.png
│   ├── Sia_semi.png
│   ├── Sia_open.png
│   └── sia_blink.png
├── cache/                # Response caching layer
├── tests/                # Test suite
├── docs/                 # Internal docs & roadmaps
├── scripts/              # Utility & fix scripts
├── main.py               # Entry point — qasync event loop
├── overlay.py            # Click-through main window + system tray
├── character_widget.py   # Visual core — breathing, lip sync, Win32
├── chat_bubble.py        # Glassmorphism chat UI
├── sia_desktop.py        # Desktop integration layer
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── launch_sia.bat        # One-click Windows launcher
└── setup.ps1             # PowerShell setup script
```

---

## ⚡ Getting Started

### Prerequisites
- Windows 10/11
- Python 3.10+
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))
- Microphone (for voice features)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/amar-kumar-cse/Sia_Assistant.git
cd Sia_Assistant

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Open .env and add your Gemini API key(s)

# 4. Launch Sia
python main.py
```

### One-Click Launch (Windows)
```bash
# Just double-click or run:
launch_sia.bat
```

---

## 🔑 Environment Variables

```env
GEMINI_API_KEY_1=your_primary_gemini_key
GEMINI_API_KEY_2=your_backup_key        # optional, for rotation
```

> Get your free Gemini API key at [aistudio.google.com](https://aistudio.google.com/app/apikey)

---

## 🎯 How It Works

```
User speaks "Hey Sia..."
        ↓
Wake word detected (local, offline)
        ↓
Voice captured & transcribed
        ↓
Gemini 1.5 Pro processes query
        ↓
Response generated + lip sync triggered
        ↓
Edge-TTS speaks response
        ↓
Proactive engine watches screen in background
        ↓
Sia comments on what you're doing 👀
```

---

## 🗺️ Roadmap

- [x] Transparent Ghost UI with Win32 API
- [x] Gemini LLM integration with key rotation
- [x] Voice recognition + wake word
- [x] Lip sync animation
- [x] Proactive screen awareness
- [ ] Multi-monitor support
- [ ] Plugin system for custom commands
- [ ] Mobile companion app

---

## 👨‍💻 Author

**Amar Kumar**
- 🔗 GitHub: [@amar-kumar-cse](https://github.com/amar-kumar-cse)
- 💼 LinkedIn: [linkedin.com/in/amarkumarr](https://linkedin.com/in/amarkumarr)
- 📧 Email: amarkrydav@gmail.com

---

## ⭐ If you find Sia cool, drop a star! It motivates a lot 🙏
