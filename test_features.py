"""Quick smoke test for all new Sia modules."""
import sys
import os

# Ensure we can find modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  Sia Advanced Features - Smoke Test")
print("=" * 50)

# Test 1: Vision Engine
try:
    import vision_engine
    assert hasattr(vision_engine, 'capture_screen')
    assert hasattr(vision_engine, 'capture_webcam')
    assert hasattr(vision_engine, 'analyze_screen')
    print("✅ 1. Vision Engine - PASS")
except Exception as e:
    print(f"❌ 1. Vision Engine - FAIL: {e}")

# Test 2: OS Automation
try:
    import os_automation
    assert hasattr(os_automation, 'open_app')
    assert hasattr(os_automation, 'set_volume')
    assert hasattr(os_automation, 'organize_files')
    assert hasattr(os_automation, 'get_system_info')
    info = os_automation.get_system_info()
    print(f"✅ 2. OS Automation - PASS (System: {info[:50]}...)")
except Exception as e:
    print(f"❌ 2. OS Automation - FAIL: {e}")

# Test 3: Knowledge Base
try:
    import knowledge_base
    assert hasattr(knowledge_base, 'search_knowledge')
    assert hasattr(knowledge_base, 'index_project')
    kb = knowledge_base.get_knowledge_base()
    # Index our own project as test
    result = kb.index_directory(os.path.dirname(os.path.abspath(__file__)), max_files=20)
    print(f"✅ 3. Knowledge Base - PASS ({result})")
except Exception as e:
    print(f"❌ 3. Knowledge Base - FAIL: {e}")

# Test 4: Web Search
try:
    import web_search
    assert hasattr(web_search, 'search_web')
    assert hasattr(web_search, 'get_latest_news')
    assert hasattr(web_search, 'search_for_brain')
    print("✅ 4. Web Search - PASS")
except Exception as e:
    print(f"❌ 4. Web Search - FAIL: {e}")

# Test 5: Brain - Mood Detection
try:
    import brain
    mood = brain.detect_mood("bohot thak gaya hoon, error nahi hat raha")
    assert mood == "STRESSED"
    mood2 = brain.detect_mood("ho gaya solve! bahut accha laga")
    assert mood2 in ("HAPPY", "EXCITED")
    print(f"✅ 5. Mood Detection - PASS (stress='{mood}', happy='{mood2}')")
except Exception as e:
    print(f"❌ 5. Mood Detection - FAIL: {e}")

# Test 6: Voice Engine - Emotion Settings
try:
    import voice_engine
    settings = voice_engine._get_emotion_settings("HAPPY")
    assert settings["rate"] == "+10%"
    assert settings["pitch"] == "+30Hz"
    settings_sad = voice_engine._get_emotion_settings("SAD")
    assert settings_sad["rate"] == "-10%"
    print(f"✅ 6. Emotional Voice - PASS (HAPPY rate={settings['rate']}, SAD rate={settings_sad['rate']})")
except Exception as e:
    print(f"❌ 6. Emotional Voice - FAIL: {e}")

# Test 7: Actions - New Commands
try:
    import actions
    assert hasattr(actions, '_handle_vision_screen')
    assert hasattr(actions, '_handle_open_app')
    assert hasattr(actions, '_handle_web_search')
    assert hasattr(actions, '_handle_news')
    assert hasattr(actions, '_handle_weather')
    assert hasattr(actions, '_handle_kb_search')
    print("✅ 7. Actions Module - PASS (all new handlers present)")
except Exception as e:
    print(f"❌ 7. Actions Module - FAIL: {e}")

# Test 8: Code Repair Engine
try:
    import code_repair
    assert code_repair.is_code_repair_request("fix this code") == True
    assert code_repair.is_code_repair_request("hello sia") == False
    assert hasattr(code_repair, 'repair_code')
    print("✅ 8. Code-Repair Engine - PASS")
except Exception as e:
    print(f"❌ 8. Code-Repair Engine - FAIL: {e}")

print("\n" + "=" * 50)
print("  Smoke Test Complete!")
print("=" * 50)
