"""
============================================================================
HARDWARE MODULE — POWER MONITOR (INA219)
============================================================================
Reads voltage, current, and power from the INA219 I2C sensor.
Calculates battery percentage, triggers alerts, and logs consumption history.
Falls back gracefully when the sensor is not present (e.g., dev environment).
============================================================================
"""

import time
import threading
import logging
from collections import deque
from config import (
    INA219_I2C_ADDRESS, BATTERY_FULL_VOLTAGE, BATTERY_EMPTY_VOLTAGE,
    BATTERY_WARN_PERCENT, BATTERY_CRITICAL_PERCENT, SHUNT_OHMS,
    MAX_MEMORY_LOGS
)

logger = logging.getLogger(__name__)

try:
    from ina219 import INA219, DeviceRangeError
    INA219_AVAILABLE = True
except ImportError:
    INA219_AVAILABLE = False
    logger.warning("[Power] ina219 library not found — using simulated data.")


class PowerMonitor:
    """
    Continuously samples the INA219 and maintains a rolling history of
    voltage, current, and power readings.
    """

    def __init__(self):
        self._sensor = None
        self._available = False
        self._lock = threading.Lock()

        # Latest readings
        self.voltage: float = 0.0
        self.current_ma: float = 0.0
        self.power_mw: float = 0.0
        self.battery_percent: float = 100.0

        # Rolling history (for UI sparkline charts)
        self.voltage_history: deque = deque(maxlen=MAX_MEMORY_LOGS)
        self.current_history: deque = deque(maxlen=MAX_MEMORY_LOGS)
        self.power_history: deque = deque(maxlen=MAX_MEMORY_LOGS)

        # Alert state
        self.alert_level: str = "OK"   # OK | WARN | CRITICAL

        self._init_sensor()
        threading.Thread(target=self._sample_loop, daemon=True, name="PowerMonitor").start()

    # ── Initialisation ──────────────────────────────────────────────────────

    def _init_sensor(self) -> None:
        if not INA219_AVAILABLE:
            return
        try:
            self._sensor = INA219(SHUNT_OHMS, address=INA219_I2C_ADDRESS)
            self._sensor.configure()
            self._available = True
            logger.info("[Power] INA219 initialised.")
        except Exception as exc:
            logger.warning(f"[Power] INA219 init failed: {exc}")
            self._available = False

    # ── Sampling Loop ───────────────────────────────────────────────────────

    def _sample_loop(self) -> None:
        while True:
            self._read()
            time.sleep(1.0)

    def _read(self) -> None:
        if self._available and self._sensor:
            try:
                with self._lock:
                    self.voltage = self._sensor.voltage()
                    self.current_ma = self._sensor.current()
                    self.power_mw = self._sensor.power()
            except Exception as exc:
                logger.debug(f"[Power] Read error: {exc}")
                # Retain last known values
        else:
            # Simulate a slowly discharging battery for development
            with self._lock:
                self.voltage = max(BATTERY_EMPTY_VOLTAGE, self.voltage - 0.001)
                self.current_ma = 350.0
                self.power_mw = self.voltage * (self.current_ma / 1000.0) * 1000.0

        with self._lock:
            self.battery_percent = self._voltage_to_percent(self.voltage)
            self.voltage_history.append(round(self.voltage, 2))
            self.current_history.append(round(self.current_ma, 1))
            self.power_history.append(round(self.power_mw, 1))
            self._update_alert()

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _voltage_to_percent(self, voltage: float) -> float:
        span = BATTERY_FULL_VOLTAGE - BATTERY_EMPTY_VOLTAGE
        if span <= 0:
            return 100.0
        pct = (voltage - BATTERY_EMPTY_VOLTAGE) / span * 100.0
        return max(0.0, min(100.0, round(pct, 1)))

    def _update_alert(self) -> None:
        if self.battery_percent <= BATTERY_CRITICAL_PERCENT:
            self.alert_level = "CRITICAL"
        elif self.battery_percent <= BATTERY_WARN_PERCENT:
            self.alert_level = "WARN"
        else:
            self.alert_level = "OK"

    # ── Public API ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            return {
                "available": self._available or not INA219_AVAILABLE,
                "voltage": round(self.voltage, 2),
                "current_ma": round(self.current_ma, 1),
                "power_mw": round(self.power_mw, 1),
                "battery_percent": self.battery_percent,
                "alert_level": self.alert_level,
                "voltage_history": list(self.voltage_history)[-60:],
                "current_history": list(self.current_history)[-60:],
            }
