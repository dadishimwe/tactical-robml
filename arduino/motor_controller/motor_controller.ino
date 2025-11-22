/*
 * ============================================================================
 * ARDUINO #2 - MOTOR & SENSOR CONTROLLER
 * ============================================================================
 * 
 * Purpose: Controls 4 DC motors via L298N driver and HC-SR04 ultrasonic sensor
 * 
 * Hardware:
 *   - Arduino Uno
 *   - L298N Motor Driver
 *   - 4× DC Motors (connected as 2 pairs: left/right)
 *   - HC-SR04 Ultrasonic Distance Sensor
 *   - Connected to Raspberry Pi via USB serial
 * 
 * Pin Configuration:
 *   D4  - L298N IN1 (Motor A direction)
 *   D5  - L298N IN2 (Motor A direction)
 *   D6  - L298N IN3 (Motor B direction)
 *   D7  - L298N IN4 (Motor B direction)
 *   D9  - L298N ENA (Motor A speed, PWM)
 *   D10 - L298N ENB (Motor B speed, PWM)
 *   D11 - HC-SR04 TRIG
 *   D12 - HC-SR04 ECHO
 * 
 * Motor Configuration:
 *   Motor A (ENA, IN1, IN2) = LEFT side (front + rear motors in parallel)
 *   Motor B (ENB, IN3, IN4) = RIGHT side (front + rear motors in parallel)
 * 
 * Serial Protocol (115200 baud):
 *   Commands FROM Raspberry Pi:
 *     F           - Forward
 *     B           - Backward
 *     L           - Turn left
 *     R           - Turn right
 *     S           - Stop
 *     SP<speed>   - Set speed (0-255, e.g., SP200)
 *     D           - Get distance reading
 *     ?           - Request status
 *     AUTO<0|1>   - Toggle autonomous mode
 * 
 *   Responses TO Raspberry Pi:
 *     OK                    - Command successful
 *     ERR:<message>         - Error occurred
 *     DIST:<cm>             - Distance in centimeters
 *     STATUS:<speed>,<dir>,<dist> - Current status
 *     OBSTACLE              - Obstacle detected (autonomous mode)
 * 
 * Author: Robot Control System
 * Version: 1.0
 * Date: 2025
 * ============================================================================
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

// L298N Motor Driver pins
const int MOTOR_A_IN1 = 4;    // Left motors direction
const int MOTOR_A_IN2 = 5;    // Left motors direction
const int MOTOR_B_IN3 = 6;    // Right motors direction
const int MOTOR_B_IN4 = 7;    // Right motors direction
const int MOTOR_A_ENA = 9;    // Left motors speed (PWM)
const int MOTOR_B_ENB = 10;   // Right motors speed (PWM)

// HC-SR04 Ultrasonic Sensor pins
const int TRIG_PIN = 11;
const int ECHO_PIN = 12;

// Motor parameters
const int DEFAULT_SPEED = 200;    // Default speed (0-255)
const int MIN_SPEED = 50;         // Minimum speed for movement
const int MAX_SPEED = 255;        // Maximum speed

// Autonomous mode parameters
const int OBSTACLE_DISTANCE = 20; // Stop distance in cm
const int SCAN_INTERVAL = 100;    // Distance check interval (ms)

// Serial communication
const long BAUD_RATE = 115200;
const int SERIAL_TIMEOUT = 50;

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

int currentSpeed = DEFAULT_SPEED;
String currentDirection = "STOP";
String inputBuffer = "";
bool autonomousMode = false;
unsigned long lastScanTime = 0;
int lastDistance = 0;

// ============================================================================
// MOVEMENT STATES
// ============================================================================

enum MotorState {
  STOP,
  FORWARD,
  BACKWARD,
  LEFT,
  RIGHT
};

MotorState currentState = STOP;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize motor control pins
  pinMode(MOTOR_A_IN1, OUTPUT);
  pinMode(MOTOR_A_IN2, OUTPUT);
  pinMode(MOTOR_B_IN3, OUTPUT);
  pinMode(MOTOR_B_IN4, OUTPUT);
  pinMode(MOTOR_A_ENA, OUTPUT);
  pinMode(MOTOR_B_ENB, OUTPUT);
  
  // Initialize ultrasonic sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  // Ensure motors are stopped
  stopMotors();
  
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);
  
  // Wait for serial to initialize
  delay(100);
  
  // Send ready message
  Serial.println("MOTOR_READY");
  Serial.flush();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Process serial commands
  processSerialInput();
  
  // Autonomous obstacle avoidance
  if (autonomousMode) {
    handleAutonomousMode();
  }
  
  // Small delay
  delay(10);
}

// ============================================================================
// SERIAL COMMUNICATION
// ============================================================================

/**
 * Process incoming serial commands
 */
