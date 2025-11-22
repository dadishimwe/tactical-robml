# Robot Control System - Complete Wiring Diagram

## Power Distribution System

### Battery Configuration
```
4× 18650 Li-ion Batteries (3.7V each)

Configuration: 2S2P (Series-Parallel)
- 2 batteries in series = 7.4V
- 2 sets in parallel = doubled capacity

[Battery 1] ──┬── (+) 7.4V
[Battery 2] ──┘

[Battery 3] ──┬── (+) 7.4V  ──→ Combined to L298N (7.4V, ~4000-6000mAh)
[Battery 4] ──┘

Note: Use a 2S BMS (Battery Management System) for safe charging/discharging
```

### Power Distribution
```
USB Power Bank (5V)
    │
    ├──→ Raspberry Pi 4 (USB-C, 5V 3A)
    │       │
    │       ├──→ Arduino Uno #1 (USB, 5V)
    │       └──→ Arduino Uno #2 (USB, 5V)
    │
    └──→ Pi Camera Module (via CSI connector on Pi)

Battery Pack (7.4V, 2S2P)
    │
    └──→ L298N Motor Driver
            ├──→ 4× DC Motors (7.4V)
            └──→ 4× Servo Motors (via 5V regulator on L298N)
```

## Arduino #1 - Servo Controller

### Pin Assignments
```
Arduino Uno #1 (Servo Control)
================================

Digital Pins:
  D3  (PWM) → Servo 1 (Camera Pan)
  D5  (PWM) → Servo 2 (Camera Tilt)
  D6  (PWM) → Servo 3 (Sensor Turret)
  D9  (PWM) → Servo 4 (Gripper/Auxiliary)

Power:
  5V  → Servo Power Rail (from L298N 5V output)
  GND → Common Ground

USB:
  Connected to Raspberry Pi for serial communication
```

### Servo Wiring Detail
```
Each Servo (SG90):
  Brown/Black Wire  → GND (common ground rail)
  Red Wire          → 5V (from L298N 5V regulator)
  Orange/Yellow     → Signal (to Arduino PWM pin)

Servo Power Rail:
  L298N 5V Output → Power Strip → All Servo Red Wires
  Arduino GND     → Ground Strip → All Servo Brown Wires
```

## Arduino #2 - Motor & Sensor Controller

### Pin Assignments
```
Arduino Uno #2 (Motor & Sensor Control)
========================================

L298N Motor Driver Connections:
  D4  → IN1 (Motor A direction)
  D5  → IN2 (Motor A direction)
  D6  → IN3 (Motor B direction)
  D7  → IN4 (Motor B direction)
  D9  (PWM) → ENA (Motor A speed)
  D10 (PWM) → ENB (Motor B speed)

HC-SR04 Ultrasonic Sensor:
  D11 → TRIG (trigger pin)
  D12 → ECHO (echo pin)

Power:
  5V  → HC-SR04 VCC
  GND → HC-SR04 GND, L298N GND

USB:
  Connected to Raspberry Pi for serial communication
```

### L298N Motor Driver Wiring
```
L298N Motor Driver
==================

Power Input:
  12V Terminal → Battery Pack (+) 7.4V
  GND Terminal → Battery Pack (-) and Arduino GND

Motor Outputs:
  OUT1, OUT2 → Left Side Motors (parallel)
  OUT3, OUT4 → Right Side Motors (parallel)

Control Inputs:
  IN1, IN2 → From Arduino D4, D5
  IN3, IN4 → From Arduino D6, D7
  ENA, ENB → From Arduino D9, D10 (PWM)

5V Regulator:
  5V Output → Servo Power Rail
  (Ensure jumper is ON for 5V regulator)
```

### Motor Wiring Configuration
```
4-Wheel Drive Configuration:
============================

Left Side:
  Front Left Motor  ──┬─→ L298N OUT1
  Rear Left Motor   ──┘   L298N OUT2

Right Side:
  Front Right Motor ──┬─→ L298N OUT3
  Rear Right Motor  ──┘   L298N OUT4

Note: Motors on same side wired in parallel
Ensure all motors spin in correct direction
(swap wires if needed)
```

## Complete System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USB POWER BANK                           │
│                         (5V, 10000mAh)                          │
└────┬──────────────────────┬─────────────────────┬──────────────┘
     │                      │                     │
     │ USB-C                │ USB                 │ USB
     ▼                      ▼                     ▼
