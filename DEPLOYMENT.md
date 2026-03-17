# Sia Assistant - Setup & Deployment Guide

## 🚀 Quick Setup

### 1. Run Setup Script

```powershell
# Open PowerShell as Administrator
cd "C:\Users\yadav\OneDrive\Desktop\Sia_Assistant"
.\setup.ps1
```

This will:
- ✅ Create virtual environment (`.venv/`)
- ✅ Install all dependencies
- ✅ Create `.env` template
- ✅ Set up project folders

---

### 2. Configure API Keys

Edit `.env` file:

```env
GEMINI_API_KEY=your_actual_key_here
ELEVENLABS_API_KEY=your_actual_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL=eleven_turbo_v2
```

**Get API Keys:**
- **Gemini**: https://makersuite.google.com/app/apikey
- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys

---

### 3. Launch Sia

```batch
.\start_sia.bat
```

---

## ⚡ Advanced Setup

### Global Hotkeys

**Available Shortcuts:**
- `Alt+Space` → Toggle Sia visibility
- `Ctrl+Shift+S` → Screenshot analysis (future)
- `Ctrl+Shift+V` → Quick voice input

**Note:** Hotkeys require administrator privileges. Run Sia as admin for full functionality.

---

### Startup on Boot

**Option 1: Manual (Recommended)**
1. Press `Win+R`
2. Type: `shell:startup`
3. Copy `start_sia_silent.bat` to this folder

**Option 2: PowerShell Script**
```powershell
# Run this once
$startup = [Environment]::GetFolderPath('Startup')
$shortcut = $startup + "\Sia Assistant.lnk"
$target = "C:\Users\yadav\OneDrive\Desktop\Sia_Assistant\start_sia_silent.bat"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcut)
$Shortcut.TargetPath = $target
$Shortcut.Save()
```

Sia will now start minimized to system tray on every boot!

---

### System Tray Behavior

When `--startup` flag is used:
- ✅ Starts minimized to system tray
- ✅ No console window
- ✅ Use `Alt+Space` to show

---

## 🔧 Troubleshooting

### Hotkeys Not Working

**Solution:**
```batch
# Run as administrator
Right-click start_sia.bat → "Run as administrator"
```

---

### Voice Recognition Issues

**Adjust Microphone Sensitivity:**

Edit `listen_engine.py`:
```python
recognizer.energy_threshold = 300  # Increase to 500 for noisy environments
```

**Test Your Microphone:**
```python
python -m speech_recognition
```

---

### Performance Issues

**Optimize for Low-End Systems:**

1. **Reduce Animation Quality:**
   - Use PNG instead of GIF
   - Increase sync interval from 50ms to 100ms

2. **Disable Acrylic Effects:**
   - Comment out blur effects in main code

3. **Limit Memory Usage:**
   - Reduce cache TTL in `memory.py`

---

## 📁 Project Structure

```
Sia_Assistant/
├── .venv/              # Virtual environment (auto-created)
├── .env                # API keys (create from template)
├── assets/             # Avatar images
│   ├── sia_idle_1.png
│   ├── sia_talk_1.png
│   └── sia_icon.ico
├── study_notes/        # PDF notes for RAG (future)
├── brain.py            # AI logic
├── voice_engine.py     # Voice synthesis
├── listen_engine.py    # Speech recognition
├── memory.py           # Context management
├── hotkey_manager.py   # Global shortcuts
├── main_sia_2.py       # Main application
├── setup.ps1           # Setup script
├── start_sia.bat       # Normal launcher
└── start_sia_silent.bat # Silent startup
```

---

## 🎯 Usage Tips

### Best Practices

1. **Keep .env Secure**
   - Never commit to Git
   - Add to `.gitignore`

2. **Update Dependencies**
   ```batch
   .venv\Scripts\activate
   pip install --upgrade -r requirements.txt
   ```

3. **Backup Your Data**
   - `memory.json` - Your personal context
   - `.env` - Your API keys
   - `study_notes/` - Your PDFs

---

### Performance Optimization

**For Best Speed:**
```env
# Use Turbo model
ELEVENLABS_MODEL=eleven_turbo_v2

# Lighter voice settings in voice_engine.py
stability = 0.3
similarity_boost = 0.6
```

**For Best Quality:**
```env
# Use Multilingual model
ELEVENLABS_MODEL=eleven_multilingual_v2

# Higher quality settings
stability = 0.5
similarity_boost = 0.8
```

---

## 🐛 Common Issues

### "Module not found" Error

```batch
# Ensure virtual environment is activated
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### "API Key Invalid" Error

1. Check `.env` file has correct keys
2. Verify keys are active on respective platforms
3. Check for trailing spaces in keys

---

### Sia Not Starting Silently

1. Verify `pythonw.exe` (not `python.exe`) in silent script
2. Check startup folder permissions
3. Test manually: `start /min "" .venv\Scripts\pythonw.exe main_sia_2.py --startup`

---

## 📞 Support

For issues:
1. Check console output for errors
2. Review `.env` configuration
3. Test API keys separately
4. Verify Python version (3.8+)

---

Built with ❤️ for seamless deployment!
