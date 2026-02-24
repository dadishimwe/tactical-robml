"""
============================================================================
TACTICAL ROBOT CONTROL SYSTEM — MAIN APPLICATION
============================================================================
Flask + Flask-SocketIO web application that orchestrates all hardware and
system modules. Exposes a REST API for motor/servo/LED control and a
WebSocket interface for real-time telemetry streaming.

Run with:
    source venv/bin/activate
    python app.py

For production / headless deployment use the systemd service:
    sudo systemctl start tactical-robot
============================================================================
"""

import os
import time
import logging
import threading
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, Response, request, jsonify, abort
)
from flask_socketio import SocketIO, emit

import config
from modules.hardware.serial_comm    import ArduinoController
from modules.hardware.camera         import CameraManager
from modules.hardware.power_monitor  import PowerMonitor
from modules.hardware.imu            import IMUMonitor
from modules.hardware.led_controller import LEDController
from modules.system.autonomous       import AutonomousNavigator
from modules.system.ml_detection     import MLDetector
from modules.system.sysmon           import SystemMonitor
from modules.system.telemetry        import TelemetryLogger

# ── Logging Setup ────────────────────────────────────────────────────────────

os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.VIDEO_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(config.LOG_DIR,
                         f"app_{datetime.now().strftime('%Y%m%d')}.log")
        ),
    ],
)
logger = logging.getLogger(__name__)

