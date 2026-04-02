"""
Transparency & Features Verification Script for Sia
Tests avatar transparency, microphone, and window features
"""

import os
import sys
from PIL import Image

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

def check_avatar_transparency():
    """Check if avatar images have transparent backgrounds."""
    print("\n" + "="*60)
    print("🎨 AVATAR TRANSPARENCY CHECK")
    print("="*60)
    
    avatar_files = ["Sia_closed.png", "Sia_semi.png", "Sia_open.png"]
    all_transparent = True
    
    for avatar_file in avatar_files:
        path = os.path.join(ASSETS_DIR, avatar_file)
        
        if not os.path.exists(path):
            print(f"❌ {avatar_file}: FILE NOT FOUND")
            all_transparent = False
            continue
        
        try:
            img = Image.open(path)
            size_kb = os.path.getsize(path) / 1024
            
            # Check for alpha channel (transparency)
            if img.mode == 'RGBA':
                has_alpha = True
                # Check if alpha channel is actually used
                if img.getextrema()[3] == (255, 255):  # All fully opaque
                    has_alpha_data = False
                else:
                    has_alpha_data = True
            else:
                has_alpha = False
                has_alpha_data = False
            
            status = "✅" if has_alpha and has_alpha_data else "⚠️ "
            
            print(f"\n{status} {avatar_file}")
            print(f"   Size: {size_kb:.1f} KB")
            print(f"   Mode: {img.mode}")
            print(f"   Dimensions: {img.size[0]}x{img.size[1]}")
            
            if has_alpha:
                if has_alpha_data:
                    print(f"   ✅ Has transparency data - PERFECT!")
                else:
                    print(f"   ⚠️  Has alpha channel but no actual transparency")
                    print(f"      (Image is fully opaque)")
            else:
                print(f"   ❌ NO TRANSPARENCY - needs background removal")
                all_transparent = False
                
        except Exception as e:
            print(f"❌ {avatar_file}: ERROR - {e}")
            all_transparent = False
    
    print("\n" + "-"*60)
    if all_transparent:
        print("✅ All avatars are properly transparent!")
    else:
        print("❌ Some avatars need background removal")
        print("   Run: python setup_transparent_avatar.py")
    
    return all_transparent

def check_microphone():
    """Check if speech recognition library is available."""
    print("\n" + "="*60)
    print("🎤 MICROPHONE & SPEECH RECOGNITION CHECK")
    print("="*60)
    
    try:
        import speech_recognition as sr
        print("\n✅ speech_recognition library: INSTALLED")
        
        # Try to get available microphones
        try:
            mics = sr.Microphone.list_microphone_indexes()
            print(f"✅ Found {len(mics)} microphone(s)")
            
            for i, mic in enumerate(mics):
                print(f"   [{i}] Available microphone")
        except Exception as e:
            print(f"⚠️  Could not list microphones: {e}")
        
        # Check recognizer settings
        recognizer = sr.Recognizer()
        print(f"\n📊 Current Microphone Settings:")
        print(f"   Energy Threshold: {recognizer.energy_threshold}")
        print(f"   Pause Threshold: {recognizer.pause_threshold}")
        print(f"   Dynamic Threshold: {recognizer.dynamic_energy_threshold}")
        
        # Check if settings are optimized
        if recognizer.energy_threshold <= 100:
            print(f"   ✅ Energy threshold is optimized (low = sensitive)")
        else:
            print(f"   ⚠️  Energy threshold might be too high")
        
        return True
    except ImportError:
        print("\n❌ speech_recognition library: NOT INSTALLED")
        print("   Install with: pip install SpeechRecognition pyaudio")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def check_pyqt5():
    """Check if PyQt5 is available."""
    print("\n" + "="*60)
    print("🪟 PyQt5 LIBRARY CHECK")
    print("="*60)
    
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication
        print("\n✅ PyQt5: INSTALLED")
        
        # Check if transparency attributes exist
        if hasattr(Qt, 'WA_TranslucentBackground'):
            print(f"✅ WA_TranslucentBackground: AVAILABLE")
        else:
            print(f"❌ WA_TranslucentBackground: NOT AVAILABLE")
        
        return True
    except ImportError:
        print("\n❌ PyQt5: NOT INSTALLED")
        print("   Install with: pip install PyQt5")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def check_engine_modules():
    """Check if Sia engine modules are available."""
    print("\n" + "="*60)
    print("⚙️  SIA ENGINE MODULES CHECK")
    print("="*60)
    
    modules = [
        ('engine.brain', 'AI Brain'),
        ('engine.voice_engine', 'Voice Engine'),
        ('engine.listen_engine', 'Listen Engine'),
        ('engine.actions', 'Action Handler'),
        ('engine.logger', 'Logger'),
    ]
    
    all_good = True
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"✅ {display_name}: OK")
        except Exception as e:
            print(f"❌ {display_name}: {str(e)[:50]}")
            all_good = False
    
    return all_good

def main():
    """Run all checks."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  SIA DESKTOP ASSISTANT - FEATURE VERIFICATION             ║")
    print("║  Checking: Transparency | Microphone | PyQt5 | Modules    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    results = {
        "Avatars Transparent": check_avatar_transparency(),
        "Microphone Ready": check_microphone(),
        "PyQt5 Available": check_pyqt5(),
        "Engine Modules": check_engine_modules(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📋 VERIFICATION SUMMARY")
    print("="*60)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} - {check_name}")
    
    all_pass = all(results.values())
    
    print("\n" + "="*60)
    if all_pass:
        print("✅ ALL CHECKS PASSED - Sia is ready to run!")
        print("\nStart Sia with:")
        print("   python sia_desktop.py")
    else:
        print("⚠️  SOME CHECKS FAILED - Fix issues before running Sia")
        print("\n📝 Next steps:")
        print("1. Run: python setup_transparent_avatar.py")
        print("2. Install missing packages: pip install -r requirements.txt")
        print("3. Run: python verify_backend.py")
    print("="*60 + "\n")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
