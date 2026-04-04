"""Lightweight in-memory telemetry for Week 5 observability."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TelemetryEvent:
    name: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, object] = field(default_factory=dict)


class TelemetryRecorder:
    """Thread-safe in-memory event and timing recorder."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: List[TelemetryEvent] = []
        self._timings: List[Dict[str, object]] = []

    def record_event(self, name: str, **metadata: object) -> None:
        with self._lock:
            self._events.append(TelemetryEvent(name=name, metadata=dict(metadata)))

    def record_timing(self, name: str, duration_seconds: float, **metadata: object) -> None:
        with self._lock:
            self._timings.append(
                {
                    "name": name,
                    "duration_seconds": duration_seconds,
                    "metadata": dict(metadata),
                    "timestamp": time.time(),
                }
            )

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            return {
                "events": list(self._events),
                "timings": list(self._timings),
            }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._timings.clear()


recorder = TelemetryRecorder()


def record_event(name: str, **metadata: object) -> None:
    recorder.record_event(name, **metadata)


def record_timing(name: str, duration_seconds: float, **metadata: object) -> None:
    recorder.record_timing(name, duration_seconds, **metadata)


def snapshot() -> Dict[str, object]:
    return recorder.snapshot()


def clear() -> None:
    recorder.clear()