void processSerialInput() {
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    // Command complete on newline
    if (inChar == '\n' || inChar == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += inChar;
    }
  }
}

/**
 * Parse and execute command
 */
void processCommand(String command) {
  command.trim();
  command.toUpperCase();
  
  if (command.length() == 0) {
    return;
  }
  
  // Movement commands
  if (command == "F") {
    moveForward();
    Serial.println("OK");
  }
  else if (command == "B") {
    moveBackward();
    Serial.println("OK");
  }
  else if (command == "L") {
    turnLeft();
    Serial.println("OK");
  }
  else if (command == "R") {
    turnRight();
    Serial.println("OK");
  }
  else if (command == "S") {
    stopMotors();
    Serial.println("OK");
  }
  
  // Speed control: SP<value>
  else if (command.startsWith("SP") && command.length() > 2) {
    int speed = command.substring(2).toInt();
    if (setSpeed(speed)) {
      Serial.println("OK");
    } else {
      Serial.println("ERR:Invalid speed");
    }
  }
  
  // Distance reading: D
  else if (command == "D") {
    int distance = getDistance();
    Serial.print("DIST:");
    Serial.println(distance);
  }
  
  // Status request: ?
  else if (command == "?") {
    sendStatus();
  }
  
  // Toggle autonomous mode: AUTO0 or AUTO1
  else if (command.startsWith("AUTO")) {
    if (command.length() >= 5) {
      autonomousMode = (command.substring(4, 5) == "1");
      Serial.print("OK:AUTO=");
      Serial.println(autonomousMode ? "ON" : "OFF");
      
      if (!autonomousMode) {
        stopMotors();
      }
    }
  }
  
  // Unknown command
  else {
    Serial.print("ERR:Unknown command: ");
    Serial.println(command);
  }
}

/**
 * Send current status
 */
void sendStatus() {
  Serial.print("STATUS:");
  Serial.print(currentSpeed);
  Serial.print(",");
  Serial.print(currentDirection);
  Serial.print(",");
  Serial.println(lastDistance);
}

// ============================================================================
// MOTOR CONTROL
// ============================================================================

/**
 * Move forward
 */
void moveForward() {
  currentState = FORWARD;
  currentDirection = "FORWARD";
  
  // Left motors forward
  digitalWrite(MOTOR_A_IN1, HIGH);
  digitalWrite(MOTOR_A_IN2, LOW);
  
  // Right motors forward
  digitalWrite(MOTOR_B_IN3, HIGH);
  digitalWrite(MOTOR_B_IN4, LOW);
  
  // Set speed
  analogWrite(MOTOR_A_ENA, currentSpeed);
  analogWrite(MOTOR_B_ENB, currentSpeed);
}

/**
 * Move backward
 */
void moveBackward() {
  currentState = BACKWARD;
  currentDirection = "BACKWARD";
  
  // Left motors backward
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, HIGH);
  
  // Right motors backward
  digitalWrite(MOTOR_B_IN3, LOW);
  digitalWrite(MOTOR_B_IN4, HIGH);
  
  // Set speed
  analogWrite(MOTOR_A_ENA, currentSpeed);
  analogWrite(MOTOR_B_ENB, currentSpeed);
}

/**
 * Turn left (left motors stop/reverse, right motors forward)
 */
