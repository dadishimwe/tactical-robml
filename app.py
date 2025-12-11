"""
============================================================================
ROBOT CONTROL SYSTEM - MAIN APPLICATION
============================================================================

Flask web server for controlling robot via web interface.

Features:
  - Live camera streaming (MJPEG)
  - Motor control via serial
  - Servo control via serial
  - Video recording
  - Distance logging
  - Telemetry dashboard
  - Autonomous modes
  - ML object detection (optional)

Author: Robot Control System
Version: 1.0
============================================================================
"""

from flask import Flask, render_template, Response, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import sys
from datetime import datetime

# Import custom modules
from modules.camera import CameraStream
from modules.serial_comm import ArduinoController
from modules.video_recorder import VideoRecorder
from modules.telemetry import TelemetryLogger
from modules.autonomous import AutonomousController

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robot-control-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
camera = CameraStream()
arduino = ArduinoController()
recorder = VideoRecorder()
telemetry = TelemetryLogger()
autonomous = AutonomousController(arduino, camera)

# Global state
app_state = {
    'recording': False,
    'autonomous': False,
    'ml_enabled': False,
    'speed': 200,
    'servo_positions': [90, 90, 90, 90]
}

# ============================================================================
# WEB ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main control interface"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """MJPEG video streaming route"""
    return Response(
        camera.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# ============================================================================
# API ENDPOINTS - MOTOR CONTROL
# ============================================================================

@app.route('/api/motor/forward', methods=['POST'])
def motor_forward():
    """Move robot forward"""
    if app_state['autonomous']:
        return jsonify({'error': 'Autonomous mode active'}), 400
    
    success = arduino.send_motor_command('F')
    telemetry.log_command('motor', 'forward')
    return jsonify({'success': success})

@app.route('/api/motor/backward', methods=['POST'])
def motor_backward():
    """Move robot backward"""
    if app_state['autonomous']:
        return jsonify({'error': 'Autonomous mode active'}), 400
    
    success = arduino.send_motor_command('B')
    telemetry.log_command('motor', 'backward')
    return jsonify({'success': success})

@app.route('/api/motor/left', methods=['POST'])
def motor_left():
    """Turn robot left"""
    if app_state['autonomous']:
        return jsonify({'error': 'Autonomous mode active'}), 400
    
    success = arduino.send_motor_command('L')
    telemetry.log_command('motor', 'left')
    return jsonify({'success': success})

@app.route('/api/motor/right', methods=['POST'])
def motor_right():
    """Turn robot right"""
    if app_state['autonomous']:
        return jsonify({'error': 'Autonomous mode active'}), 400
    
    success = arduino.send_motor_command('R')
    telemetry.log_command('motor', 'right')
    return jsonify({'success': success})

@app.route('/api/motor/stop', methods=['POST'])
def motor_stop():
    """Stop all motors"""
    success = arduino.send_motor_command('S')
    telemetry.log_command('motor', 'stop')
    return jsonify({'success': success})

@app.route('/api/motor/speed', methods=['POST'])
def set_speed():
    """Set motor speed (0-255)"""
    data = request.get_json()
    speed = data.get('speed', 200)
    
    if not 0 <= speed <= 255:
        return jsonify({'error': 'Speed must be 0-255'}), 400
    
    success = arduino.send_motor_command(f'SP{speed}')
    if success:
        app_state['speed'] = speed
        telemetry.log_command('motor', f'speed_{speed}')
    
    return jsonify({'success': success, 'speed': speed})

# ============================================================================
# API ENDPOINTS - SERVO CONTROL
# ============================================================================

@app.route('/api/servo/set', methods=['POST'])
def set_servo():
    """Set individual servo position"""
    data = request.get_json()
    servo_num = data.get('servo', 1)
    angle = data.get('angle', 90)
    
    if not 1 <= servo_num <= 4:
        return jsonify({'error': 'Servo must be 1-4'}), 400
    
    if not 0 <= angle <= 180:
        return jsonify({'error': 'Angle must be 0-180'}), 400
    
    success = arduino.send_servo_command(f'S{servo_num}{angle:03d}')
    if success:
        app_state['servo_positions'][servo_num - 1] = angle
        telemetry.log_command('servo', f's{servo_num}_{angle}')
    
    return jsonify({'success': success, 'servo': servo_num, 'angle': angle})

@app.route('/api/servo/preset', methods=['POST'])
def servo_preset():
    """Load servo preset"""
    data = request.get_json()
    preset = data.get('preset', 0)
    
    if not 0 <= preset <= 6:
        return jsonify({'error': 'Preset must be 0-6'}), 400
    
    success = arduino.send_servo_command(f'P{preset}')
    telemetry.log_command('servo', f'preset_{preset}')
    return jsonify({'success': success, 'preset': preset})

@app.route('/api/servo/center', methods=['POST'])
def servo_center():
    """Center all servos"""
    success = arduino.send_servo_command('C')
    if success:
        app_state['servo_positions'] = [90, 90, 90, 90]
        telemetry.log_command('servo', 'center')
    
    return jsonify({'success': success})

# ============================================================================
# API ENDPOINTS - SENSOR & STATUS
# ============================================================================

@app.route('/api/distance', methods=['GET'])
def get_distance():
    """Get current distance reading"""
    distance = arduino.get_distance()
    telemetry.log_distance(distance)
    return jsonify({'distance': distance})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    motor_status = arduino.get_motor_status()
    servo_status = arduino.get_servo_status()
    
    return jsonify({
        'motor': motor_status,
        'servo': servo_status,
        'recording': app_state['recording'],
        'autonomous': app_state['autonomous'],
        'ml_enabled': app_state['ml_enabled'],
        'speed': app_state['speed'],
        'uptime': telemetry.get_uptime()
    })

# ============================================================================
# API ENDPOINTS - VIDEO RECORDING
# ============================================================================

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """Start video recording"""
    if app_state['recording']:
        return jsonify({'error': 'Already recording'}), 400
    
    filename = recorder.start_recording(camera)
    app_state['recording'] = True
    telemetry.log_command('recording', 'start')
    
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """Stop video recording"""
    if not app_state['recording']:
        return jsonify({'error': 'Not recording'}), 400
    
    filename = recorder.stop_recording()
    app_state['recording'] = False
    telemetry.log_command('recording', 'stop')
    
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/recordings', methods=['GET'])
def list_recordings():
    """List all recorded videos"""
    recordings = recorder.list_recordings()
    return jsonify({'recordings': recordings})

# ============================================================================
# API ENDPOINTS - AUTONOMOUS MODE
# ============================================================================

@app.route('/api/autonomous/start', methods=['POST'])
def start_autonomous():
    """Start autonomous obstacle avoidance"""
    if app_state['autonomous']:
        return jsonify({'error': 'Already in autonomous mode'}), 400
    
    success = autonomous.start()
    if success:
        app_state['autonomous'] = True
        telemetry.log_command('autonomous', 'start')
    
    return jsonify({'success': success})

@app.route('/api/autonomous/stop', methods=['POST'])
def stop_autonomous():
    """Stop autonomous mode"""
    if not app_state['autonomous']:
        return jsonify({'error': 'Not in autonomous mode'}), 400
    
    autonomous.stop()
    app_state['autonomous'] = False
    telemetry.log_command('autonomous', 'stop')
    
    return jsonify({'success': True})

# ============================================================================
# API ENDPOINTS - TELEMETRY
# ============================================================================

@app.route('/api/telemetry/logs', methods=['GET'])
def get_telemetry():
    """Get telemetry logs"""
    logs = telemetry.get_recent_logs(limit=100)
    return jsonify({'logs': logs})

@app.route('/api/telemetry/export', methods=['GET'])
def export_telemetry():
    """Export telemetry as CSV"""
    csv_file = telemetry.export_csv()
    return send_from_directory('data/logs', csv_file, as_attachment=True)

@app.route('/api/telemetry/stats', methods=['GET'])
def get_stats():
    """Get telemetry statistics"""
    stats = telemetry.get_statistics()
    return jsonify(stats)

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('status', {'connected': True})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_update')
def handle_update_request():
    """Send real-time updates to client"""
    distance = arduino.get_distance()
    emit('distance_update', {'distance': distance})
    emit('status_update', {
        'recording': app_state['recording'],
        'autonomous': app_state['autonomous'],
        'speed': app_state['speed']
    })

# ============================================================================
# ML INTEGRATION (OPTIONAL)
# ============================================================================

try:
    from modules.ml_detection import MLDetector
    ml_detector = MLDetector(camera)
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("ML module not available. Install dependencies to enable.")

@app.route('/api/ml/toggle', methods=['POST'])
def toggle_ml():
    """Toggle ML object detection"""
    if not ML_AVAILABLE:
        return jsonify({'error': 'ML module not available.'}), 400
    
    data = request.get_json()
    enable = data.get('enable', False)
    
    if enable:
        ml_detector.start()
        app_state['ml_enabled'] = True
    else:
        ml_detector.stop()
        app_state['ml_enabled'] = False
    
    telemetry.log_command('ml', 'enabled' if enable else 'disabled')
    return jsonify({'success': True, 'enabled': app_state['ml_enabled']})

@app.route('/api/ml/detections', methods=['GET'])
def get_detections():
    """Get current ML detections"""
    if not ML_AVAILABLE or not app_state['ml_enabled']:
        return jsonify({'detections': []})
    
    detections = ml_detector.get_detections()
    return jsonify({'detections': detections})

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("ROBOT CONTROL SYSTEM - Starting Server")
    print("=" * 70)
    print(f"Camera: {'Available' if camera.is_available() else 'Not Found'}")
    print(f"Arduino Motor Controller: {'Connected' if arduino.motor_connected else 'Not Connected'}")
    print(f"Arduino Servo Controller: {'Connected' if arduino.servo_connected else 'Not Connected'}")
    print(f"ML Detection: {'Available' if ML_AVAILABLE else 'Not Available'}")
    print("=" * 70)
    print("Starting web server on http://0.0.0.0:5000")
    print("=" * 70)
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
