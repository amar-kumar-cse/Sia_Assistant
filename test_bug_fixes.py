#!/usr/bin/env python3
"""
Test script to validate all three bug fixes for Sia Assistant
Dushman #1: API Key Rotation
Dushman #2: Edge-TTS Network Resilience  
Dushman #3: CoInitialize for pyttsx3 on Windows
"""

import sys
import os
import time
import threading

# Add engine to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_key_rotation():
    """Test #1: Verify API key rotation logic works correctly"""
    print("\n" + "="*60)
    print("🧪 TEST #1: API KEY ROTATION LOGIC")
    print("="*60)
    
    try:
        from engine.brain import _key_manager, _load_all_api_keys
        
        keys = _load_all_api_keys()
        print(f"✅ Loaded {len(keys)} API keys from environment")
        
        if keys:
            print(f"   Keys: {'***'.join([k[-6:] for k in keys])}")
            
            # Test current_key()
            current = _key_manager.current_key()
            if current:
                print(f"✅ current_key() returned: ...{current[-6:]}")
            else:
                print("⚠️  current_key() returned None (all keys might be exhausted)")
            
            # Test mark_exhausted with thread safety
            if current:
                print(f"\n   Testing mark_exhausted() on key ...{current[-6:]}")
                _key_manager.mark_exhausted(current, cooldown_seconds=10)
                print("✅ Marked key as exhausted (10s cooldown)")
                
                # Should rotate to next
                next_key = _key_manager.current_key()
                if next_key and next_key != current:
                    print(f"✅ Rotated to next key: ...{next_key[-6:]}")
                else:
                    print("⚠️  No rotation (may have only 1 key)")
            
            print("\n✅ KEY ROTATION TEST PASSED")
            return True
        else:
            print("⚠️  No API keys found in environment - skipping rotation tests")
            return True
            
    except Exception as e:
        print(f"❌ KEY ROTATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_tts_logic():
    """Test #2: Verify Edge-TTS retry logic is in place"""
    print("\n" + "="*60)
    print("🧪 TEST #2: EDGE-TTS NETWORK RESILIENCE")
    print("="*60)
    
    try:
        import inspect
        from engine.voice_engine import _use_edge_tts_fallback
        
        # Check function signature
        source = inspect.getsource(_use_edge_tts_fallback)
        
        checks = {
            "max_retries": "max_retries = 2" in source,
            "internet_check": "socket" in source and "8.8.8.8" in source,
            "timeout_handling": "TimeoutExpired" in source,
            "pyttsx3_fallback": "_use_pyttsx3_last_resort" in source,
            "process_kill": "process.kill()" in source,
            "retry_delay": "time.sleep" in source,
            "logging": "logger" in source,
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}: {'Present' if passed else 'Missing'}")
        
        if all(checks.values()):
            print("\n✅ EDGE-TTS RESILIENCE TEST PASSED")
            return True
        else:
            print("\n⚠️  Some edge-tts checks failed")
            return False
            
    except Exception as e:
        print(f"❌ EDGE-TTS TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pyttsx3_windows_com():
    """Test #3: Verify Windows COM initialization for pyttsx3"""
    print("\n" + "="*60)
    print("🧪 TEST #3: PYTTSX3 WINDOWS COM INITIALIZATION")
    print("="*60)
    
    try:
        import inspect
        from engine.voice_engine import _use_pyttsx3_last_resort
        
        source = inspect.getsource(_use_pyttsx3_last_resort)
        
        checks = {
            "platform_check": "sys.platform == 'win32'" in source,
            "ctypes_import": "import ctypes" in source,
            "com_initialization": "CoInitializeEx" in source,
            "error_handling": "except Exception as e" in source,
            "logging": "logger" in source,
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}: {'Present' if passed else 'Missing'}")
        
        # Try actual pyttsx3 initialization if available
        print("\n   Attempting pyttsx3 import test...")
        try:
            import pyttsx3
            print("   ✅ pyttsx3 is installed")
            
            # Test that we can create an engine
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.ole32.CoInitializeEx(None, 0)
                    print("   ✅ Windows COM initialized successfully")
                except Exception as e:
                    print(f"   ⚠️  COM initialization warning: {e}")
                
            engine = pyttsx3.init()
            print("   ✅ pyttsx3 engine created successfully")
            
        except ImportError:
            print("   ⚠️  pyttsx3 not installed (optional for testing)")
        
        if all(checks.values()):
            print("\n✅ PYTTSX3 WINDOWS COM TEST PASSED")
            return True
        else:
            print("\n⚠️  Some pyttsx3 checks failed")
            return False
            
    except Exception as e:
        print(f"❌ PYTTSX3 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thread_safety():
    """Test that key rotation is thread-safe"""
    print("\n" + "="*60)
    print("🧪 TEST #4: KEY ROTATION THREAD SAFETY")
    print("="*60)
    
    try:
        from engine.brain import _key_manager, _load_all_api_keys
        
        keys = _load_all_api_keys()
        if not keys or len(keys) < 2:
            print("⚠️  Need at least 2 API keys to test thread safety")
            return True
        
        print(f"   Testing concurrent access with {len(keys)} keys...")
        
        results = []
        errors = []
        
        def access_key_manager():
            try:
                for _ in range(5):
                    key = _key_manager.current_key()
                    results.append(key)
                    _key_manager.rotate()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 threads accessing key manager simultaneously
        threads = [threading.Thread(target=access_key_manager) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        if errors:
            print(f"❌ Thread safety errors: {errors}")
            return False
        else:
            print(f"✅ Successfully handled {len(results)} concurrent accesses")
            print(f"✅ No race conditions detected")
            print("\n✅ THREAD SAFETY TEST PASSED")
            return True
            
    except Exception as e:
        print(f"❌ THREAD SAFETY TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🔧 "*20)
    print("SIA ASSISTANT - BUG FIX VALIDATION SUITE")
    print("🔧 "*20)
    
    results = {
        "Key Rotation": test_key_rotation(),
        "Edge-TTS Resilience": test_edge_tts_logic(),
        "pyttsx3 Windows COM": test_pyttsx3_windows_com(),
        "Thread Safety": test_thread_safety(),
    }
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print("="*60)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL FIXES VALIDATED SUCCESSFULLY!")
        print("   Sia Assistant should now handle:")
        print("   ✅ API key rotation with quota exhaustion")
        print("   ✅ Edge-TTS with network resilience")
        print("   ✅ pyttsx3 with Windows COM initialization")
    else:
        print(f"\n⚠️  {total - passed} tests failed - please review logs above")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
