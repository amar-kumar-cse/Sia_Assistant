import os
import requests
import pygame
import io
import time
from dotenv import load_dotenv
import pyttsx3

# Initialize fallback TTS engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Try to set a female voice if available
for voice in voices:
    if "female" in voice.name.lower() or "zira" in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break


load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# Use Turbo model for minimal latency
MODEL_ID = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2")

pygame.mixer.init()

# Global state for animation synchronization
is_speaking = False
is_streaming = False  # New flag for streaming state
speech_start_time = None
speech_duration = 0

def speak(text, callback_started=None, callback_finished=None):
    """
    Synthesizes speech using ElevenLabs API and plays it.
    
    Args:
        text: Text to speak
        callback_started: Function to call when speech starts
        callback_finished: Function to call when speech ends
    """
    global is_speaking, speech_start_time, speech_duration
    
    if not ELEVENLABS_API_KEY or "your_elevenlabs_api_key" in ELEVENLABS_API_KEY:
        print(f"[Sia (Fallback Voice)]: {text}")
        # print("⚠️ Note: ELEVENLABS_API_KEY not configured - Using system voice")
        is_speaking = True
        if callback_started: callback_started()
        
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Fallback voice error: {e}")
            
        is_speaking = False
        if callback_finished: callback_finished()
        return


    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    data = {
        "text": text,
        "model_id": MODEL_ID,  # Using Turbo model
        "voice_settings": {
            "stability": 0.4,  # Slightly lower for faster generation
            "similarity_boost": 0.7,
            "style": 0.3,  # Lower for faster processing
            "use_speaker_boost": True
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            audio_data = io.BytesIO(response.content)
            
            # Mark speaking state
            is_speaking = True
            speech_start_time = time.time()
            
            # Callback when speech starts
            if callback_started:
                callback_started()
            
            # Load and play audio
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Mark speaking complete
            speech_duration = time.time() - speech_start_time
            is_speaking = False
            
            # Callback when speech finishes
            if callback_finished:
                callback_finished()
                
        else:
            print(f"⚠️ ElevenLabs API Error [{response.status_code}]: {response.text}")
            is_speaking = False
            
    except Exception as e:
        print(f"❌ Voice generation failed: {e}")
        is_speaking = False

def stop():
    """Stops any currently playing audio."""
    global is_speaking
    
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    
    is_speaking = False

def get_speaking_state():
    """Returns current speaking state."""
    return is_speaking

def estimate_speech_duration(text):
    """
    Estimates speech duration based on text length.
    Average speaking rate: ~150 words per minute = 2.5 words per second
    """
    word_count = len(text.split())
    estimated_duration = (word_count / 2.5)  # seconds
    return estimated_duration


def speak_chunk(text_chunk, is_first_chunk=False):
    """
    Speak a text chunk with minimal latency.
    Optimized for streaming - starts playing immediately.
    
    Args:
        text_chunk: Short text segment to speak
        is_first_chunk: If True, sets speaking state
    """
    global is_speaking, is_streaming, speech_start_time
    
    if not ELEVENLABS_API_KEY or "your_elevenlabs_api_key" in ELEVENLABS_API_KEY:
        print(f"[Sia Chunk (Fallback)]: {text_chunk}")
        try:
             # Streaming not supported in fallback, just speak
             engine.say(text_chunk)
             engine.runAndWait()
        except:
            pass
        return

    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # Optimized settings for speed
    data = {
        "text": text_chunk,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.3,  # Lower for faster streaming
            "similarity_boost": 0.6,
            "optimize_streaming_latency": 4,  # Max optimization
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        
        if response.status_code == 200:
            audio_data = io.BytesIO(response.content)
            
            # Set speaking state on first chunk
            if is_first_chunk:
                is_speaking = True
                is_streaming = True
                speech_start_time = time.time()
            
            # Play immediately
            pygame.mixer.music.load(audio_data)
            pygame.mixer.music.play()
            
            # Wait for this chunk to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        else:
            print(f"⚠️ Chunk synthesis failed [{response.status_code}]")
            
    except Exception as e:
        print(f"❌ Chunk error: {e}")


def finish_streaming():
    """Call this when streaming is complete."""
    global is_speaking, is_streaming, speech_duration, speech_start_time
    
    if speech_start_time:
        speech_duration = time.time() - speech_start_time
    
    is_speaking = False
    is_streaming = False


def speak_async(text, on_start=None, on_finish=None):
    """Non-blocking speech synthesis. Runs in a background thread."""
    import threading
    def _run():
        if on_start:
            on_start()
        speak(text)
        if on_finish:
            on_finish()
    threading.Thread(target=_run, daemon=True).start()
