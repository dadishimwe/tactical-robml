# Advanced Robot Control System

A complete web-based robot control system with tactical-themed UI, real-time camera streaming, autonomous navigation, and optional ML object detection.

![Robot Control System](https://img.shields.io/badge/Platform-Raspberry_Pi-red) ![Arduino](https://img.shields.io/badge/Arduino-Uno-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

### Core Functionality
- **Real-time Camera Streaming** - Low-latency MJPEG video feed with HUD overlay
- **Motor Control** - 4-wheel drive with variable speed control (WASD or touch controls)
- **Servo Control** - 4 independent servos for camera gimbal, gripper, or sensor turret
- **Distance Sensing** - HC-SR04 ultrasonic sensor with live distance display
- **Tactical UI** - Call of Duty inspired interface with military aesthetics

### Advanced Features
- **Video Recording** - Save clips with timestamps to local storage
- **Telemetry Logging** - Track commands, distance readings, and export to CSV
- **Autonomous Mode** - Obstacle avoidance with multiple navigation patterns
- **ML Object Detection** - Optional YOLOv8 integration for person/object tracking
- **Remote Access** - Cloudflare Tunnel for secure worldwide access
- **Keyboard Controls** - Full desktop keyboard mapping for power users
- **Mobile Optimized** - Responsive design with touch-friendly controls

---

## Hardware Requirements

### Essential Components
- **Raspberry Pi 4** (2GB+ RAM recommended)
- **2× Arduino Uno** boards
- **4× DC Motors** with wheels (6-12V)
- **4× Servo Motors** (SG90 or similar)
- **L298N Motor Driver** module
- **HC-SR04 Ultrasonic Sensor**
- **Pi Camera Module** (v2 or v3)
- **4× 18650 Li-ion Batteries** (3.7V each)
- **2S BMS** (Battery Management System)
- **USB Power Bank** (10000mAh+, 5V 3A output)
- Jumper wires, breadboard, chassis, mounting hardware

### Optional Components
- Heatsinks for Raspberry Pi and L298N
- Cooling fan for extended operation
- LED indicators for status display
- Physical emergency stop button
- Additional sensors (GPS, IMU, line following)

---

## Quick Start

### 1. Hardware Assembly

Follow the complete wiring diagram in [`diagrams/WIRING_DIAGRAM.md`](diagrams/WIRING_DIAGRAM.md).

**Key Points:**
- Battery pack powers motors/servos only (via L298N)
- USB power bank powers Raspberry Pi and Arduinos
- **Critical:** All grounds must be connected together
- Install 5A fuse in battery circuit

### 2. Arduino Programming

**Upload servo controller to Arduino #1:**
```bash
# Open arduino/servo_controller/servo_controller.ino in Arduino IDE
# Select Board: Arduino Uno
# Select correct Port
# Click Upload
```

**Upload motor controller to Arduino #2:**
```bash
# Open arduino/motor_controller/motor_controller.ino in Arduino IDE
# Upload to second Arduino
```

### 3. Raspberry Pi Setup

**Install Raspberry Pi OS and dependencies:**
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git libcamera-dev python3-picamera2
```

**Install Flask application:**
```bash
cd ~
# Copy flask-app directory to Raspberry Pi
cd flask-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Run the application:**
```bash
python app.py
```

Access at: `http://<raspberry-pi-ip>:5000`

### 4. Cloudflare Tunnel (Optional)

For remote access from anywhere:

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create robot-control
cloudflared tunnel route dns robot-control games.yourdomain.com

# Run tunnel
cloudflared tunnel run robot-control
```

See [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) for detailed instructions.

---

## Project Structure

```
robot-control-system/
├── arduino/
│   ├── servo_controller/
│   │   └── servo_controller.ino      # Arduino #1: Servo control
│   └── motor_controller/
│       └── motor_controller.ino      # Arduino #2: Motor & sensor control
├── flask-app/
│   ├── app.py                        # Main Flask application
│   ├── requirements.txt              # Python dependencies
│   ├── modules/
│   │   ├── camera.py                 # Camera streaming
│   │   ├── serial_comm.py            # Arduino communication
│   │   ├── video_recorder.py         # Video recording
│   │   ├── telemetry.py              # Data logging
│   │   ├── autonomous.py             # Autonomous navigation
│   │   └── ml_detection.py           # ML object detection (optional)
│   ├── templates/
│   │   └── index.html                # Tactical UI interface
│   └── static/
│       ├── css/
│       │   └── style.css             # Tactical theme styling
│       └── js/
│           ├── controls.js           # Main control logic
│           ├── keyboard.js           # Keyboard mapping
│           └── telemetry.js          # Telemetry display
├── diagrams/
│   └── WIRING_DIAGRAM.md             # Complete wiring guide
├── docs/
│   ├── SETUP_GUIDE.md                # Detailed setup instructions
│   └── API_REFERENCE.md              # API documentation
└── README.md                         # This file
```

---

## Keyboard Controls

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| **W** | Forward | **1-4** | Select Servo |
| **S** | Backward | **↑/↓** | Adjust Servo |
| **A** | Turn Left | **Home** | Center All |
| **D** | Turn Right | **PgUp/PgDn** | Presets |
| **Space** | Stop | **R** | Record |
| **Q/E** | Speed ±10 | **H** | Toggle HUD |
| **M** | Toggle ML | **F** | Fullscreen |
| **Esc** | Emergency Stop | **?** | Show Help |

---

## API Endpoints

### Motor Control
- `POST /api/motor/forward` - Move forward
- `POST /api/motor/backward` - Move backward
- `POST /api/motor/left` - Turn left
- `POST /api/motor/right` - Turn right
- `POST /api/motor/stop` - Stop motors
- `POST /api/motor/speed` - Set speed (0-255)

### Servo Control
- `POST /api/servo/set` - Set servo position
- `POST /api/servo/preset` - Load preset
- `POST /api/servo/center` - Center all servos

### Sensors & Status
- `GET /api/distance` - Get distance reading
- `GET /api/status` - Get system status

### Recording & Telemetry
- `POST /api/recording/start` - Start recording
- `POST /api/recording/stop` - Stop recording
- `GET /api/telemetry/stats` - Get statistics
- `GET /api/telemetry/export` - Export CSV

### Autonomous & ML
- `POST /api/autonomous/start` - Start autonomous mode
- `POST /api/ml/toggle` - Toggle ML detection
- `GET /api/ml/detections` - Get detections

See [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) for complete documentation.

---

## Screenshots

### Main Control Interface
The tactical-themed interface features:
- Live camera feed with HUD overlay
- D-pad controls for movement
- Vertical sliders for servo control
- Real-time distance radar
- Telemetry dashboard

### Mobile View
Optimized for landscape orientation with:
- Touch-friendly controls
- Responsive layout
- Full-screen video feed
- Collapsible panels

---

## Configuration

### Camera Settings

Edit `modules/camera.py`:
```python
# Adjust resolution and framerate
resolution=(640, 480)  # Lower for better performance
framerate=30           # Reduce for lower bandwidth
```

### Autonomous Parameters

Edit `modules/autonomous.py`:
```python
self.obstacle_distance = 25  # Stop distance (cm)
self.safe_distance = 40      # Comfortable distance (cm)
self.scan_interval = 0.2     # Distance check interval (seconds)
```

### ML Detection

Enable ML features by uncommenting in `requirements.txt`:
```txt
torch==2.1.0
torchvision==0.16.0
ultralytics==8.0.200
```

Then install:
```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### Camera Not Working
```bash
# Check camera connection
vcgencmd get_camera
# Should show: supported=1 detected=1

# Enable camera interface
sudo raspi-config
# Interface Options → Camera → Enable
```

### Arduino Not Connecting
```bash
# Check USB devices
ls -l /dev/ttyACM* /dev/ttyUSB*

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Motors Not Running
- Check battery voltage (should be 7.4V)
- Verify L298N power LED is on
- Remove ENA/ENB jumpers on L298N
- Check motor wire connections

### Servos Jittering
- Verify 5V power from L298N
- Check common ground connection
- Add capacitors across servo power rails
- Use external 5V BEC if needed

See [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md) for more troubleshooting tips.

---

## Performance Optimization

### Reduce Latency
- Lower camera resolution: `(480, 360)` instead of `(640, 480)`
- Reduce framerate: `20 fps` instead of `30 fps`
- Use hardware-accelerated picamera2

### Reduce CPU Usage
- Disable debug mode in production
- Limit telemetry logging frequency
- Use lightweight ML models (YOLOv8n instead of YOLOv8x)

### Extend Battery Life
- Reduce motor speed when not needed
- Disable ML detection when not in use
- Power off servos when stationary
- Use sleep modes during idle periods

---

## Advanced Usage

### Custom Servo Configurations

**Camera Gimbal + Gripper:**
- Servo 1: Camera Pan (0-180°)
- Servo 2: Camera Tilt (0-180°)
- Servo 3: Gripper Open/Close
- Servo 4: Gripper Wrist Rotate

**Sensor Turret:**
- Servo 1: Ultrasonic Pan
- Servo 2: Ultrasonic Tilt
- Servo 3: Camera Pan
- Servo 4: LED Spotlight

### Autonomous Navigation Modes

**Explore Mode:**
- Random exploration with obstacle avoidance
- Suitable for unknown environments

**Patrol Mode:**
- Follows square pattern
- Returns to starting position

**Wall Following:**
- Maintains distance from wall
- Requires side-facing sensors (simplified version included)

### ML Object Detection

**Enable person tracking:**
```python
from modules.ml_detection import PersonTracker

tracker = PersonTracker(ml_detector, servo_controller)
tracker.start()
# Camera will follow detected persons
```

**Custom object detection:**
```python
ml_detector.set_target_classes(['person', 'car', 'dog'])
ml_detector.set_confidence_threshold(0.7)
```

---

## Security Considerations

### Production Deployment

**Enable Cloudflare Access:**
1. Go to Cloudflare Zero Trust dashboard
2. Create Access application
3. Add authentication method (email, Google, etc.)
4. Restrict access to specific users

**Add API Authentication:**
```python
# In app.py
from functools import wraps

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != 'your-secret-key':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/motor/forward', methods=['POST'])
@require_api_key
def motor_forward():
    # ...
```

**Network Security:**
- Use HTTPS only (automatic with Cloudflare Tunnel)
- Implement rate limiting
- Add CORS restrictions
- Enable firewall on Raspberry Pi

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd robot-control-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r flask-app/requirements.txt

# Run in development mode
cd flask-app
python app.py
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Flask** - Web framework
- **Socket.IO** - Real-time communication
- **OpenCV** - Computer vision
- **Ultralytics YOLOv8** - Object detection
- **Cloudflare** - Tunnel and CDN services
- **Arduino** - Microcontroller platform
- **Raspberry Pi Foundation** - Single-board computer

---

## Support

- **Documentation:** See `docs/` directory
- **Issues:** Report bugs via GitHub Issues
- **Discussions:** Share your builds and ask questions

---

## Roadmap

### Planned Features
- [ ] GPS navigation for outdoor use
- [ ] IMU sensor integration for orientation tracking
- [ ] Voice control via speech recognition
- [ ] Mobile app (React Native)
- [ ] Multi-robot coordination
- [ ] Advanced path planning algorithms
- [ ] Integration with ROS (Robot Operating System)

### Community Requests
- [ ] Support for different motor drivers
- [ ] Alternative camera options (USB webcam)
- [ ] Gesture control
- [ ] VR headset integration
- [ ] Chess playing mode (computer vision + Stockfish)

---

## FAQ

**Q: Can I use a USB webcam instead of Pi Camera?**  
A: Yes, use the `CameraStreamOpenCV` class in `modules/camera.py`.

**Q: Does this work with Arduino Mega or other boards?**  
A: Yes, just adjust pin numbers in the Arduino code.

**Q: Can I add more servos?**  
A: Yes, Arduino Uno has 6 PWM pins. Update the code to use additional pins.

**Q: How much does it cost to build?**  
A: Approximately $150-200 for all components (excluding tools).

**Q: Can I use this for outdoor robots?**  
A: Yes, but add weatherproofing and consider GPS/compass for navigation.

**Q: Is ML detection required?**  
A: No, it's completely optional. The system works fully without it.

---

**Built with ❤️ for robotics enthusiasts**

Enjoy building and controlling your robot! 🤖
