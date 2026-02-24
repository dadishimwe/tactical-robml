"""
============================================================================
HARDWARE MODULE — SERIAL COMMUNICATION
============================================================================
Thread-safe, auto-reconnecting serial interface for both Arduino controllers.
Implements graceful degradation: if one Arduino disconnects, the other
continues operating and the system alerts the user rather than crashing.
============================================================================
"""

import serial
import serial.tools.list_ports
import threading
import time
import queue
import logging

from config import (
    BAUD_RATE, SERIAL_TIMEOUT, RECONNECT_INTERVAL, MAX_RECONNECT_TRIES
)

logger = logging.getLogger(__name__)


class ArduinoController:
    """
    Manages serial communication with both Arduino controllers.

    Motor Arduino  — handles DC motors, front/left/right HC-SR04 sensors,
                     INA219 power monitor, and WS2812B LED strip.
    Servo Arduino  — handles 4× SG90 servos and MPU-6050 IMU.
    """

    def __init__(self, motor_port: str = None, servo_port: str = None):
        self._baud = BAUD_RATE
        self._timeout = SERIAL_TIMEOUT

        self.motor_serial: serial.Serial | None = None
        self.servo_serial: serial.Serial | None = None
        self.motor_connected = False
        self.servo_connected = False

        self._motor_lock = threading.Lock()
        self._servo_lock = threading.Lock()
        self._motor_responses: queue.Queue = queue.Queue()
        self._servo_responses: queue.Queue = queue.Queue()

        self._motor_reconnect_count = 0
        self._servo_reconnect_count = 0

        # Attempt initial connection
        if motor_port is None or servo_port is None:
            motor_port, servo_port = self._auto_detect_ports()

        self._motor_port = motor_port
        self._servo_port = servo_port
        self._connect_motor(motor_port)
        self._connect_servo(servo_port)

        # Start listener and watchdog threads
        threading.Thread(target=self._listen_motor, daemon=True, name="MotorListener").start()
        threading.Thread(target=self._listen_servo, daemon=True, name="ServoListener").start()
        threading.Thread(target=self._watchdog, daemon=True, name="SerialWatchdog").start()

    # ── Port Detection ──────────────────────────────────────────────────────

    def _auto_detect_ports(self) -> tuple[str | None, str | None]:
        """Probe all USB serial ports for MOTOR_READY / SERVO_READY handshakes."""
        logger.info("[Serial] Auto-detecting Arduino ports…")
        ports = [p for p in serial.tools.list_ports.comports()
                 if "USB" in p.description or "ACM" in p.device]

        motor_port = servo_port = None
        for port in ports:
            try:
                with serial.Serial(port.device, self._baud, timeout=2) as ser:
                    time.sleep(2)
                    if ser.in_waiting > 0:
                        msg = ser.readline().decode("utf-8", errors="ignore").strip()
                        if "MOTOR_READY" in msg:
                            motor_port = port.device
                            logger.info(f"[Serial] Motor controller → {port.device}")
                        elif "SERVO_READY" in msg:
                            servo_port = port.device
                            logger.info(f"[Serial] Servo controller → {port.device}")
            except Exception as exc:
                logger.warning(f"[Serial] Could not probe {port.device}: {exc}")

        return motor_port, servo_port

    # ── Connection Helpers ──────────────────────────────────────────────────

    def _connect_motor(self, port: str | None) -> None:
        if not port:
            logger.warning("[Serial] Motor port not specified — motor features disabled.")
            return
        try:
            self.motor_serial = serial.Serial(port, self._baud, timeout=self._timeout)
            time.sleep(2)
            self.motor_connected = True
            self._motor_reconnect_count = 0
            logger.info(f"[Serial] Motor controller connected on {port}")
        except Exception as exc:
            logger.error(f"[Serial] Motor connection failed: {exc}")
            self.motor_connected = False

    def _connect_servo(self, port: str | None) -> None:
        if not port:
            logger.warning("[Serial] Servo port not specified — servo features disabled.")
            return
        try:
            self.servo_serial = serial.Serial(port, self._baud, timeout=self._timeout)
            time.sleep(2)
            self.servo_connected = True
            self._servo_reconnect_count = 0
            logger.info(f"[Serial] Servo controller connected on {port}")
        except Exception as exc:
            logger.error(f"[Serial] Servo connection failed: {exc}")
            self.servo_connected = False

    # ── Watchdog (auto-reconnect) ───────────────────────────────────────────

    def _watchdog(self) -> None:
        """Periodically attempt to reconnect disconnected Arduinos."""
        while True:
            time.sleep(RECONNECT_INTERVAL)
            if not self.motor_connected and self._motor_reconnect_count < MAX_RECONNECT_TRIES:
                logger.info("[Serial] Attempting motor reconnect…")
                self._motor_reconnect_count += 1
                self._connect_motor(self._motor_port)

            if not self.servo_connected and self._servo_reconnect_count < MAX_RECONNECT_TRIES:
                logger.info("[Serial] Attempting servo reconnect…")
                self._servo_reconnect_count += 1
                self._connect_servo(self._servo_port)

    # ── Listener Threads ───────────────────────────────────────────────────

    def _listen_motor(self) -> None:
        while True:
            if self.motor_connected and self.motor_serial:
                try:
                    if self.motor_serial.in_waiting > 0:
                        raw = self.motor_serial.readline().decode("utf-8", errors="ignore").strip()
                        if raw:
                            self._motor_responses.put(raw)
                except Exception as exc:
                    logger.warning(f"[Motor] Listener error: {exc}")
                    self.motor_connected = False
            time.sleep(0.01)

    def _listen_servo(self) -> None:
        while True:
            if self.servo_connected and self.servo_serial:
                try:
                    if self.servo_serial.in_waiting > 0:
                        raw = self.servo_serial.readline().decode("utf-8", errors="ignore").strip()
                        if raw:
                            self._servo_responses.put(raw)
                except Exception as exc:
                    logger.warning(f"[Servo] Listener error: {exc}")
                    self.servo_connected = False
            time.sleep(0.01)

    # ── Command Senders ────────────────────────────────────────────────────

    def send_motor_command(self, command: str) -> bool:
        if not self.motor_connected:
            return False
        try:
            with self._motor_lock:
                self.motor_serial.write(f"{command}\n".encode())
                self.motor_serial.flush()
            return True
        except Exception as exc:
            logger.error(f"[Motor] Send error: {exc}")
            self.motor_connected = False
            return False

    def send_servo_command(self, command: str) -> bool:
        if not self.servo_connected:
            return False
        try:
            with self._servo_lock:
                self.servo_serial.write(f"{command}\n".encode())
                self.servo_serial.flush()
            return True
        except Exception as exc:
            logger.error(f"[Servo] Send error: {exc}")
            self.servo_connected = False
            return False

    # ── Sensor Queries ─────────────────────────────────────────────────────

    def _query_motor(self, command: str, prefix: str, timeout: float = 1.0) -> str | None:
        """Send a command and wait for a prefixed response."""
        if not self.motor_connected:
            return None
        # Drain stale responses
        while not self._motor_responses.empty():
            self._motor_responses.get_nowait()
        self.send_motor_command(command)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._motor_responses.empty():
                resp = self._motor_responses.get()
                if resp.startswith(prefix):
                    return resp
            time.sleep(0.01)
        return None

    def _query_servo(self, command: str, prefix: str, timeout: float = 1.0) -> str | None:
        if not self.servo_connected:
            return None
        while not self._servo_responses.empty():
            self._servo_responses.get_nowait()
        self.send_servo_command(command)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._servo_responses.empty():
                resp = self._servo_responses.get()
                if resp.startswith(prefix):
                    return resp
            time.sleep(0.01)
        return None

    def get_distance_front(self) -> int:
        resp = self._query_motor("DF", "DIST_F:")
        return int(resp.split(":")[1]) if resp else 0

    def get_distance_left(self) -> int:
        resp = self._query_motor("DL", "DIST_L:")
        return int(resp.split(":")[1]) if resp else 0

    def get_distance_right(self) -> int:
        resp = self._query_motor("DR", "DIST_R:")
        return int(resp.split(":")[1]) if resp else 0

    def get_all_distances(self) -> dict:
        resp = self._query_motor("DA", "DIST_ALL:")
        if resp:
            try:
                parts = resp.split(":")[1].split(",")
                return {"front": int(parts[0]), "left": int(parts[1]), "right": int(parts[2])}
            except Exception:
                pass
        return {"front": 0, "left": 0, "right": 0}

    def get_imu_data(self) -> dict:
        resp = self._query_servo("IMU", "IMU:")
        if resp:
            try:
                parts = resp.split(":")[1].split(",")
                return {
                    "pitch": float(parts[0]),
                    "roll":  float(parts[1]),
                    "yaw":   float(parts[2]),
                    "ax": float(parts[3]),
                    "ay": float(parts[4]),
                    "az": float(parts[5]),
                }
            except Exception:
                pass
        return {"pitch": 0.0, "roll": 0.0, "yaw": 0.0, "ax": 0.0, "ay": 0.0, "az": 0.0}

    def get_motor_status(self) -> dict:
        resp = self._query_motor("?", "STATUS:")
        if resp:
            try:
                parts = resp.split(":")[1].split(",")
                return {
                    "connected": True,
                    "speed": int(parts[0]),
                    "direction": parts[1],
                    "distance_front": int(parts[2]),
                }
            except Exception:
                pass
        return {"connected": self.motor_connected, "speed": 0, "direction": "UNKNOWN", "distance_front": 0}

    def get_servo_status(self) -> dict:
        resp = self._query_servo("?", "STATUS:")
        if resp:
            try:
                positions = [int(x) for x in resp.split(":")[1].split(",")]
                return {"connected": True, "positions": positions}
            except Exception:
                pass
        return {"connected": self.servo_connected, "positions": [90, 90, 90, 90]}

    # ── LED Control (sent to Motor Arduino) ───────────────────────────────

    def set_led_mode(self, mode: str) -> bool:
        """
        mode: IDLE | MOVING | AUTO | RECORD | WARN | CRITICAL | NIGHT | ML | OFF
        """
        return self.send_motor_command(f"LED:{mode}")

    def set_led_color(self, r: int, g: int, b: int) -> bool:
        return self.send_motor_command(f"LEDC:{r},{g},{b}")

    # ── Cleanup ────────────────────────────────────────────────────────────

    def close(self) -> None:
        self.motor_connected = False
        self.servo_connected = False
        for ser in (self.motor_serial, self.servo_serial):
            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
        logger.info("[Serial] All connections closed.")

    def __del__(self):
        self.close()
