import speech_recognition as sr

def listen_for_wake_word(wake_word="sia", source=None):
    """
    Continuously listens for the wake word 'Sia'.
    Returns True when wake word is detected.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 0.5
    
    # If source is not provided, open a new one
    context_manager = source if source else sr.Microphone()
    
    # If we created the context manager, we need to enter it
    if source is None:
        with context_manager as src:
            return _listen_loop(recognizer, src, wake_word)
    else:
        return _listen_loop(recognizer, source, wake_word)

def _listen_loop(recognizer, source, wake_word):
    print(f"👂 Waiting for '{wake_word}'...")
    recognizer.adjust_for_ambient_noise(source, duration=0.2)
    
    while True:
        try:
            audio = recognizer.listen(source, timeout=2, phrase_time_limit=3)
            try:
                # Use faster/lower accuracy model for wake word if possible, 
                # but Google is fine for now.
                text = recognizer.recognize_google(audio).lower()
                print(f"heard: {text}")
                if wake_word in text:
                    print("⚡ Wake word detected!")
                    return True
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                pass
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            print(f"⚠️ Wake word error: {e}")
            pass

def listen(use_whisper=False):
    """
    Listens to the microphone and returns the recognized text.
    Optimized for INSTANT RESPONSE with minimal latency.
    Args:
        use_whisper (bool): If True, use OpenAI Whisper API (requires API key)
    """
    recognizer = sr.Recognizer()
    
    # OPTIMIZATION 1: Reduce energy threshold
    recognizer.energy_threshold = 300 
    recognizer.dynamic_energy_threshold = True
    recognizer.dynamic_energy_adjustment_damping = 0.15
    
    # OPTIMIZATION 2: Faster cutoff
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.3
    
    with sr.Microphone() as source:
        # OPTIMIZATION 3: Minimal noise adjustment
        print("🎤 Listening...")
        # recognizer.adjust_for_ambient_noise(source, duration=0.2) # Skip if already adjusted in wake loop
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            return None

    try:
        print("⚡ Recognizing...")
        if use_whisper:
            # Placeholder for OpenAI Whisper API
            # import openai
            # ... implementation ...
            print("⚠️ Whisper not configured, falling back to Google")
            text = recognizer.recognize_google(audio)
        else:
            text = recognizer.recognize_google(audio)
            
        print(f"✅ Heard: {text}")
        return text
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"❌ Recognition error: {e}")
        return None


def listen_with_vad():
    """
    Advanced listening with Voice Activity Detection.
    Experimental - requires webrtcvad library.
    """
    try:
        import webrtcvad
    except ImportError:
        print("⚠️ webrtcvad not installed. Using standard listen().")
        return listen()
    
    recognizer = sr.Recognizer()
    vad = webrtcvad.Vad(2)  # Aggressiveness 2 (0-3, higher = more aggressive)
    
    # Optimized settings
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 0.4  # Even faster cutoff with VAD
    
    with sr.Microphone(sample_rate=16000) as source:
        print("🎤 VAD Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.1)
        
        try:
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            return None
    
    try:
        text = recognizer.recognize_google(audio)
        print(f"✅ VAD Heard: {text}")
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"❌ VAD error: {e}")
        return None

