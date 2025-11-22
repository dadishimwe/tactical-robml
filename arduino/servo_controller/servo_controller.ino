/*
 * ============================================================================
 * ARDUINO #1 - SERVO CONTROLLER
 * ============================================================================
 * 
 * Purpose: Controls 4 servo motors with smooth movement, presets, and status
 * 
 * Hardware:
 *   - Arduino Uno
 *   - 4× SG90 Servo Motors
 *   - Connected to Raspberry Pi via USB serial
 * 
 * Pin Configuration:
 *   D3  (PWM) - Servo 1 (Camera Pan / Primary)
 *   D5  (PWM) - Servo 2 (Camera Tilt / Secondary)
 *   D6  (PWM) - Servo 3 (Sensor Turret / Gripper)
 *   D9  (PWM) - Servo 4 (Auxiliary / Wrist)
 * 
 * Serial Protocol (115200 baud):
 *   Commands FROM Raspberry Pi:
 *     S<servo><angle>     - Set servo position (e.g., S1090 = Servo 1 to 90°)
 *     P<preset>           - Load preset (P0=home, P1=scan, P2=grip)
 *     C                   - Center all servos (90°)
 *     ?                   - Request status
 *     SMOOTH<0|1>         - Toggle smooth movement
 * 
 *   Responses TO Raspberry Pi:
 *     OK                  - Command successful
 *     ERR:<message>       - Error occurred
 *     STATUS:<s1>,<s2>,<s3>,<s4> - Current servo positions
 * 
 * Author: Robot Control System
 * Version: 1.0
 * Date: 2025
 * ============================================================================
 */

#include <Servo.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Servo pin definitions
const int SERVO_PINS[4] = {3, 5, 6, 9};  // PWM-capable pins

// Servo angle limits (adjust based on your servo specs)
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;
const int SERVO_CENTER = 90;

// Movement parameters
const int SMOOTH_DELAY = 15;      // Delay between steps (ms) for smooth movement
const int SMOOTH_STEP = 2;        // Degrees per step for smooth movement
bool smoothMovement = true;       // Enable/disable smooth movement

// Serial communication
const long BAUD_RATE = 115200;
const int SERIAL_TIMEOUT = 50;

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

Servo servos[4];                  // Servo objects
int currentPositions[4];          // Current servo positions (0-180)
int targetPositions[4];           // Target servo positions (0-180)
String inputBuffer = "";          // Serial input buffer
bool servoAttached[4] = {false};  // Track which servos are attached

// ============================================================================
// PRESET CONFIGURATIONS
// ============================================================================

// Preset 0: Home position (all centered)
const int PRESET_HOME[4] = {90, 90, 90, 90};

// Preset 1: Scan position (camera looking forward, sensor scanning)
const int PRESET_SCAN[4] = {90, 60, 45, 90};

// Preset 2: Grip position (gripper ready, camera angled down)
const int PRESET_GRIP[4] = {90, 120, 0, 45};

// Preset 3: Look left
const int PRESET_LEFT[4] = {0, 90, 90, 90};

// Preset 4: Look right
const int PRESET_RIGHT[4] = {180, 90, 90, 90};

// Preset 5: Look up
const int PRESET_UP[4] = {90, 0, 90, 90};

