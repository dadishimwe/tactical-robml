/*
============================================================================
  TACTICAL ROBOT — MOTOR CONTROLLER FIRMWARE  v2.0
  Arduino Uno #1
============================================================================
  Responsibilities:
    • 4-wheel DC motor drive via L298N
    • Front, Left, Right HC-SR04 ultrasonic distance sensors
    • INA219 battery voltage / current monitor (I2C)
    • WS2812B LED strip (status and night-mode lighting)

  Pin Map:
    D3  — WS2812B LED data
    D5  — Motor A ENA (PWM)
    D6  — Motor A IN1
    D7  — Motor A IN2
    D8  — Motor B IN3
    D9  — Motor B IN4
    D10 — Motor B ENB (PWM)
    D11 — Right HC-SR04 TRIG
    D12 — Right HC-SR04 ECHO
    A0  — Front HC-SR04 TRIG
    A1  — Front HC-SR04 ECHO
    A2  — Left  HC-SR04 TRIG
    A3  — Left  HC-SR04 ECHO
    SDA/SCL — INA219 (I2C)

  Serial Protocol (115200 baud):
    Commands (Raspberry Pi → Arduino):
      FORWARD | BACKWARD | LEFT | RIGHT | STOP | SLOW
      SPEED:<0-255>
      DF | DL | DR | DA          — query distances
      LED:<MODE>                 — IDLE|MOVING|AUTO|RECORD|WARN|CRITICAL|NIGHT|ML|OFF
      LEDC:<R>,<G>,<B>           — custom LED colour
      ?                          — full status query

    Responses (Arduino → Raspberry Pi):
      MOTOR_READY
      DIST_F:<cm>
      DIST_L:<cm>
      DIST_R:<cm>
      DIST_ALL:<front>,<left>,<right>
      STATUS:<speed>,<dir>,<front_dist>
============================================================================
*/

#include <Wire.h>
#include <INA219_WE.h>
#include <Adafruit_NeoPixel.h>

// ── Pin Definitions ──────────────────────────────────────────────────────────

#define MOTOR_A_EN   5
#define MOTOR_A_IN1  6
#define MOTOR_A_IN2  7
#define MOTOR_B_IN3  8
#define MOTOR_B_IN4  9
#define MOTOR_B_EN   10

#define TRIG_FRONT   A0
#define ECHO_FRONT   A1
#define TRIG_LEFT    A2
#define ECHO_LEFT    A3
#define TRIG_RIGHT   11
#define ECHO_RIGHT   12

#define LED_PIN      3
#define LED_COUNT    16

// ── Constants ────────────────────────────────────────────────────────────────

#define BAUD_RATE        115200
#define MAX_DISTANCE_CM  300
#define SOUND_SPEED_DIV  58

// ── Globals ──────────────────────────────────────────────────────────────────

int    motorSpeed    = 200;
String direction     = "STOP";
String inputBuffer   = "";

INA219_WE        ina219;
bool             inaAvailable = false;
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// ── LED Helpers ───────────────────────────────────────────────────────────────

void ledSetAll(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < LED_COUNT; i++)
    strip.setPixelColor(i, strip.Color(r, g, b));
  strip.show();
}

void ledNightMode() {
  int half = LED_COUNT / 2;
  for (int i = 0;    i < half;      i++) strip.setPixelColor(i, strip.Color(255, 255, 255));
  for (int i = half; i < LED_COUNT; i++) strip.setPixelColor(i, strip.Color(80, 0, 0));
  strip.show();
}

void ledApplyMode(const String& mode) {
  if      (mode == "IDLE")     ledSetAll(0,   80,  0);
  else if (mode == "MOVING")   ledSetAll(0,   200, 0);
  else if (mode == "AUTO")     ledSetAll(0,   0,   200);
  else if (mode == "RECORD")   ledSetAll(200, 0,   0);
  else if (mode == "WARN")     ledSetAll(200, 150, 0);
  else if (mode == "CRITICAL") ledSetAll(255, 0,   0);
  else if (mode == "NIGHT")    ledNightMode();
  else if (mode == "ML")       ledSetAll(150, 0,   200);
  else                         ledSetAll(0,   0,   0);
}

// ── Distance Measurement ─────────────────────────────────────────────────────

long measureDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long dur = pulseIn(echoPin, HIGH, 30000UL);
  if (dur == 0) return 0;
  long cm = dur / SOUND_SPEED_DIV;
  return (cm > MAX_DISTANCE_CM) ? 0 : cm;
}

// ── Motor Control ─────────────────────────────────────────────────────────────

void motorStop() {
  analogWrite(MOTOR_A_EN, 0);
  analogWrite(MOTOR_B_EN, 0);
  direction = "STOP";
}

void motorForward() {
  digitalWrite(MOTOR_A_IN1, HIGH); digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN3, HIGH); digitalWrite(MOTOR_B_IN4, LOW);
  analogWrite(MOTOR_A_EN, motorSpeed);
  analogWrite(MOTOR_B_EN, motorSpeed);
  direction = "FORWARD";
}

