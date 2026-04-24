"""Telemetry facade: in-memory snapshot + persistent async storage."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List

from engine.telemetry_store import store as persistent_store


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


# Start persistent worker once at import time.
persistent_store.start()


def record_event(name: str, **metadata: object) -> None:
    recorder.record_event(name, **metadata)
    metric = metadata.get("metric_value")
    metric_value = float(metric) if isinstance(metric, (int, float)) else None
    session_id = metadata.get("session_id")
    persistent_store.record_event(
        event_type=name,
        metric_value=metric_value,
        session_id=str(session_id) if session_id is not None else None,
        payload={k: v for k, v in metadata.items() if k not in {"metric_value", "session_id"}},
    )


def record_timing(name: str, duration_seconds: float, **metadata: object) -> None:
    recorder.record_timing(name, duration_seconds, **metadata)
    session_id = metadata.get("session_id")
    persistent_store.record_event(
        event_type=f"{name}_latency",
        metric_value=float(duration_seconds),
        session_id=str(session_id) if session_id is not None else None,
        payload={k: v for k, v in metadata.items() if k != "session_id"},
    )


def snapshot() -> Dict[str, object]:
    return recorder.snapshot()


def clear() -> None:
    recorder.clear()


def average_response_time_this_week() -> float:
    """Convenience query for: average response latency in last 7 days."""
    return persistent_store.average_response_time_last_week()
