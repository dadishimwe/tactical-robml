"""
============================================================================
SYSTEM MODULE — SYSTEM PERFORMANCE MONITOR
============================================================================
Samples CPU, memory, temperature, disk, and network metrics using psutil.
Maintains rolling histories for the UI performance dashboard.
Emits alerts when CPU temperature exceeds safe thresholds.
============================================================================
"""

import threading
import time
import logging
import os
from collections import deque
from config import (
    SYSMON_INTERVAL, CPU_WARN_TEMP, CPU_CRITICAL_TEMP, MAX_MEMORY_LOGS
)

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("[SysMon] psutil not installed — install with: pip install psutil")


def _read_cpu_temp() -> float:
    """Read Raspberry Pi CPU temperature from the thermal zone sysfs node."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 0.0


class SystemMonitor:
    """
    Continuously samples system performance metrics and maintains rolling
    histories for dashboard sparkline charts.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Latest snapshot
        self.cpu_percent: float  = 0.0
        self.cpu_temp: float     = 0.0
        self.mem_percent: float  = 0.0
        self.mem_used_mb: float  = 0.0
        self.mem_total_mb: float = 0.0
        self.disk_percent: float = 0.0
        self.net_sent_kb: float  = 0.0
        self.net_recv_kb: float  = 0.0
        self.uptime_sec: float   = 0.0
        self.alert_level: str    = "OK"

        # Rolling histories
        self.cpu_history:  deque = deque(maxlen=MAX_MEMORY_LOGS)
        self.temp_history: deque = deque(maxlen=MAX_MEMORY_LOGS)
        self.mem_history:  deque = deque(maxlen=MAX_MEMORY_LOGS)

        self._prev_net_sent = 0
        self._prev_net_recv = 0
        self._start_time = time.time()

        threading.Thread(target=self._sample_loop, daemon=True, name="SysMon").start()

    # ── Sampling ─────────────────────────────────────────────────────────────

    def _sample_loop(self) -> None:
        while True:
            self._sample()
            time.sleep(SYSMON_INTERVAL)

    def _sample(self) -> None:
        with self._lock:
            if PSUTIL_AVAILABLE:
                self.cpu_percent  = psutil.cpu_percent(interval=None)
                mem               = psutil.virtual_memory()
                self.mem_percent  = mem.percent
                self.mem_used_mb  = round(mem.used / 1024 / 1024, 1)
                self.mem_total_mb = round(mem.total / 1024 / 1024, 1)
                disk              = psutil.disk_usage("/")
                self.disk_percent = disk.percent
                net               = psutil.net_io_counters()
                self.net_sent_kb  = round((net.bytes_sent - self._prev_net_sent) / 1024, 1)
                self.net_recv_kb  = round((net.bytes_recv - self._prev_net_recv) / 1024, 1)
                self._prev_net_sent = net.bytes_sent
                self._prev_net_recv = net.bytes_recv

            self.cpu_temp   = _read_cpu_temp()
            self.uptime_sec = round(time.time() - self._start_time, 0)

            self.cpu_history.append(round(self.cpu_percent, 1))
            self.temp_history.append(self.cpu_temp)
            self.mem_history.append(round(self.mem_percent, 1))

            if self.cpu_temp >= CPU_CRITICAL_TEMP:
                self.alert_level = "CRITICAL"
            elif self.cpu_temp >= CPU_WARN_TEMP:
                self.alert_level = "WARN"
            else:
                self.alert_level = "OK"

    # ── Public API ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            return {
                "cpu_percent":  round(self.cpu_percent, 1),
                "cpu_temp":     self.cpu_temp,
                "mem_percent":  round(self.mem_percent, 1),
                "mem_used_mb":  self.mem_used_mb,
                "mem_total_mb": self.mem_total_mb,
                "disk_percent": round(self.disk_percent, 1),
                "net_sent_kb":  self.net_sent_kb,
                "net_recv_kb":  self.net_recv_kb,
                "uptime_sec":   self.uptime_sec,
                "alert_level":  self.alert_level,
                "cpu_history":  list(self.cpu_history)[-60:],
                "temp_history": list(self.temp_history)[-60:],
                "mem_history":  list(self.mem_history)[-60:],
            }
