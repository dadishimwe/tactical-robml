"""
============================================================================
SYSTEM MODULE — AUTONOMOUS NAVIGATION
============================================================================
Implements obstacle avoidance using all three HC-SR04 sensors (front, left,
right) and the MPU-6050 IMU. Supports two autonomous modes:
  • EXPLORE  — random-walk obstacle avoidance
  • PATROL   — structured rectangular patrol route
Gracefully degrades to front-only avoidance if side sensors are unavailable.
============================================================================
"""

import threading
import time
import random
import logging
from config import (
    OBSTACLE_STOP_DISTANCE, OBSTACLE_WARN_DISTANCE,
    AUTO_EXPLORE_TURN_MIN, AUTO_EXPLORE_TURN_MAX,
    AUTO_PATROL_FORWARD_SEC, AUTO_PATROL_TURN_SEC,
    SENSOR_SCAN_INTERVAL
)

logger = logging.getLogger(__name__)


class AutonomousNavigator:
    """
    Drives the robot autonomously using sensor fusion from the three
    ultrasonic sensors and IMU orientation data.
    """

    MODES = ("EXPLORE", "PATROL")

    def __init__(self, arduino_controller, imu_monitor=None):
        self._arduino = arduino_controller
        self._imu = imu_monitor
        self._lock = threading.Lock()
        self._running = False
        self._mode = "EXPLORE"
        self._thread: threading.Thread | None = None

        # Expose last sensor readings for the UI radar
        self.dist_front: int = 0
        self.dist_left:  int = 0
        self.dist_right: int = 0
        self.current_action: str = "IDLE"

    # ── Control ─────────────────────────────────────────────────────────────

    def start(self, mode: str = "EXPLORE") -> bool:
        if not self._arduino.motor_connected:
            logger.warning("[Auto] Motor Arduino not connected — cannot start.")
            return False
        mode = mode.upper()
        if mode not in self.MODES:
            mode = "EXPLORE"
        with self._lock:
            if self._running:
                return True
            self._mode = mode
            self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"Auto-{mode}"
        )
        self._thread.start()
        logger.info(f"[Auto] Started in {mode} mode.")
        return True

    def stop(self) -> None:
        with self._lock:
            self._running = False
        self._arduino.send_motor_command("STOP")
        self.current_action = "IDLE"
        logger.info("[Auto] Stopped.")

    def is_running(self) -> bool:
        return self._running

    # ── Main Loop ────────────────────────────────────────────────────────────

    def _run(self) -> None:
        if self._mode == "PATROL":
            self._patrol_loop()
        else:
            self._explore_loop()

    def _explore_loop(self) -> None:
        """Random-walk with 3-sensor obstacle avoidance."""
        while self._running:
            if self._check_safety_halt():
                time.sleep(0.2)
                continue

            distances = self._arduino.get_all_distances()
            self.dist_front = distances.get("front", 0)
            self.dist_left  = distances.get("left", 0)
            self.dist_right = distances.get("right", 0)

            if self.dist_front > 0 and self.dist_front < OBSTACLE_STOP_DISTANCE:
                self._handle_front_obstacle()
            elif self.dist_left > 0 and self.dist_left < OBSTACLE_STOP_DISTANCE:
                self._turn_right(0.4)
            elif self.dist_right > 0 and self.dist_right < OBSTACLE_STOP_DISTANCE:
                self._turn_left(0.4)
            elif self.dist_front > 0 and self.dist_front < OBSTACLE_WARN_DISTANCE:
                # Slow down when approaching
                self._arduino.send_motor_command("SLOW")
                self.current_action = "SLOW"
            else:
                self._arduino.send_motor_command("FORWARD")
                self.current_action = "FORWARD"

            time.sleep(SENSOR_SCAN_INTERVAL)

    def _patrol_loop(self) -> None:
        """Structured rectangular patrol: forward → right → forward → right…"""
        legs = 0
        while self._running:
            if self._check_safety_halt():
                time.sleep(0.2)
                continue

            # Drive forward for one patrol leg, checking sensors
            deadline = time.time() + AUTO_PATROL_FORWARD_SEC
            while self._running and time.time() < deadline:
                if self._check_safety_halt():
                    break
                distances = self._arduino.get_all_distances()
                self.dist_front = distances.get("front", 0)
                self.dist_left  = distances.get("left", 0)
                self.dist_right = distances.get("right", 0)

                if self.dist_front > 0 and self.dist_front < OBSTACLE_STOP_DISTANCE:
                    self._handle_front_obstacle()
                    break
                self._arduino.send_motor_command("FORWARD")
                self.current_action = "FORWARD"
                time.sleep(SENSOR_SCAN_INTERVAL)

            # Turn right at each corner
            if self._running:
                self._turn_right(AUTO_PATROL_TURN_SEC)
                legs += 1

    # ── Safety ──────────────────────────────────────────────────────────────

    def _check_safety_halt(self) -> bool:
        """Return True and stop motors if IMU detects a flip or collision."""
        if self._imu is None:
            return False
        if self._imu.is_flipped:
            self._arduino.send_motor_command("STOP")
            self.current_action = "HALT_FLIP"
            logger.warning("[Auto] Safety halt — robot flipped.")
            return True
        if self._imu.collision_detected:
            self._arduino.send_motor_command("STOP")
            self.current_action = "HALT_COLLISION"
            time.sleep(0.5)
            return True
        return False

    # ── Manoeuvres ───────────────────────────────────────────────────────────

    def _handle_front_obstacle(self) -> None:
        self._arduino.send_motor_command("STOP")
        self.current_action = "STOP"
        time.sleep(0.3)
        self._arduino.send_motor_command("BACKWARD")
        self.current_action = "BACKWARD"
        time.sleep(0.4)
        self._arduino.send_motor_command("STOP")

        # Choose turn direction based on side sensor data
        if self.dist_left > self.dist_right:
            self._turn_left(random.uniform(AUTO_EXPLORE_TURN_MIN, AUTO_EXPLORE_TURN_MAX))
        else:
            self._turn_right(random.uniform(AUTO_EXPLORE_TURN_MIN, AUTO_EXPLORE_TURN_MAX))

    def _turn_left(self, duration: float) -> None:
        self._arduino.send_motor_command("LEFT")
        self.current_action = "TURN_LEFT"
        time.sleep(duration)
        self._arduino.send_motor_command("STOP")

    def _turn_right(self, duration: float) -> None:
        self._arduino.send_motor_command("RIGHT")
        self.current_action = "TURN_RIGHT"
        time.sleep(duration)
        self._arduino.send_motor_command("STOP")

    # ── Status ──────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "mode": self._mode,
            "action": self.current_action,
            "dist_front": self.dist_front,
            "dist_left":  self.dist_left,
            "dist_right": self.dist_right,
        }