// Preset 6: Look down
const int PRESET_DOWN[4] = {90, 180, 90, 90};

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);
  
  // Wait for serial to initialize
  delay(100);
  
  // Attach servos and set to center position
  for (int i = 0; i < 4; i++) {
    servos[i].attach(SERVO_PINS[i]);
    currentPositions[i] = SERVO_CENTER;
    targetPositions[i] = SERVO_CENTER;
    servos[i].write(SERVO_CENTER);
    servoAttached[i] = true;
    delay(100);  // Allow servo to reach position
  }
  
  // Send ready message
  Serial.println("SERVO_READY");
  Serial.flush();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Process serial commands
  processSerialInput();
  
  // Update servo positions (smooth movement)
  updateServoPositions();
  
  // Small delay to prevent overwhelming the serial buffer
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
  
  // Single servo control: S<servo><angle>
  // Example: S1090 = Servo 1 to 90 degrees
  if (command.startsWith("S") && command.length() >= 4) {
    int servoNum = command.substring(1, 2).toInt();
    int angle = command.substring(2).toInt();
    
    if (setServoPosition(servoNum, angle)) {
      Serial.println("OK");
    } else {
      Serial.println("ERR:Invalid servo or angle");
    }
  }
  
  // Preset: P<number>
  else if (command.startsWith("P") && command.length() >= 2) {
    int presetNum = command.substring(1).toInt();
    
    if (loadPreset(presetNum)) {
      Serial.println("OK");
    } else {
      Serial.println("ERR:Invalid preset");
    }
  }
  
  // Center all servos: C
  else if (command == "C") {
    centerAllServos();
    Serial.println("OK");
  }
  
  // Status request: ?
  else if (command == "?") {
    sendStatus();
  }
  
  // Toggle smooth movement: SMOOTH0 or SMOOTH1
  else if (command.startsWith("SMOOTH")) {
    if (command.length() >= 7) {
      smoothMovement = (command.substring(6, 7) == "1");
      Serial.print("OK:SMOOTH=");
      Serial.println(smoothMovement ? "ON" : "OFF");
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
  for (int i = 0; i < 4; i++) {
    Serial.print(currentPositions[i]);
    if (i < 3) Serial.print(",");
  }
  Serial.println();
}

// ============================================================================
// SERVO CONTROL
// ============================================================================

/**
 * Set target position for a specific servo
 * @param servoNum Servo number (1-4)
 * @param angle Target angle (0-180)
 * @return true if valid, false otherwise
 */
bool setServoPosition(int servoNum, int angle) {
  // Validate servo number (1-indexed for user, 0-indexed internally)
  if (servoNum < 1 || servoNum > 4) {
    return false;
  }
  
  // Validate angle
  if (angle < SERVO_MIN || angle > SERVO_MAX) {
    return false;
  }
  
  // Set target position
  int index = servoNum - 1;
  targetPositions[index] = angle;
  
  return true;
}

/**
 * Update all servo positions (smooth movement)
 */
void updateServoPositions() {
  bool anyMoving = false;
  
  for (int i = 0; i < 4; i++) {
    if (currentPositions[i] != targetPositions[i]) {
      anyMoving = true;
      
      if (smoothMovement) {
        // Smooth movement: move in small steps
        int diff = targetPositions[i] - currentPositions[i];
        
        if (abs(diff) <= SMOOTH_STEP) {
          // Close enough, jump to target
          currentPositions[i] = targetPositions[i];
        } else {
          // Move one step toward target
          if (diff > 0) {
            currentPositions[i] += SMOOTH_STEP;
          } else {
            currentPositions[i] -= SMOOTH_STEP;
          }
        }
      } else {
        // Instant movement
        currentPositions[i] = targetPositions[i];
      }
      
      // Write to servo
      servos[i].write(currentPositions[i]);
    }
  }
  
  // Add delay only if servos are moving
  if (anyMoving && smoothMovement) {
    delay(SMOOTH_DELAY);
  }
}

/**
 * Center all servos to 90 degrees
 */
void centerAllServos() {
  for (int i = 0; i < 4; i++) {
    targetPositions[i] = SERVO_CENTER;
  }
}

/**
 * Load a preset configuration
 * @param presetNum Preset number (0-6)
 * @return true if valid preset, false otherwise
 */
bool loadPreset(int presetNum) {
  const int* preset = nullptr;
  
  switch (presetNum) {
    case 0: preset = PRESET_HOME; break;
    case 1: preset = PRESET_SCAN; break;
    case 2: preset = PRESET_GRIP; break;
    case 3: preset = PRESET_LEFT; break;
    case 4: preset = PRESET_RIGHT; break;
    case 5: preset = PRESET_UP; break;
    case 6: preset = PRESET_DOWN; break;
    default: return false;
  }
  
  // Load preset positions
  for (int i = 0; i < 4; i++) {
    targetPositions[i] = preset[i];
  }
  
  return true;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Constrain angle to valid range
 */
int constrainAngle(int angle) {
  return constrain(angle, SERVO_MIN, SERVO_MAX);
}
