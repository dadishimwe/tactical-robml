"""
============================================================================
SYSTEM MODULE — TELEMETRY & EVENT LOGGER
============================================================================
Aggregates data from all subsystems into a unified telemetry snapshot.
Maintains an in-memory event log (streamed to the UI) and writes structured
JSON log files to disk for post-mission analysis.
============================================================================
"""

import json
import os
import time
import threading
import logging
from collections import deque
from datetime import datetime
from config import LOG_DIR, MAX_MEMORY_LOGS

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """
    Central telemetry hub. Collects status from all hardware and system
    modules, maintains an event log, and serialises snapshots to disk.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._event_log: deque = deque(maxlen=MAX_MEMORY_LOGS)
        self._log_file: str | None = None
        self._log_handle = None
        os.makedirs(LOG_DIR, exist_ok=True)
        self._open_log_file()

    # ── Log File Management ──────────────────────────────────────────────────

    def _open_log_file(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file = os.path.join(LOG_DIR, f"telemetry_{ts}.jsonl")
        try:
            self._log_handle = open(self._log_file, "a", buffering=1)
            logger.info(f"[Telemetry] Logging to {self._log_file}")
        except Exception as exc:
            logger.warning(f"[Telemetry] Could not open log file: {exc}")

    # ── Event Logging ────────────────────────────────────────────────────────

    def log_event(self, level: str, source: str, message: str) -> None:
        """
        Record a named event. level: INFO | WARN | ERROR | CRITICAL
        """
        entry = {
            "ts":      datetime.now().isoformat(timespec="milliseconds"),
            "level":   level.upper(),
            "source":  source,
            "message": message,
        }
        with self._lock:
            self._event_log.append(entry)
            if self._log_handle:
                try:
                    self._log_handle.write(json.dumps(entry) + "\n")
                except Exception:
                    pass

    def get_recent_events(self, n: int = 100) -> list:
        with self._lock:
            return list(self._event_log)[-n:]

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def build_snapshot(
        self,
        motor_status: dict,
        servo_status: dict,
        autonomous_status: dict,
        imu_status: dict,
        power_status: dict,
        sysmon_status: dict,
        camera_status: dict,
        ml_status: dict,
        led_status: dict,
        recording: bool,
    ) -> dict:
        """Assemble a full telemetry snapshot for WebSocket broadcast."""
        snapshot = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "motor":      motor_status,
            "servo":      servo_status,
            "autonomous": autonomous_status,
            "imu":        imu_status,
            "power":      power_status,
            "system":     sysmon_status,
            "camera":     camera_status,
            "ml":         ml_status,
            "led":        led_status,
            "recording":  recording,
        }
        # Write snapshot to disk
        if self._log_handle:
            try:
                self._log_handle.write(json.dumps({"snapshot": snapshot}) + "\n")
            except Exception:
                pass
        return snapshot

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._log_handle:
            try:
                self._log_handle.close()
            except Exception:
                pass
