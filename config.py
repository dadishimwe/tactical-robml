"""
============================================================================
TACTICAL ROBOT CONTROL SYSTEM — CENTRAL CONFIGURATION
============================================================================
All hardware pin assignments, thresholds, and application settings are
defined here. Modify this file to adapt the system to your hardware setup
without touching any other source file.
============================================================================
"""

import os

# ── Application ────────────────────────────────────────────────────────────
APP_HOST        = "0.0.0.0"
APP_PORT        = 5000
APP_DEBUG       = False          # NEVER True in production / field deployment
SECRET_KEY      = os.environ.get("ROBOT_SECRET_KEY", "change-me-in-production")
API_KEY         = os.environ.get("ROBOT_API_KEY", "tactical-robot-api-key")

# ── Serial / Arduino ────────────────────────────────────────────────────────
BAUD_RATE           = 115200
SERIAL_TIMEOUT      = 1.0        # seconds
RECONNECT_INTERVAL  = 5.0        # seconds between reconnect attempts
MAX_RECONNECT_TRIES = 10

# ── Camera ──────────────────────────────────────────────────────────────────
CAMERA_RESOLUTION   = (640, 480)
CAMERA_FRAMERATE    = 30
CAMERA_JPEG_QUALITY = 80         # 1-100; lower = less CPU, more compression
ESP32_CAM_URL       = ""         # e.g. "http://192.168.1.50/stream"

# ── Motor Control ───────────────────────────────────────────────────────────
DEFAULT_SPEED   = 200            # 0-255 PWM
MIN_SPEED       = 50
MAX_SPEED       = 255

# ── Servo Control ───────────────────────────────────────────────────────────
SERVO_MIN_ANGLE     = 0
SERVO_MAX_ANGLE     = 180
SERVO_CENTER_ANGLE  = 90
SERVO_SCAN_STEP     = 5          # degrees per sweep step
SERVO_SCAN_DELAY    = 0.05       # seconds between sweep steps

# ── Ultrasonic Sensors ──────────────────────────────────────────────────────
OBSTACLE_STOP_DISTANCE  = 25     # cm — stop and avoid
OBSTACLE_WARN_DISTANCE  = 40     # cm — slow down / warn
SENSOR_SCAN_INTERVAL    = 0.15   # seconds between distance polls

# ── IMU (MPU-6050) ──────────────────────────────────────────────────────────
IMU_I2C_ADDRESS     = 0x68
IMU_FLIP_THRESHOLD  = 60        # degrees — robot considered flipped
IMU_TILT_THRESHOLD  = 30        # degrees — terrain warning

# ── Power / Battery (INA219) ────────────────────────────────────────────────
INA219_I2C_ADDRESS      = 0x40
BATTERY_FULL_VOLTAGE    = 8.4    # V — 2S Li-ion fully charged
BATTERY_EMPTY_VOLTAGE   = 6.4    # V — 2S Li-ion cutoff
BATTERY_WARN_PERCENT    = 20     # % — trigger low-battery alert
BATTERY_CRITICAL_PERCENT= 10     # % — trigger emergency shutdown
SHUNT_OHMS              = 0.1    # Ω — INA219 shunt resistor value

# ── LED Strip (WS2812B) ──────────────────────────────────────────────────────
LED_PIN             = 18         # GPIO pin (BCM) on Raspberry Pi
LED_COUNT           = 16         # number of LEDs in strip
LED_BRIGHTNESS      = 128        # 0-255
LED_FREQ_HZ         = 800000
LED_DMA             = 10
LED_INVERT          = False

# LED colour presets (R, G, B)
LED_COLOR_IDLE      = (0,   80,  0)    # dim green
LED_COLOR_MOVING    = (0,   200, 0)    # bright green
LED_COLOR_AUTONOMOUS= (0,   0,   200)  # blue
LED_COLOR_RECORDING = (200, 0,   0)    # red
LED_COLOR_WARN      = (200, 150, 0)    # amber
LED_COLOR_CRITICAL  = (255, 0,   0)    # bright red
LED_COLOR_NIGHT     = (255, 255, 255)  # white headlights
LED_COLOR_ML        = (150, 0,   200)  # purple
LED_COLOR_OFF       = (0,   0,   0)

# ── Telemetry ────────────────────────────────────────────────────────────────
LOG_DIR             = "data/logs"
VIDEO_DIR           = "data/videos"
MAX_MEMORY_LOGS     = 2000
TELEMETRY_INTERVAL  = 0.5        # seconds between WebSocket telemetry pushes

# ── ML Detection ────────────────────────────────────────────────────────────
ML_MODEL_NAME           = "yolov8n.pt"   # use NCNN export for best Pi perf
ML_CONFIDENCE_THRESHOLD = 0.50
ML_DETECTION_FPS        = 5             # max detection frames per second

# ── Autonomous Navigation ────────────────────────────────────────────────────
AUTO_EXPLORE_TURN_MIN   = 0.5    # seconds
AUTO_EXPLORE_TURN_MAX   = 1.5    # seconds
AUTO_PATROL_FORWARD_SEC = 3.0    # seconds per patrol leg
AUTO_PATROL_TURN_SEC    = 0.7    # seconds for 90° turn

# ── System Monitoring ────────────────────────────────────────────────────────
SYSMON_INTERVAL         = 2.0    # seconds between system metric samples
CPU_WARN_TEMP           = 70.0   # °C
CPU_CRITICAL_TEMP       = 80.0   # °C