# ── Flask & SocketIO ─────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
socketio = SocketIO(
    app,
    async_mode="eventlet",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# ── Hardware & System Initialisation ─────────────────────────────────────────

logger.info("Initialising hardware modules…")
arduino   = ArduinoController()
camera    = CameraManager()
power     = PowerMonitor()
imu       = IMUMonitor(arduino)
led       = LEDController()
ml        = MLDetector()
navigator = AutonomousNavigator(arduino, imu)
sysmon    = SystemMonitor()
telemetry = TelemetryLogger()

# Inject ML overlay into camera pipeline
camera.set_ml_overlay(ml.process_frame)

logger.info("All modules initialised.")

# ── Application State ─────────────────────────────────────────────────────────

_recording_filename: str | None = None

# ── Auth Decorator ────────────────────────────────────────────────────────────

def require_api_key(f):
    """Protect API endpoints with a simple bearer / header key check."""
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if request.is_json:
            key = key or (request.get_json(silent=True) or {}).get("api_key")
        if key != config.API_KEY:
            abort(401)
        return f(*args, **kwargs)
    return decorated

# ── LED State Helper ──────────────────────────────────────────────────────────

def _update_led_for_state():
    """Derive the correct LED mode from current robot state."""
    if camera.get_status()["recording"]:
        led.set_mode("RECORD")
    elif navigator.is_running():
        led.set_mode("AUTO")
    elif ml.get_status()["enabled"]:
        led.set_mode("ML")
    else:
        led.set_mode("IDLE")

# ── Telemetry Broadcast Thread ────────────────────────────────────────────────

def _telemetry_broadcast():
    """Push a full telemetry snapshot to all connected WebSocket clients."""
    while True:
        try:
            snapshot = telemetry.build_snapshot(
                motor_status      = arduino.get_motor_status(),
                servo_status      = arduino.get_servo_status(),
                autonomous_status = navigator.get_status(),
                imu_status        = imu.get_status(),
                power_status      = power.get_status(),
                sysmon_status     = sysmon.get_status(),
                camera_status     = camera.get_status(),
                ml_status         = ml.get_status(),
                led_status        = led.get_status(),
                recording         = camera.get_status()["recording"],
            )
            socketio.emit("telemetry", snapshot)

            # Targeted alerts
            if power.alert_level == "CRITICAL":
                led.set_mode("CRITICAL")
                socketio.emit("alert", {
                    "level": "CRITICAL", "source": "power",
                    "message": f"Battery critical: {power.battery_percent:.0f}%"
                })
                telemetry.log_event("CRITICAL", "power",
                                    f"Battery at {power.battery_percent:.0f}%")
            elif power.alert_level == "WARN":
                led.set_mode("WARN")
                socketio.emit("alert", {
                    "level": "WARN", "source": "power",
                    "message": f"Battery low: {power.battery_percent:.0f}%"
                })

            if imu.is_flipped:
                socketio.emit("alert", {
                    "level": "CRITICAL", "source": "imu",
                    "message": "Robot flipped — motors halted."
                })
                telemetry.log_event("CRITICAL", "imu", "Flip detected")

            if sysmon.alert_level == "CRITICAL":
                socketio.emit("alert", {
                    "level": "WARN", "source": "sysmon",
                    "message": f"CPU temp critical: {sysmon.cpu_temp}°C"
                })

        except Exception as exc:
            logger.debug(f"[Telemetry] Broadcast error: {exc}")

        time.sleep(config.TELEMETRY_INTERVAL)


threading.Thread(
    target=_telemetry_broadcast, daemon=True, name="TelemetryBroadcast"
).start()

# ============================================================================
# ROUTES — Pages
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    return Response(
        camera.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/esp32_feed")
def esp32_feed():
    """Proxy ESP32-CAM stream if configured."""
    esp_url = config.ESP32_CAM_URL
    if not esp_url:
        return jsonify({"error": "ESP32-CAM URL not configured"}), 404
    import requests as req
    def _proxy():
        try:
            with req.get(esp_url, stream=True, timeout=5) as r:
                for chunk in r.iter_content(chunk_size=4096):
                    yield chunk
        except Exception as exc:
            logger.warning(f"[ESP32] Stream error: {exc}")
    return Response(_proxy(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ============================================================================
# ROUTES — Motor Control API
# ============================================================================

@app.route("/api/motor/<direction>", methods=["POST"])
def motor_command(direction: str):
    valid = {"forward", "backward", "left", "right", "stop", "slow"}
    direction = direction.lower()
    if direction not in valid:
        return jsonify({"success": False, "error": "Invalid direction"}), 400
    ok = arduino.send_motor_command(direction.upper())
    if ok and direction not in ("stop", "slow"):
        led.set_mode("MOVING")
    elif direction == "stop":
        _update_led_for_state()
    telemetry.log_event("INFO", "motor", f"Command: {direction}")
    return jsonify({
        "success": ok,
        "direction": direction,
        "motor_connected": arduino.motor_connected,
    })

@app.route("/api/motor/speed", methods=["POST"])
def set_speed():
    data  = request.get_json(silent=True) or {}
    speed = int(data.get("speed", config.DEFAULT_SPEED))
    speed = max(config.MIN_SPEED, min(config.MAX_SPEED, speed))
    ok    = arduino.send_motor_command(f"SPEED:{speed}")
    return jsonify({"success": ok, "speed": speed})

# ============================================================================
# ROUTES — Servo Control API
# ============================================================================

@app.route("/api/servo/set", methods=["POST"])
def servo_set():
    data  = request.get_json(silent=True) or {}
    servo = int(data.get("servo", 1))
    angle = int(data.get("angle", config.SERVO_CENTER_ANGLE))
    angle = max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, angle))
    ok    = arduino.send_servo_command(f"S{servo}:{angle}")
    return jsonify({
        "success": ok, "servo": servo, "angle": angle,
        "servo_connected": arduino.servo_connected,
    })

@app.route("/api/servo/center", methods=["POST"])
def servo_center():
    ok = arduino.send_servo_command("CENTER")
    return jsonify({"success": ok})

@app.route("/api/servo/preset", methods=["POST"])
def servo_preset():
    data   = request.get_json(silent=True) or {}
    preset = int(data.get("preset", 1))
    ok     = arduino.send_servo_command(f"PRESET:{preset}")
    return jsonify({"success": ok, "preset": preset})

@app.route("/api/servo/scan", methods=["POST"])
def servo_scan():
    """Trigger a 180° sweep scan on servo 1 (ultrasonic mount)."""
    ok = arduino.send_servo_command("SCAN")
    return jsonify({"success": ok})

# ============================================================================
# ROUTES — Autonomous Navigation API
# ============================================================================

@app.route("/api/autonomous/start", methods=["POST"])
def autonomous_start():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "EXPLORE")
    ok   = navigator.start(mode)
    if ok:
        led.set_mode("AUTO")
        telemetry.log_event("INFO", "autonomous", f"Started in {mode} mode")
    return jsonify({"success": ok, "mode": mode})

@app.route("/api/autonomous/stop", methods=["POST"])
def autonomous_stop():
    navigator.stop()
    _update_led_for_state()
    telemetry.log_event("INFO", "autonomous", "Stopped")
    return jsonify({"success": True})

@app.route("/api/autonomous/status", methods=["GET"])
def autonomous_status_route():
    return jsonify(navigator.get_status())

# ============================================================================
# ROUTES — ML Detection API
# ============================================================================

@app.route("/api/ml/toggle", methods=["POST"])
def ml_toggle():
    data   = request.get_json(silent=True) or {}
    enable = data.get("enable", True)
    if enable:
        ok = ml.enable()
    else:
        ml.disable()
        ok = True
    _update_led_for_state()
    status = ml.get_status()
    return jsonify({"success": ok, "enabled": status["enabled"],
                    "available": status["available"]})

@app.route("/api/ml/detections", methods=["GET"])
def ml_detections():
    return jsonify(ml.get_status())

# ============================================================================
# ROUTES — LED Control API
# ============================================================================

@app.route("/api/led/mode", methods=["POST"])
def led_mode():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "IDLE").upper()
    led.set_mode(mode)
    return jsonify({"success": True, "mode": mode})

