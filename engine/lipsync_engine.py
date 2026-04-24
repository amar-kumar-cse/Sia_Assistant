"""Lip-sync pipeline: prepare audio envelope and play with amplitude sync callbacks."""

from __future__ import annotations

import hashlib
import os
import queue
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np
import pygame

from .logger import get_logger

logger = get_logger(__name__)

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover
    librosa = None


class LipSyncEngine:
    """Extracts and replays amplitude envelope in sync with audio playback."""

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        base = cache_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "lipsync_cache")
        self.cache_dir = Path(base)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_cache_files = 50

        self._stop_event = threading.Event()
        self._audio_thread: Optional[threading.Thread] = None
        self._sync_thread: Optional[threading.Thread] = None

    @staticmethod
    def _hash_file(path: str) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _cache_paths(self, audio_file_path: str) -> Tuple[Path, Path]:
        key = self._hash_file(audio_file_path)
        return self.cache_dir / f"{key}.npy", self.cache_dir / f"{key}.ts.npy"

    def _evict_if_needed(self) -> None:
        files = sorted(self.cache_dir.glob("*.npy"), key=lambda p: p.stat().st_mtime)
        while len(files) > self._max_cache_files * 2:
            victim = files.pop(0)
            try:
                victim.unlink(missing_ok=True)
            except Exception:
                pass

    def prepare(self, audio_file_path: str) -> List[Tuple[float, float]]:
        """Return list of (timestamp_sec, amplitude_0_to_1). Cached by audio hash."""
        amp_path, ts_path = self._cache_paths(audio_file_path)
        if amp_path.exists() and ts_path.exists():
            amps = np.load(amp_path)
            ts = np.load(ts_path)
            return [(float(t), float(a)) for t, a in zip(ts.tolist(), amps.tolist())]

        if librosa is None:
            logger.warning("librosa unavailable; using fallback fixed amplitude schedule")
            return self._fallback_prepare(audio_file_path)

        try:
            y, sr = librosa.load(audio_file_path, sr=16000, mono=True)
            rms = librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0]
            if rms.size == 0:
                return self._fallback_prepare(audio_file_path)
            rms = rms.astype(np.float32)
            max_v = float(np.max(rms)) if float(np.max(rms)) > 0 else 1.0
            amps = np.clip(rms / max_v, 0.0, 1.0)
            ts = np.arange(len(amps), dtype=np.float32) * (160.0 / 16000.0)

            np.save(amp_path, amps)
            np.save(ts_path, ts)
            self._evict_if_needed()
            return [(float(t), float(a)) for t, a in zip(ts.tolist(), amps.tolist())]
        except Exception as exc:
            logger.warning("lipsync prepare failed; fallback used: %s", exc)
            return self._fallback_prepare(audio_file_path)

    def _fallback_prepare(self, audio_file_path: str) -> List[Tuple[float, float]]:
        duration = 2.0
        try:
            snd = pygame.mixer.Sound(audio_file_path)
            duration = max(0.5, snd.get_length())
        except Exception:
            pass
        step = 0.033
        out: List[Tuple[float, float]] = []
        t = 0.0
        seq = deque([0.35, 0.65, 0.35])
        while t < duration:
            seq.rotate(-1)
            out.append((t, float(seq[0])))
            t += step
        return out

    def play_with_sync(self, audio_file_path: str, amplitude_callback: Callable[[float], None]) -> None:
        """Play audio in background and emit amplitude every ~33ms."""
        schedule = self.prepare(audio_file_path)
        if not schedule:
            schedule = [(0.0, 0.45)]

        self.stop()
        self._stop_event.clear()

        def _audio_worker() -> None:
            try:
                pygame.mixer.music.load(audio_file_path)
                pygame.mixer.music.play()
            except Exception as exc:
                logger.warning("Audio playback failed; lipsync fallback only: %s", exc)

        def _sync_worker() -> None:
            start = time.monotonic()
            idx = 0
            total = len(schedule)
            try:
                while not self._stop_event.is_set():
                    elapsed = time.monotonic() - start
                    while idx + 1 < total and schedule[idx + 1][0] <= elapsed:
                        idx += 1
                    amplitude_callback(float(schedule[idx][1]))

                    busy = False
                    try:
                        busy = pygame.mixer.music.get_busy()
                    except Exception:
                        pass

                    if not busy and elapsed > schedule[-1][0]:
                        break
                    time.sleep(0.033)
            except Exception as exc:
                logger.warning("Lip sync worker failed: %s", exc)
            finally:
                try:
                    amplitude_callback(0.0)
                except Exception:
                    pass

        self._audio_thread = threading.Thread(target=_audio_worker, name="LipSyncAudio", daemon=True)
        self._sync_thread = threading.Thread(target=_sync_worker, name="LipSyncSync", daemon=True)
        self._audio_thread.start()
        self._sync_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=0.5)
        if self._audio_thread and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=0.5)
        self._sync_thread = None
        self._audio_thread = None
