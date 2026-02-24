# Tactical Robot Control System v2.0

![UI Screenshot](https://i.imgur.com/example.png) <!-- Replace with actual screenshot -->

A complete overhaul of the original `tactical-robml` project, transforming it into a robust, feature-rich, and professional robotics platform. This version introduces a modular architecture, advanced hardware integration, a redesigned tactical UI, and comprehensive system monitoring.

## Key Features

- **Redesigned Tactical UI**: A dark, information-dense interface with real-time telemetry, system performance sparklines, proximity radar, IMU orientation display, and full mobile responsiveness.
- **Modular Hardware Layer**: All hardware components are now optional and handled with graceful degradation. The system can run in a "simulation" mode on a development machine without any physical hardware connected.
- **Advanced Power System**: Integrated **INA219** sensor for real-time voltage, current, and power monitoring, with accurate battery percentage calculation and low-battery alerts.
- **Enhanced Autonomous Navigation**: The autonomous core now uses three ultrasonic sensors (front, left, right) for better environmental awareness and smarter obstacle avoidance. It also integrates **IMU data** to halt movement if the robot flips over.
- **Full IMU Integration**: An **MPU-6050** provides real-time pitch and roll data, displayed on the UI. It includes a critical flip-detection system that automatically stops the robot to prevent damage.
- **Dynamic Lighting System**: Control a **WS2812B NeoPixel LED strip** with multiple modes (Idle, Night Vision, Warning, ML Active) and a custom color picker. The system provides visual feedback for robot status.
- **Comprehensive System Monitoring**: The UI displays live charts for CPU usage, temperature, and memory, providing insight into the Raspberry Pi's performance.
- **Robust Serial Communication**: Rewritten serial module with automatic reconnection and error handling for both Arduino controllers.
- **Professional Codebase**: The entire Python backend has been refactored for clarity, modularity, and adherence to modern coding standards (PEP8, Black formatting).
- **Dual Camera Support**: The system can seamlessly switch between the primary Raspberry Pi camera and a secondary **ESP32-CAM** for a rear-view or alternative perspective.

## Hardware Stack

This project is built around a Raspberry Pi 4 and two Arduino Unos, orchestrating a suite of sensors and actuators.

| Component | Role | Notes |
|---|---|---|
| **Raspberry Pi 4** | Main Brain | Runs the Flask web server, video streaming, and all high-level logic. |
| **Arduino Uno #1** | Motor Controller | Manages the **TB6612FNG** motor driver, 3× HC-SR04 ultrasonic sensors, and receives INA219 data. |
| **Arduino Uno #2** | Servo Controller | Manages 4× servo motors, the MPU-6050 IMU, and the passive buzzer. |
| **TB6612FNG** | Motor Driver | Efficiently drives the four DC gear motors. A major upgrade over the L298N. |
| **Pi Camera Module** | Primary Vision | Provides the main real-time video feed. |
| **3× HC-SR04** | Proximity Sensing | Front, left, and right sensors for 360° awareness. |
| **INA219** | Power Monitor | Measures battery voltage and current draw. |
| **MPU-6050** | IMU | Senses orientation (pitch/roll) and detects flips. |
| **WS2812B Strip** | Status LEDs | Provides addressable RGB visual feedback. |
| **Passive Buzzer** | Audio Alerts | Gives auditory feedback for warnings and state changes. |
| **ESP32-CAM** | Secondary Camera | Optional rear-view or secondary camera. |

See the [WIRING_DIAGRAM.md](WIRING_DIAGRAM.md) for detailed connection information.

## Software & Architecture

- **Backend**: Python 3, Flask, Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript (with Chart.js)
- **Arduinos**: C++ (Arduino Framework)
- **ML**: YOLOv8 (with optional NCNN support for CPU optimization)

### System Architecture

The system is composed of several independent Python modules that are managed by the main `app.py` file. This modularity ensures that a failure in one component (e.g., a disconnected sensor) does not crash the entire application.

- `app.py`: The main Flask application. It handles HTTP requests, API endpoints, and WebSocket events.
- `modules/`: Contains all the core logic.
  - `hardware/`: Direct interfaces for physical components (Camera, IMU, LEDs, Power, Serial).
  - `system/`: Higher-level logic modules (Autonomous navigation, ML, System Monitoring, Telemetry).
- `arduino/`: Firmware for the two Arduino microcontrollers.
- `templates/`: The main `index.html` file for the UI.
- `config.py`: Central configuration for all system parameters (pins, ports, thresholds, etc.).

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dadishimwe/tactical-robml.git
    cd tactical-robml
    ```

2.  **Install System Dependencies:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-dev i2c-tools
    ```

3.  **Set up Python Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

4.  **Configure Hardware:**
    - Enable I2C and Camera interfaces using `sudo raspi-config`.
    - Flash the firmware from the `arduino/motor_controller` and `arduino/servo_controller` directories to their respective Arduino Unos using the Arduino IDE.
    - Connect all hardware components as detailed in [WIRING_DIAGRAM.md](WIRING_DIAGRAM.md).

5.  **Run the Application:**
    ```bash
    source venv/bin/activate
    python3 app.py
    ```
    Open a web browser and navigate to `http://<your-pi-ip>:5000`.

## Usage

- **Drive Control**: Use the on-screen D-pad or the `W/A/S/D` keys for movement. The spacebar is an emergency stop.
- **Servo Control**: Adjust the four servo sliders to control their positions individually. Use the preset buttons for common positions.
- **Autonomous Mode**: Select an autonomous mode (`EXPLORE` or `PATROL`) and click `START AUTO` to let the robot navigate on its own.
- **ML Detection**: Toggle the `ML DETECT` button to enable or disable real-time object detection on the video feed.
- **Lighting**: Select a pre-defined lighting mode or use the color picker for a custom static color.
- **System Monitoring**: Keep an eye on the right-hand panels to monitor power, orientation, and system performance in real-time.

## Future Improvements

- **Mapping**: Integrate SLAM (Simultaneous Localization and Mapping) to build a map of the environment during autonomous exploration.
- **Path Planning**: Implement A* or other pathfinding algorithms to navigate to specific points on the generated map.
- **WebRTC**: Upgrade the video stream from MJPEG to WebRTC for lower latency and better performance.
- **ROS Integration**: Port the system to the Robot Operating System (ROS) for more standardized and powerful robotics capabilities.
