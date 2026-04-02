# 🎯 Sia Desktop Assistant - Complete Setup Guide

## 3 Main Features Implementation

### 1. **Avatar Transparency (Floating Effect)** 🎨

**Current Issue**: Sia's avatar has a white/dark background instead of being transparent.

#### Step 1: Remove Avatar Background

Run this script to make avatars transparent:

```bash
python setup_transparent_avatar.py
```

**🔧 Two methods available:**

**Method A: Automatic (Recommended)** - Uses color-based removal
- Works automatically with your current images  
- Fast processing
- Good for solid backgrounds

**Method B: Best Quality** - Uses AI background removal
```bash
pip install rembg
python setup_transparent_avatar.py
```
- Uses AI model for perfect background removal
- Takes longer but results look professional
- Download ~300MB model on first run

#### After Setup:
✅ Your avatars will have transparent backgrounds  
✅ Code will auto-detect transparent PNG files  
✅ You'll see logs: `✅ Loaded transparent avatar: Sia_closed.png`

---

### 2. **"System: Could Not Hear Anything" Fix** 🎤

**Problem**: Microphone sensitivity is too high, missing quiet speech.

#### Solution Applied:
- Reduced `energy_threshold` from 300 → **50** (ultra-sensitive)
- Reduced `pause_threshold` from 0.6 → **0.5** (faster response)
- Activated `dynamic_energy_threshold` (adapts to environment)

**Files Updated:**
- `engine/listen_engine.py` - Main listening logic
- `sia_desktop.py` - Wake word detection

#### If still not working:

1. **Check Microphone:**
   ```bash
   python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_indexes())"
   ```

2. **Test Microphone:**
   ```python
   import speech_recognition as sr
   recognizer = sr.Recognizer()
   with sr.Microphone() as source:
       print("Speak!")
       audio = recognizer.listen(source)
       print(f"Audio energy: {sr.Recognizer().energy_threshold}")
   ```

3. **Manual Adjustment** (if needed):
   Edit `engine/listen_engine.py`, line ~75:
   ```python
   recognizer.energy_threshold = 30  # Try even lower (0-100 range)
   ```

---

### 3. **Always-On-Top + Screen Geometry** 🔝

**Already Implemented!** ✅

#### How it works:
```python
# Window always stays on top
self.setWindowFlags(
    Qt.FramelessWindowHint |
    Qt.WindowStaysOnTopHint  # ← This keeps Sia always visible
)

# Positioned at screen corners with proper size
PANEL_WIDTH = 400
PANEL_HEIGHT = 700
x_pos = screen.width() - PANEL_WIDTH - 20
y_pos = (screen.height() - PANEL_HEIGHT) // 2
```

#### Features:
- ✅ Always visible above other windows
- ✅ Doesn't block desktop (transparent background)
- ✅ Right-side panel like Windows Action Center
- ✅ Frameless design
- ✅ Draggable (click and drag to move)

---

## 🚀 Quick Start Activation Steps

### Step 0: Check Python Requirements
```bash
pip install pillow  # For image processing
pip install rembg   # Optional: best quality background removal
```

### Step 1: Make Avatars Transparent
```bash
python setup_transparent_avatar.py
```

### Step 2: Restart Sia
```bash
python sia_desktop.py
```
or
```bash
./start_sia.bat
```

### Step 3: Watch for Success Indicators

**Console Output:**
```
✅ Loaded transparent avatar: Sia_closed.png
✅ Lip-sync frames loaded: 3 frames
```

**Visual Changes:**
- Sia appears on desktop without background box
- Can see your wallpaper behind her
- Chat bubbles float above her
- Always visible, even when other windows open

---

## 🔍 Troubleshooting

### Avatar Still Has Background?

**Cause**: Image doesn't have alpha channel (transparency data)

**Fix:**
```bash
# Method 1: Use rembg (best quality)
pip install rembg
python setup_transparent_avatar.py

# Method 2: Use online tool
# Visit https://remove.bg
# Upload each image: Sia_closed.png, Sia_semi.png, Sia_open.png
# Download as PNG with transparent background
# Replace files in assets/ folder
```

### Microphone Not Detecting Speech?

**Possible Causes & Fixes:**

1. **Wrong Microphone Selected**
   ```bash
   # List available mics
   python -c "import speech_recognition as sr; print(speech_recognition.Microphone.list_microphone_indexes())"
   ```

2. **Sensitivity Still Too High**
   Edit `engine/listen_engine.py`:
   ```python
   recognizer.energy_threshold = 30  # Lower = more sensitive
   ```

3. **Noise Interference**
   - Close browser tabs
   - Turn off background music
   - Reduce fan/AC noise
   - Microphone might be too far away

4. **Test Recognition**
   ```bash
   python -c "
   import speech_recognition as sr
   r = sr.Recognizer()
   r.energy_threshold = 50
   with sr.Microphone() as source:
       print('Say something!')
       audio = r.listen(source)
       print(r.recognize_google(audio))
   "
   ```

### Sia Still Appears Behind Other Windows?

The "Always On Top" flag should keep it visible. If not:

1. Check Windows settings:
   - Settings → Display → Graphics
   - Ensure GPU drivers are updated

2. Force flag update:
   ```python
   # In sia_desktop.py, add after self.show():
   self.raise_()
   self.activateWindow()
   ```

---

## 📊 Technical Changes Summary

### Files Modified:

**1. `sia_desktop.py`**
- Line 418: Changed `WA_TranslucentBackground` from `False` → `True`
- Line 528-537: Enhanced character pixmap loading with alpha channel validation
- Line 195-197: Optimized wake word microphone settings
- Line 765: Improved paintEvent for true transparency

**2. `engine/listen_engine.py`**
- Line 75-85: Optimized microphone thresholds for sensitivity

**3. NEW FILE: `setup_transparent_avatar.py`**
- Removes backgrounds from avatar images
- Creates transparent PNG files
- Supports both automatic and AI-based methods

---

## 🎓 What Changed?

### Before (Dark Box Problem)
```
┌─────────────────────┐
│    [Dark Box]       │  ← Solid background
│    ┌─────────────┐  │
│    │   Avatar    │  │  ← Character
│    └─────────────┘  │
│  [Chat Bubble]      │
└─────────────────────┘
```

### After (Transparent Floating)
```
Your desktop wallpaper showing through
         ┌─────────────┐
    ┌─>[   Avatar    ]<─ Only character visible
    │    └─────────────┘
    └──[Chat Bubble] floating above
       (transparent background)
```

---

## ✨ Next Steps to Enhance

After getting transparency working:

1. **Custom Avatar Art**
   - Design your own transparent PNG
   - Place in `assets/` folder
   - Update image paths in code

2. **Better Microphone**
   - External USB microphone reduces background noise
   - Improves voice recognition accuracy

3. **Custom Emotions**
   - Create different avatar poses for moods
   - Code supports unlimited emotional states

---

## 🆘 Still Need Help?

1. Check the log files:
   ```bash
   cat logs/sia.log  # View error messages
   ```

2. Run diagnostic:
   ```bash
   python verify_backend.py
   ```

3. Debug mode:
   ```bash
   python sia_desktop.py --debug
   ```

---

**Version**: Sia v2.0 - Transparent Desktop Assistant  
**Date**: 2026-04  
**Status**: ✅ Production Ready
