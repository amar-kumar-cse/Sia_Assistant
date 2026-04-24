"""Persistent telemetry store with async batch writer."""

from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import memory
from .logger import get_logger

logger = get_logger(__name__)


class TelemetryStore:
    """Thread-safe, non-blocking telemetry recorder backed by memory.db."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=2000)
        self._running = False
        self._worker: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._run, name="TelemetryWriter", daemon=True)
        self._worker.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._running = False
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)

    def record_event(
        self,
        event_type: str,
        metric_value: Optional[float] = None,
        session_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        item = {
            "event_type": event_type,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": session_id,
            "metric_value": metric_value,
            "payload_json": json.dumps(payload or {}, ensure_ascii=False),
        }
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            logger.warning("Telemetry queue full; dropping event=%s", event_type)

    def _drain_batch(self, max_items: int = 50, timeout: float = 1.0) -> List[Dict[str, Any]]:
        batch: List[Dict[str, Any]] = []
        try:
            first = self._queue.get(timeout=timeout)
            batch.append(first)
        except queue.Empty:
            return batch

        for _ in range(max_items - 1):
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def _run(self) -> None:
        while self._running:
            batch = self._drain_batch(max_items=50, timeout=1.0)
            if not batch:
                continue
            try:
                with memory._db_lock, memory._get_db() as conn:
                    conn.executemany(
                        """
                        INSERT INTO telemetry_event (event_type, ts, session_id, metric_value, payload_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                item["event_type"],
                                item["ts"],
                                item.get("session_id"),
                                item.get("metric_value"),
                                item.get("payload_json"),
                            )
                            for item in batch
                        ],
                    )
            except Exception as exc:
                logger.error("Telemetry batch insert failed: %s", exc)

    @staticmethod
    def average_response_time_last_week() -> float:
        try:
            with memory._db_lock, memory._get_db() as conn:
                row = conn.execute(
                    """
                    SELECT avg(metric_value) AS avg_val
                    FROM telemetry_event
                    WHERE event_type = 'response_latency'
                      AND ts >= datetime('now', '-7 days')
                    """
                ).fetchone()
            val = row["avg_val"] if row and row["avg_val"] is not None else 0.0
            return float(val)
        except Exception as exc:
            logger.error("Telemetry query failed: %s", exc)
            return 0.0


store = TelemetryStore()