void turnLeft() {
  currentState = LEFT;
  currentDirection = "LEFT";
  
  // Left motors backward (or stop)
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, HIGH);
  
  // Right motors forward
  digitalWrite(MOTOR_B_IN3, HIGH);
  digitalWrite(MOTOR_B_IN4, LOW);
  
  // Set speed (reduce left side for gentler turn)
  analogWrite(MOTOR_A_ENA, currentSpeed / 2);
  analogWrite(MOTOR_B_ENB, currentSpeed);
}

/**
 * Turn right (right motors stop/reverse, left motors forward)
 */
void turnRight() {
  currentState = RIGHT;
  currentDirection = "RIGHT";
  
  // Left motors forward
  digitalWrite(MOTOR_A_IN1, HIGH);
  digitalWrite(MOTOR_A_IN2, LOW);
  
  // Right motors backward (or stop)
  digitalWrite(MOTOR_B_IN3, LOW);
  digitalWrite(MOTOR_B_IN4, HIGH);
  
  // Set speed (reduce right side for gentler turn)
  analogWrite(MOTOR_A_ENA, currentSpeed);
  analogWrite(MOTOR_B_ENB, currentSpeed / 2);
}

/**
 * Stop all motors
 */
void stopMotors() {
  currentState = STOP;
  currentDirection = "STOP";
  
  // Stop both motors
  digitalWrite(MOTOR_A_IN1, LOW);
  digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN3, LOW);
  digitalWrite(MOTOR_B_IN4, LOW);
  
  // Set speed to 0
  analogWrite(MOTOR_A_ENA, 0);
  analogWrite(MOTOR_B_ENB, 0);
}

/**
 * Set motor speed
 * @param speed Speed value (0-255)
 * @return true if valid, false otherwise
 */
bool setSpeed(int speed) {
  if (speed < 0 || speed > MAX_SPEED) {
    return false;
  }
  
  currentSpeed = speed;
  
  // Update speed if motors are running
  if (currentState != STOP) {
    analogWrite(MOTOR_A_ENA, currentSpeed);
    analogWrite(MOTOR_B_ENB, currentSpeed);
  }
  
  return true;
}

// ============================================================================
// ULTRASONIC SENSOR
// ============================================================================

/**
 * Get distance reading from HC-SR04 sensor
 * @return Distance in centimeters (0-400)
 */
int getDistance() {
  // Clear trigger pin
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  
  // Send 10us pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pin (timeout after 30ms = ~5m)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  
  // Calculate distance (speed of sound = 343 m/s)
  // Distance = (duration / 2) / 29.1
  int distance = duration / 58;
  
  // Validate reading (HC-SR04 range: 2-400 cm)
  if (distance < 2 || distance > 400) {
    distance = 400; // Return max distance on error
  }
  
  lastDistance = distance;
  return distance;
}

// ============================================================================
// AUTONOMOUS MODE
// ============================================================================

/**
 * Handle autonomous obstacle avoidance
 */
void handleAutonomousMode() {
  unsigned long currentTime = millis();
  
  // Check distance at regular intervals
  if (currentTime - lastScanTime >= SCAN_INTERVAL) {
    lastScanTime = currentTime;
    
    int distance = getDistance();
    
    // Obstacle detected
    if (distance < OBSTACLE_DISTANCE && distance > 0) {
      if (currentState == FORWARD) {
        // Stop and notify
        stopMotors();
        Serial.println("OBSTACLE");
        
        // Back up slightly
        delay(100);
        moveBackward();
        delay(500);
        stopMotors();
        
        // Turn to avoid (random direction)
        if (random(0, 2) == 0) {
          turnLeft();
        } else {
          turnRight();
        }
        delay(700);
        stopMotors();
      }
    }
    // Path clear, continue forward
    else if (currentState == STOP && distance >= OBSTACLE_DISTANCE) {
      moveForward();
    }
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Emergency stop (can be called from anywhere)
 */
void emergencyStop() {
  stopMotors();
  autonomousMode = false;
  Serial.println("EMERGENCY_STOP");
}
