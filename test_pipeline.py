import sys
import logging
logging.basicConfig(level=logging.DEBUG)

def test_pipeline():
    print("--- TESTING LISTEN ENGINE ---")
    try:
        from engine import listen_engine
        print("Please say something within the next 5 seconds (say 'hello')...")
        # Just manually invoke recognizer to see if microphone is physically working
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            text = r.recognize_google(audio)
            print("HEARD:", text)
    except Exception as e:
        print("LISTEN ERROR:", e)

    print("\n--- TESTING BRAIN ENGINE ---")
    try:
        from engine import brain
        response = brain.think("Say hello world simply")
        print("BRAIN REPLIED:", response)
    except Exception as e:
        print("BRAIN ERROR:", e)

    print("\n--- TESTING VOICE ENGINE ---")
    try:
        from engine import voice_engine
        import time
        print("Speaking...")
        def started(): print("Callback config: started")
        def finished(): print("Callback config: finished")
        voice_engine.speak("Hello from Sia", emotion="HAPPY", callback_started=started, callback_finished=finished)
        # Give it a couple of seconds to finish
        time.sleep(3)
        print("VOICE TEST COMPLETE")
    except Exception as e:
        print("VOICE ERROR:", e)

if __name__ == "__main__":
    test_pipeline()
