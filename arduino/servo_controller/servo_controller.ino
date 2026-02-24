/*
============================================================================
  TACTICAL ROBOT — SERVO CONTROLLER FIRMWARE  v2.0
  Arduino Uno #2
============================================================================
  Responsibilities:
    • 4× servo motor control (pan/tilt camera, sensor sweep, aux)
    • MPU-6050 IMU — pitch/roll orientation + flip detection
    • Passive buzzer for audio alerts

  Pin Map:
    D3  — Servo 1 (sensor sweep / pan)
    D5  — Servo 2 (camera tilt)
    D6  — Servo 3 (camera pan)
    D9  — Servo 4 (auxiliary)
    D11 — Passive buzzer
    SDA/SCL — MPU-6050 (I2C)

  Serial Protocol (115200 baud):
    Commands (Raspberry Pi → Arduino):
      S<n>:<angle>      — set servo n (1-4) to angle (0-180)
      CENTER            — centre all servos to 90°
      PRESET:<1-4>      — load named preset
      SCAN              — 180° sweep on servo 1
      IMU               — request IMU reading
      BUZZ:<freq>,<ms>  — play tone at freq Hz for ms milliseconds
      ?                 — full status

    Responses (Arduino → Raspberry Pi):
      SERVO_READY
      OK
      IMU:<pitch>,<roll>,<ax>,<ay>,<az>
      FLIP:1            — flip detected
      SCAN_POS:<angle>  — current scan angle
      STATUS:<s1>,<s2>,<s3>,<s4>
============================================================================
*/

#include <Wire.h>
#include <Servo.h>
#include <MPU6050_light.h>

// ── Pin Definitions ──────────────────────────────────────────────────────────

#define SERVO1_PIN  3
#define SERVO2_PIN  5
#define SERVO3_PIN  6
#define SERVO4_PIN  9
#define BUZZER_PIN  11

// ── Constants ────────────────────────────────────────────────────────────────

#define BAUD_RATE       115200
#define SERVO_MIN       0
#define SERVO_MAX       180
#define SERVO_CENTER    90
#define FLIP_THRESHOLD  45.0
#define IMU_INTERVAL    200

// ── Globals ──────────────────────────────────────────────────────────────────

Servo servos[4];
int   angles[4]  = {SERVO_CENTER, SERVO_CENTER, SERVO_CENTER, SERVO_CENTER};
int   targets[4] = {SERVO_CENTER, SERVO_CENTER, SERVO_CENTER, SERVO_CENTER};

MPU6050      mpu(Wire);
bool         mpuAvailable = false;
float        pitch = 0.0, roll = 0.0;
bool         isFlipped = false;
unsigned long lastImuRead = 0;

String inputBuffer = "";

// ── Servo Helpers ─────────────────────────────────────────────────────────────

void setServo(int idx, int angle) {
  angle = constrain(angle, SERVO_MIN, SERVO_MAX);
  targets[idx] = angle;
}

void applyServo(int idx) {
  angles[idx] = targets[idx];
  servos[idx].write(angles[idx]);
}

void centerAll() {
  for (int i = 0; i < 4; i++) setServo(i, SERVO_CENTER);
  for (int i = 0; i < 4; i++) applyServo(i);
}

void loadPreset(int preset) {
  switch (preset) {
    case 1: setServo(0, 90);  setServo(1, 45);  setServo(2, 90);  setServo(3, 90);  break;
    case 2: setServo(0, 90);  setServo(1, 135); setServo(2, 90);  setServo(3, 90);  break;
    case 3: setServo(0, 0);   setServo(1, 90);  setServo(2, 45);  setServo(3, 90);  break;
    case 4: setServo(0, 180); setServo(1, 90);  setServo(2, 135); setServo(3, 90);  break;
    default: centerAll(); return;
  }
  for (int i = 0; i < 4; i++) applyServo(i);
}

void doScan() {
  for (int a = 0; a <= 180; a += 5) {
    setServo(0, a);
    applyServo(0);
    delay(30);
    Serial.print("SCAN_POS:"); Serial.println(a);
  }
  setServo(0, SERVO_CENTER);
  applyServo(0);
}

