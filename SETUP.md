# 🚀 Sia Assistant - Complete Setup Guide

## Prerequisites

- Windows 10/11
- Python 3.8 or higher
- Internet connection for API calls

---

## ⚡ Automated Setup (Recommended)

### Step 1: Run Setup PowerShell Script

```powershell
# Right-click PowerShell and "Run as Administrator"
cd "C:\Users\yadav\OneDrive\Desktop\Sia_Assistant"

#If execution policy blocks script:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Run setup
.\setup.ps1
```

**This script automatically:**
- ✅ Creates virtual environment
- ✅ Installs all dependencies
- ✅ Creates `.env` template
- ✅ Sets up folders

---

### Step 2: Configure API Keys

Open `.env` and add your keys:

```env
GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_KEY
ELEVENLABS_API_KEY=YOUR_ACTUAL_ELEVENLABS_KEY
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL=eleven_turbo_v2
```

**Where to get keys:**
- Gemini: https://makersuite.google.com/app/apikey  
- ElevenLabs: https://elevenlabs.io/app/settings/api-keys

---

### Step 3: Launch Sia

**Normal Mode:**
```batch
start_sia.bat
```

**Silent Mode (System Tray):**
```batch
start_sia_silent.bat
```

---

## 📋 Manual Setup (Alternative)

If automated setup fails:

```batch
# 1. Create virtual environment
python -m venv .venv

# 2. Activate it
.venv\Scripts\activate

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file (see template above)
notepad .env

# 6. Run Sia
python main_sia_2.py
```

---

## 🎹 Global Hotkeys Setup

**Available Shortcuts:**
- `Alt+Space` → Show/Hide Sia
- `Ctrl+Shift+V` → Quick voice input

**Enable Hotkeys:**
1. Right-click `start_sia.bat`
2. Select "Run as administrator"

> **Note:** Global hotkeys require admin privileges on Windows

---

## 🌅 Auto-Start on Boot

### Method 1: Startup Folder (Easiest)

1. Press `Win+R`
2. Type: `shell:startup` and press Enter
3. Copy `start_sia_silent.bat` to this folder

Sia will now start minimized to system tray on every boot!

### Method 2: Task Scheduler (Advanced)

1. Open Task Scheduler
2. Create Basic Task → "Sia Assistant"
3. Trigger: "When I log on"
4. Action: Start a program
5. Program: `C:\Users\yadav\OneDrive\Desktop\Sia_Assistant\start_sia_silent.bat`

---

## 🎨 Add Avatar Images

Place these in `assets/` folder:

**Required files:**
- `sia_idle_1.png` - Idle animation frame 1
- `sia_idle_2.png` - Idle animation frame 2
- `sia_talk_1.png` - Talking animation frame 1
- `sia_talk_2.png` - Talking animation frame 2
- `sia_icon.ico` - System tray icon (optional)

**Optional:** Use `.gif` files for smoother animation:
- `sia_idle.gif`
- `sia_talking.gif`

---

## 🎤 Microphone Optimization

### Test Microphone

```python
# Run this to test
python -m speech_recognition
```

### Adjust Sensitivity

If background noise triggers Sia, edit `listen_engine.py`:

```python
# Line ~12
recognizer.energy_threshold = 500  # Increase if too sensitive
```

**Recommended values:**
- Quiet room: 300
- Normal office: 500
- Noisy environment: 800-1000

---

## 🧪 Testing Your Setup

### Quick Test Commands

```python
# 1. Test modules
python -c "import brain, voice_engine, memory; print('✅ All modules OK')"

# 2. Test API connectivity
python -c "import brain; print(brain.think('test'))"

# 3. Test hotkeys
python hotkey_manager.py
```

### Test Sia Interaction

```
Say: "Hi Sia, kaisi ho?"
Expected: Sia responds in Hinglish with "Hero" addressing

Say: "Open my resume"
Expected: Resume.pdf opens

Say: "What's my college?"
Expected: Sia responds "RIT Roorkee"
```

---

## ⚙️ Configuration Options

### Voice Quality vs Speed

**Fast (Default):**
```env
ELEVENLABS_MODEL=eleven_turbo_v2
```

**High Quality:**
```env
ELEVENLABS_MODEL=eleven_multilingual_v2
```

### Animation Speed

Edit `main_sia_2.py`:
```python
# Line ~106
self.sync_timer.start(50)  # 50ms = ultra-smooth
# Change to 100 for lower CPU usage
```

---

## 🐛 Troubleshooting

### "Virtual environment not found"

```batch
# Create it manually
python -m venv .venv
.\setup.ps1
```

### "API Key Invalid"

1. Check `.env` file has no extra spaces
2. Verify keys on provider websites
3. Try regenerating keys

### "No module named 'PyQt5'"

```batch
# Reinstall dependencies
.venv\Scripts\activate
pip install -r requirements.txt --force-reinstall
```

### Hotkeys Not Working

- Run `start_sia.bat` as administrator
- Check if another app uses the same hotkey
- Try alternative hotkey combinations

### Poor Voice Recognition

1. Check microphone is set as default
2. Adjust `energy_threshold` in `listen_engine.py`
3. Speak clearer and closer to mic
4. Test with `python -m speech_recognition`

---

## 📂 Important Files

```
Sia_Assistant/
├── .env                    ← YOUR API KEYS (DO NOT SHARE)
├── .venv/                  ← Virtual environment
├── assets/                 ← Avatar images
├── study_notes/            ← PDF notes (RAG feature)
├── main_sia_2.py           ← Main application
├── setup.ps1               ← Setup script
├── start_sia.bat           ← Normal launcher
├── start_sia_silent.bat    ← Silent startup
└── QUICKSTART.md          ← Quick reference
```

---

## 🎯 Next Steps

1. ✅ Complete setup
2. ✅ Test voice interaction
3. ✅ Configure startup automation
4. ✅ Enable global hotkeys
5. 🎨 Customize avatar images
6. 📚 Add study PDFs for RAG (coming soon)

---

## 🆘 Still Having Issues?

1. Check console output for error messages
2. Verify Python version: `python --version` (should be 3.8+)
3. Ensure all files are in correct locations
4. Try manual setup method
5. Review `DEPLOYMENT.md` for advanced options

---

**You're all set! Launch Sia and enjoy your premium AI companion! 🚀**

Built with ❤️ by Amar for Amar