void motorBackward() {
  digitalWrite(MOTOR_A_IN1, LOW); digitalWrite(MOTOR_A_IN2, HIGH);
  digitalWrite(MOTOR_B_IN3, LOW); digitalWrite(MOTOR_B_IN4, HIGH);
  analogWrite(MOTOR_A_EN, motorSpeed);
  analogWrite(MOTOR_B_EN, motorSpeed);
  direction = "BACKWARD";
}

void motorLeft() {
  digitalWrite(MOTOR_A_IN1, LOW);  digitalWrite(MOTOR_A_IN2, HIGH);
  digitalWrite(MOTOR_B_IN3, HIGH); digitalWrite(MOTOR_B_IN4, LOW);
  analogWrite(MOTOR_A_EN, motorSpeed);
  analogWrite(MOTOR_B_EN, motorSpeed);
  direction = "LEFT";
}

void motorRight() {
  digitalWrite(MOTOR_A_IN1, HIGH); digitalWrite(MOTOR_A_IN2, LOW);
  digitalWrite(MOTOR_B_IN3, LOW);  digitalWrite(MOTOR_B_IN4, HIGH);
  analogWrite(MOTOR_A_EN, motorSpeed);
  analogWrite(MOTOR_B_EN, motorSpeed);
  direction = "RIGHT";
}

void motorSlow() {
  int s = max(50, motorSpeed / 2);
  analogWrite(MOTOR_A_EN, s);
  analogWrite(MOTOR_B_EN, s);
  direction = "SLOW";
}

// ── Command Parser ────────────────────────────────────────────────────────────

void processCommand(const String& cmd) {
  if      (cmd == "FORWARD")  motorForward();
  else if (cmd == "BACKWARD") motorBackward();
  else if (cmd == "LEFT")     motorLeft();
  else if (cmd == "RIGHT")    motorRight();
  else if (cmd == "STOP")     motorStop();
  else if (cmd == "SLOW")     motorSlow();

  else if (cmd.startsWith("SPEED:")) {
    motorSpeed = constrain(cmd.substring(6).toInt(), 0, 255);
  }

  else if (cmd == "DF") {
    Serial.print("DIST_F:"); Serial.println(measureDistance(TRIG_FRONT, ECHO_FRONT));
  }
  else if (cmd == "DL") {
    Serial.print("DIST_L:"); Serial.println(measureDistance(TRIG_LEFT, ECHO_LEFT));
  }
  else if (cmd == "DR") {
    Serial.print("DIST_R:"); Serial.println(measureDistance(TRIG_RIGHT, ECHO_RIGHT));
  }
  else if (cmd == "DA") {
    long f = measureDistance(TRIG_FRONT, ECHO_FRONT);
    long l = measureDistance(TRIG_LEFT,  ECHO_LEFT);
    long r = measureDistance(TRIG_RIGHT, ECHO_RIGHT);
    Serial.print("DIST_ALL:");
    Serial.print(f); Serial.print(",");
    Serial.print(l); Serial.print(",");
    Serial.println(r);
  }

  else if (cmd.startsWith("LED:")) {
    ledApplyMode(cmd.substring(4));
  }
  else if (cmd.startsWith("LEDC:")) {
    String v = cmd.substring(5);
    int c1 = v.indexOf(','), c2 = v.lastIndexOf(',');
    ledSetAll(v.substring(0, c1).toInt(),
              v.substring(c1 + 1, c2).toInt(),
              v.substring(c2 + 1).toInt());
  }

  else if (cmd == "?") {
    long f = measureDistance(TRIG_FRONT, ECHO_FRONT);
    Serial.print("STATUS:");
    Serial.print(motorSpeed); Serial.print(",");
    Serial.print(direction);  Serial.print(",");
    Serial.println(f);
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(BAUD_RATE);

  // Motor
  int motorPins[] = {MOTOR_A_EN, MOTOR_A_IN1, MOTOR_A_IN2,
                     MOTOR_B_EN, MOTOR_B_IN3, MOTOR_B_IN4};
  for (int p : motorPins) pinMode(p, OUTPUT);
  motorStop();

  // Ultrasonic
  int trigPins[] = {TRIG_FRONT, TRIG_LEFT, TRIG_RIGHT};
  int echoPins[] = {ECHO_FRONT, ECHO_LEFT, ECHO_RIGHT};
  for (int p : trigPins) pinMode(p, OUTPUT);
  for (int p : echoPins) pinMode(p, INPUT);

  // INA219
  Wire.begin();
  if (ina219.init()) {
    inaAvailable = true;
    ina219.setBusRange(INA219_BUS_RANGE_16V);
    ina219.setShuntSizeInOhms(0.1);
  }

  // LED strip
  strip.begin();
  strip.setBrightness(128);
  ledApplyMode("IDLE");

  Serial.println("MOTOR_READY");
}

// ── Loop ──────────────────────────────────────────────────────────────────────

void loop() {
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
