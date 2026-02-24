"""
============================================================================
HARDWARE MODULE — IMU (MPU-6050 via Servo Arduino)
============================================================================
Reads pitch, roll, yaw and accelerometer data forwarded from the servo
Arduino over serial. Detects flip-over and terrain-tilt events and
maintains a rolling history for the UI orientation widget.
============================================================================
"""

import math
import threading
import time
import logging
from collections import deque
from config import IMU_FLIP_THRESHOLD, IMU_TILT_THRESHOLD, MAX_MEMORY_LOGS

logger = logging.getLogger(__name__)


class IMUMonitor:
    """
    Consumes IMU data from the ArduinoController and exposes processed
    orientation state to the rest of the application.
    """

    def __init__(self, arduino_controller):
        self._arduino = arduino_controller
        self._lock = threading.Lock()

        self.pitch: float = 0.0
        self.roll: float  = 0.0
        self.yaw: float   = 0.0
        self.ax: float    = 0.0
        self.ay: float    = 0.0
        self.az: float    = 0.0

        self.is_flipped: bool = False
        self.is_tilted: bool  = False
        self.collision_detected: bool = False
        self._last_az: float  = 9.8   # ~1g

        self.pitch_history: deque = deque(maxlen=MAX_MEMORY_LOGS)
        self.roll_history:  deque = deque(maxlen=MAX_MEMORY_LOGS)

        threading.Thread(target=self._poll_loop, daemon=True, name="IMUMonitor").start()

    # ── Polling ─────────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while True:
            if self._arduino.servo_connected:
                data = self._arduino.get_imu_data()
                with self._lock:
                    self.pitch = data["pitch"]
                    self.roll  = data["roll"]
                    self.yaw   = data["yaw"]
                    self.ax    = data["ax"]
                    self.ay    = data["ay"]
                    self.az    = data["az"]

                    self.is_flipped = abs(self.pitch) > IMU_FLIP_THRESHOLD or \
                                      abs(self.roll)  > IMU_FLIP_THRESHOLD

                    self.is_tilted  = abs(self.pitch) > IMU_TILT_THRESHOLD or \
                                      abs(self.roll)  > IMU_TILT_THRESHOLD

                    # Detect sudden jolt (collision) via Z-axis spike
                    delta_az = abs(self.az - self._last_az)
                    self.collision_detected = delta_az > 4.0
                    self._last_az = self.az

                    self.pitch_history.append(round(self.pitch, 1))
                    self.roll_history.append(round(self.roll, 1))

                    if self.is_flipped:
                        logger.warning("[IMU] FLIP DETECTED — motors should be disabled.")
                    if self.collision_detected:
                        logger.warning("[IMU] COLLISION DETECTED.")
            time.sleep(0.1)

    # ── Public API ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            return {
                "pitch": round(self.pitch, 1),
                "roll":  round(self.roll, 1),
                "yaw":   round(self.yaw, 1),
                "ax": round(self.ax, 2),
                "ay": round(self.ay, 2),
                "az": round(self.az, 2),
                "is_flipped": self.is_flipped,
                "is_tilted":  self.is_tilted,
                "collision":  self.collision_detected,
                "pitch_history": list(self.pitch_history)[-60:],
                "roll_history":  list(self.roll_history)[-60:],
            }