// ── Buzzer ────────────────────────────────────────────────────────────────────

void buzz(int freq, int durationMs) {
  if (freq <= 0) { noTone(BUZZER_PIN); return; }
  tone(BUZZER_PIN, freq, durationMs);
}

void buzzAlert(int level) {
  switch (level) {
    case 1: buzz(1000, 100); break;
    case 2: buzz(800, 300); delay(150); buzz(800, 300); break;
    case 3:
      for (int i = 0; i < 5; i++) { buzz(1200, 100); delay(100); }
      break;
  }
}

// ── IMU ───────────────────────────────────────────────────────────────────────

void updateIMU() {
  if (!mpuAvailable) return;
  unsigned long now = millis();
  if (now - lastImuRead < IMU_INTERVAL) return;
  lastImuRead = now;

  mpu.update();
  pitch = mpu.getAngleX();
  roll  = mpu.getAngleY();

  bool flippedNow = (abs(pitch) > FLIP_THRESHOLD || abs(roll) > FLIP_THRESHOLD);
  if (flippedNow && !isFlipped) {
    Serial.println("FLIP:1");
    buzzAlert(3);
  }
  isFlipped = flippedNow;
}

// ── Command Parser ────────────────────────────────────────────────────────────

void processCommand(const String& cmd) {
  // S<n>:<angle>
  if (cmd.length() >= 4 && cmd[0] == 'S' && isDigit(cmd[1]) && cmd[2] == ':') {
    int idx   = cmd[1] - '1';
    int angle = cmd.substring(3).toInt();
    if (idx >= 0 && idx < 4) {
      setServo(idx, angle);
      applyServo(idx);
      Serial.println("OK");
    }
  }
  else if (cmd == "CENTER") {
    centerAll();
    Serial.println("OK");
  }
  else if (cmd.startsWith("PRESET:")) {
    loadPreset(cmd.substring(7).toInt());
    Serial.println("OK");
  }
  else if (cmd == "SCAN") {
    doScan();
    Serial.println("OK");
  }
  else if (cmd == "IMU") {
    if (mpuAvailable) {
      mpu.update();
      Serial.print("IMU:");
      Serial.print(mpu.getAngleX(), 2); Serial.print(",");
      Serial.print(mpu.getAngleY(), 2); Serial.print(",");
      Serial.print(mpu.getAccX(),   3); Serial.print(",");
      Serial.print(mpu.getAccY(),   3); Serial.print(",");
      Serial.println(mpu.getAccZ(), 3);
    } else {
      Serial.println("IMU:0,0,0,0,0");
    }
  }
  else if (cmd.startsWith("BUZZ:")) {
    String v  = cmd.substring(5);
    int    ci = v.indexOf(',');
    int    freq = v.substring(0, ci).toInt();
    int    dur  = v.substring(ci + 1).toInt();
    buzz(freq, dur);
    Serial.println("OK");
  }
  else if (cmd == "?") {
    Serial.print("STATUS:");
    for (int i = 0; i < 4; i++) {
      Serial.print(angles[i]);
      if (i < 3) Serial.print(",");
    }
    Serial.println();
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(BAUD_RATE);

  int pins[] = {SERVO1_PIN, SERVO2_PIN, SERVO3_PIN, SERVO4_PIN};
  for (int i = 0; i < 4; i++) {
    servos[i].attach(pins[i]);
    servos[i].write(SERVO_CENTER);
  }

  pinMode(BUZZER_PIN, OUTPUT);

  Wire.begin();
  byte status = mpu.begin();
  if (status == 0) {
    mpuAvailable = true;
    mpu.calcOffsets(true, true);
  }

  buzz(880, 120); delay(150); buzz(1100, 120);
  Serial.println("SERVO_READY");
}

// ── Loop ──────────────────────────────────────────────────────────────────────

void loop() {
  updateIMU();

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) processCommand(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}
