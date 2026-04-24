"""
engine/voice.py — Edge TTS Voice Engine with Amplitude Streaming
Bugs fixed:
  - BUG #24: edge_tts → .mp3 save karta hai, .wav nahi — file extension fix
  - BUG #25: soundfile float64 → float32 explicit dtype taaki PyAudio mismatch na ho
  - BUG #26: Purana thread khatam karo pehle naya start karo
  - BUG #27: asyncio.new_event_loop() explicitly Windows pe safe hai QThread ke andar
"""

import asyncio
import os
import threading

import edge_tts
import numpy as np
import pyaudio
import soundfile as sf
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class SiaVoiceThread(QThread):
    """Background thread: TTS generate karo + audio play karo + amplitude emit karo."""
    speaking_done = pyqtSignal()

    def __init__(self, text: str, voice: str, rate: str, amplitude_callback):
        super().__init__()
        self.text = text
        self.voice = voice
        self.rate = rate
        self.amplitude_callback = amplitude_callback
        self._stop_flag = threading.Event()

    def stop_speaking(self):
        self._stop_flag.set()

    def run(self):
        # BUG #27 FIX: Explicit event loop — Windows pe QThread ke andar safe
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._speak())
        finally:
            loop.close()
            self.speaking_done.emit()

    async def _speak(self):
        # BUG #24 FIX: .mp3 save karo — edge_tts MP3 format use karta hai
        tmp_path = "temp/speech.mp3"
        os.makedirs("temp", exist_ok=True)

        try:
            communicate = edge_tts.Communicate(
                self.text, voice=self.voice, rate=self.rate
            )
            await communicate.save(tmp_path)
        except Exception as exc:
            print(f"[Voice] TTS generation failed: {exc}")
            if self.amplitude_callback:
                self.amplitude_callback(0.0)
            return

        # BUG #25 FIX: dtype='float32' explicitly — PyAudio paFloat32 se match
        try:
            audio_data, sample_rate = sf.read(tmp_path, dtype="float32")
        except Exception as exc:
            print(f"[Voice] Audio read failed: {exc}")
            if self.amplitude_callback:
                self.amplitude_callback(0.0)
            return

        # Mono ensure karo
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        p = pyaudio.PyAudio()
        stream = None
        try:
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=sample_rate,
                output=True,
            )

            chunk_size = int(sample_rate * 0.033)  # 33ms chunks ~30fps

            for i in range(0, len(audio_data), chunk_size):
                if self._stop_flag.is_set():
                    break

                chunk = audio_data[i : i + chunk_size]
                if len(chunk) == 0:
                    continue

                # Amplitude calculate karo
                if self.amplitude_callback:
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    normalized = min(rms / 0.15, 1.0)  # 0.15 RMS ~= normal speech
                    self.amplitude_callback(normalized)

                stream.write(chunk.tobytes())

        except Exception as exc:
            print(f"[Voice] Playback error: {exc}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            p.terminate()
            if self.amplitude_callback:
                self.amplitude_callback(0.0)


class SiaVoice(QObject):
    """Main voice controller — main thread se use karo."""
    speaking_done = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.voice = os.environ.get("TTS_VOICE", "hi-IN-SwaraNeural")
        self.rate = os.environ.get("TTS_RATE", "+5%")
        os.makedirs("temp", exist_ok=True)
        self._thread: SiaVoiceThread | None = None

    def speak(self, text: str, amplitude_callback=None):
        # BUG #26 FIX: Pehla thread khatam karo pehle naya shuru karo
        if self._thread is not None and self._thread.isRunning():
            self._thread.stop_speaking()
            self._thread.quit()
            self._thread.wait(800)

        self._thread = SiaVoiceThread(text, self.voice, self.rate, amplitude_callback)
        self._thread.speaking_done.connect(self.speaking_done)
        self._thread.start()

    def stop(self):
        """App close pe voice band karo."""
        if self._thread and self._thread.isRunning():
            self._thread.stop_speaking()
            self._thread.quit()
            self._thread.wait(1000)