┌─────────────┐    ┌──────────────┐      ┌──────────────┐
│ RASPBERRY   │    │  ARDUINO #1  │      │  ARDUINO #2  │
│   PI 4      │    │   (Servos)   │      │(Motors/Sens) │
│             │    │              │      │              │
│ [Camera]────┤    │ D3─┐         │      │ D4───┐       │
│  Module     │    │ D5─┤         │      │ D5───┤       │
│             │    │ D6─┤         │      │ D6───┼──┐    │
│             │    │ D9─┤         │      │ D7───┼──┼──┐ │
└─────────────┘    │    │         │      │ D9───┼──┼──┼─┤
                   │ 5V─┼─────┐   │      │ D10──┼──┼──┼─┤
                   │ GND┼───┐ │   │      │ D11──┤  │  │ │
                   └────┼───┼─┼───┘      │ D12──┤  │  │ │
                        │   │ │          └──────┼──┼──┼─┘
                        │   │ │                 │  │  │
                   ┌────▼───▼─▼────┐           │  │  │
                   │ SERVO POWER   │           │  │  │
                   │     RAIL      │           │  │  │
                   │  5V     GND   │           │  │  │
                   └─┬──┬──┬──┬───┘           │  │  │
                     │  │  │  │               │  │  │
                    S1 S2 S3 S4              │  │  │
                     │  │  │  │               │  │  │
                   ┌─▼──▼──▼──▼───────────────▼──▼──▼─┐
                   │      L298N MOTOR DRIVER          │
                   │                                   │
                   │  IN1 IN2 IN3 IN4  ENA ENB        │
                   │                                   │
                   │  OUT1 OUT2 OUT3 OUT4             │
                   │   │    │    │    │               │
                   │  12V  GND   5V                   │
                   └───┼────┼────┼────────────────────┘
                       │    │    │
                       │    │    └─→ To Servo Rail
                       │    │
        ┌──────────────┴────┴──────────────┐
        │    BATTERY PACK (7.4V 2S2P)      │
        │  [Batt1+Batt2]  [Batt3+Batt4]   │
        └──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
    ┌───▼───┐  ┌───▼───┐  ┌───▼───┐  ┌───▼───┐
    │ Motor │  │ Motor │  │ Motor │  │ Motor │
    │  FL   │  │  RL   │  │  FR   │  │  RR   │
    └───────┘  └───────┘  └───────┘  └───────┘
```

## Servo Application Recommendations

### Configuration 1: Camera Gimbal + Gripper (Recommended)
```
Servo 1 (D3): Camera Pan (0-180°, horizontal rotation)
Servo 2 (D5): Camera Tilt (0-180°, vertical tilt)
Servo 3 (D6): Gripper Open/Close (0° = open, 90° = closed)
Servo 4 (D9): Gripper Wrist Rotate (0-180°, rotation)
```

### Configuration 2: Sensor Turret + Utility
```
Servo 1 (D3): Ultrasonic Sensor Pan (scan environment)
Servo 2 (D5): Ultrasonic Sensor Tilt (vertical scan)
Servo 3 (D6): Camera Pan (independent camera control)
Servo 4 (D9): LED Spotlight Direction
```

### Configuration 3: Full Camera Gimbal
```
Servo 1 (D3): Camera Pan (primary horizontal)
Servo 2 (D5): Camera Tilt (primary vertical)
Servo 3 (D6): Camera Roll (stabilization)
Servo 4 (D9): Sensor/Light Pan (auxiliary)
```

## Safety Considerations

### Fuses and Protection
```
Battery Pack → 5A Fuse → L298N Motor Driver
(Protects against short circuits and overcurrent)
```

### Voltage Regulation
- L298N has built-in 5V regulator for servos (max 500mA)
- If servos draw more current, use external 5V BEC (Battery Eliminator Circuit)
- Never connect motor battery directly to Arduino or servos

### Grounding
- **Critical**: All grounds must be connected together
- USB Power Bank GND ← → Arduino GND ← → L298N GND ← → Battery GND
- Poor grounding causes erratic servo behavior and communication issues

### Heat Management
- L298N can get hot during extended use
- Add heatsinks to L298N if available
- Ensure good ventilation around motor driver

## Connection Checklist

- [ ] Battery pack properly configured (2S2P with BMS)
- [ ] USB power bank charged and connected to Pi
- [ ] Both Arduinos connected to Pi via USB
- [ ] L298N powered from battery pack (7.4V)
- [ ] All 4 motors connected to L298N outputs
- [ ] Motor control pins (IN1-IN4, ENA, ENB) connected to Arduino #2
- [ ] All 4 servos connected to Arduino #1 PWM pins
- [ ] Servo power rail connected to L298N 5V output
- [ ] HC-SR04 sensor connected to Arduino #2 (D11, D12)
- [ ] Pi Camera Module connected to CSI port
- [ ] All grounds connected together (common ground)
- [ ] Fuse installed in battery circuit
- [ ] Double-check polarity on all connections

## Troubleshooting

### Motors not running
- Check battery voltage (should be 7.4V)
- Verify L298N power LED is on
- Test motor outputs with multimeter
- Check ENA/ENB jumpers are removed (for PWM control)

### Servos jittering
- Insufficient power (use external BEC if needed)
- Poor ground connection
- Electrical noise from motors (add capacitors to motor terminals)

### Sensor giving wrong readings
- Check 5V power supply
- Verify TRIG/ECHO connections
- Ensure sensor is not obstructed
- Check for loose wires

### Arduino not communicating
- Verify USB connections to Pi
- Check serial port permissions on Pi
- Test with Arduino IDE Serial Monitor
- Ensure correct baud rate (115200)