@app.route("/api/led/color", methods=["POST"])
def led_color():
    data = request.get_json(silent=True) or {}
    r = max(0, min(255, int(data.get("r", 0))))
    g = max(0, min(255, int(data.get("g", 0))))
    b = max(0, min(255, int(data.get("b", 0))))
    led.set_custom_color(r, g, b)
    return jsonify({"success": True, "color": [r, g, b]})

@app.route("/api/led/night", methods=["POST"])
def led_night():
    state = led.toggle_night_mode()
    return jsonify({"success": True, "night_mode": state})

# ============================================================================
# ROUTES — Recording API
# ============================================================================

@app.route("/api/recording/start", methods=["POST"])
def recording_start():
    global _recording_filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _recording_filename = os.path.join(config.VIDEO_DIR, f"mission_{ts}.mp4")
    ok = camera.start_recording(_recording_filename)
    if ok:
        led.set_mode("RECORD")
        telemetry.log_event("INFO", "recording", f"Started: {_recording_filename}")
    return jsonify({"success": ok, "filename": _recording_filename})

@app.route("/api/recording/stop", methods=["POST"])
def recording_stop():
    ok = camera.stop_recording()
    _update_led_for_state()
    telemetry.log_event("INFO", "recording", "Stopped")
    return jsonify({"success": ok, "filename": _recording_filename})

# ============================================================================
# ROUTES — Sensor & Status API
# ============================================================================

@app.route("/api/sensors", methods=["GET"])
def sensors():
    return jsonify({
        "distances": arduino.get_all_distances(),
        "imu":       imu.get_status(),
        "power":     power.get_status(),
    })

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "motor":       arduino.get_motor_status(),
        "servo":       arduino.get_servo_status(),
        "autonomous":  navigator.get_status(),
        "imu":         imu.get_status(),
        "power":       power.get_status(),
        "system":      sysmon.get_status(),
        "camera":      camera.get_status(),
        "ml":          ml.get_status(),
        "led":         led.get_status(),
        "recording":   camera.get_status()["recording"],
        "connections": {
            "motor_arduino": arduino.motor_connected,
            "servo_arduino": arduino.servo_connected,
        },
    })

@app.route("/api/events", methods=["GET"])
def events():
    n = int(request.args.get("n", 100))
    return jsonify({"events": telemetry.get_recent_events(n)})

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on("connect")
def on_connect():
    logger.info(f"[WS] Client connected: {request.sid}")
    emit("connected", {"message": "Tactical Robot Control System online."})

@socketio.on("disconnect")
def on_disconnect():
    logger.info(f"[WS] Client disconnected: {request.sid}")

@socketio.on("request_update")
def on_request_update():
    emit("status_update", arduino.get_motor_status())

@socketio.on("ping_latency")
def on_ping(data):
    emit("pong_latency", data)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info(
        f"Starting Tactical Robot Control System on "
        f"http://{config.APP_HOST}:{config.APP_PORT}"
    )
    try:
        socketio.run(
            app,
            host=config.APP_HOST,
            port=config.APP_PORT,
            debug=config.APP_DEBUG,
        )
    finally:
        logger.info("Shutting down…")
        navigator.stop()
        camera.cleanup()
        led.cleanup()
        arduino.close()
        telemetry.close()
