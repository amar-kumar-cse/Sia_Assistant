"""Lip-sync scheduler converting amplitude to mouth frame states."""

from __future__ import annotations

from typing import Iterable, List, Tuple


class LipSyncScheduler:
    CLOSED = "talk_closed"
    SEMI = "talk_semi"
    OPEN = "talk_open"

    def __init__(self, min_hold_ms: int = 60) -> None:
        self.min_hold_ms = min_hold_ms

    @staticmethod
    def amplitude_to_state(v: float) -> str:
        if v < 0.20:
            return LipSyncScheduler.CLOSED
        if v < 0.55:
            return LipSyncScheduler.SEMI
        return LipSyncScheduler.OPEN

    def to_schedule(self, amplitudes: Iterable[float], step_seconds: float) -> List[Tuple[float, str]]:
        raw: List[Tuple[float, str]] = []
        t = 0.0
        for v in amplitudes:
            raw.append((t, self.amplitude_to_state(float(v))))
            t += step_seconds
        return self._compress(raw)

    def _compress(self, seq: List[Tuple[float, str]]) -> List[Tuple[float, str]]:
        if not seq:
            return []
        out: List[Tuple[float, str]] = [seq[0]]
        hold_sec = self.min_hold_ms / 1000.0
        for ts, st in seq[1:]:
            prev_ts, prev_st = out[-1]
            if st != prev_st and (ts - prev_ts) < hold_sec:
                continue
            if st != prev_st:
                out.append((ts, st))
        return out
