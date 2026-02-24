# Tactical Robot v2.0 - Wiring Diagram

This document details the complete wiring for all components in the v2.0 system. It is crucial to follow these connections carefully to ensure correct and safe operation.

**Grounding:** All components MUST share a common ground (GND). Connect the GND pins of the Raspberry Pi, both Arduinos, the TB6612FNG, and the negative terminal of the battery pack together.

## 1. Power System

- **Batteries**: 2S2P 18650 Li-ion pack (7.4V nominal).
- **BMS**: A 2S Battery Management System is connected to the battery pack for protection.
- **Main Switch**: A high-current switch is placed between the BMS output and the rest of the system.
- **Buck Converter**: A buck converter steps down the 7.4V from the battery to a stable 5V to power the Raspberry Pi.

```
(7.4V BATT+) --- [BMS B+] --- [Main Switch] ---+--- (TB6612FNG VM)
                                              |
(GND) -------- [BMS B-] ----------------------+--- (TB6612FNG GND)
                                              |
                                              +--- (Buck Converter VIN+)
                                              |
                                              +--- (GND)

(Buck Converter VOUT+) ---------------------------> (Raspberry Pi 5V Pin)
(Buck Converter VOUT-) ---------------------------> (Raspberry Pi GND Pin)
```

## 2. Raspberry Pi 4 Connections

The Pi is the central controller.

| Pi Pin (BCM) | Pi Pin (Board) | Connection | Purpose |
|---|---|---|---|
| GPIO 2 (SDA) | Pin 3 | I2C Bus | INA219 & MPU-6050 Data |
| GPIO 3 (SCL) | Pin 5 | I2C Bus | INA219 & MPU-6050 Clock |
| GPIO 18 | Pin 12 | WS2812B LED Strip | LED Data Line |
| 5V | Pin 2/4 | 5V Power In | From Buck Converter |
| GND | Pin 6/9/etc. | Ground | Common Ground |
| USB 0 | - | Arduino Uno #1 | Motor Controller Serial |
| USB 1 | - | Arduino Uno #2 | Servo Controller Serial |

## 3. Arduino #1: Motor Controller

This Arduino handles all motor functions and proximity sensing.

**Power:**
- **VIN**: Connect to the 5V output of the TB6612FNG internal regulator.
- **GND**: Connect to common ground.

**TB6612FNG Motor Driver:**

```
      TB6612FNG
      +-------+
VM ---| VM    |
VIN --| VCC   |--- (Arduino #1 VIN)
GND --| GND   |
      |       |
AIN1 -| AIN1  |--- (Arduino #1 D8)
AIN2 -| AIN2  |--- (Arduino #1 D7)
PWMA -| PWMA  |--- (Arduino #1 D6, PWM)
      |       |
BIN1 -| BIN1  |--- (Arduino #1 D9)
BIN2 -| BIN2  |--- (Arduino #1 D10)
PWMB -| PWMB  |--- (Arduino #1 D11, PWM)
      |       |
STBY -| STBY  |--- (Arduino #1 D12)
      |       |
AO1 --| AO1   |--- (Left Motors +)
AO2 --| AO2   |--- (Left Motors -)
BO1 --| BO1   |--- (Right Motors +)
BO2 --| BO2   |--- (Right Motors -)
      +-------+
```

**Ultrasonic Sensors (HC-SR04):**

| Sensor | Arduino Pin (Trig) | Arduino Pin (Echo) |
|---|---|---|
| Front | D2 | D3 |
| Left | D4 | D5 |
| Right | A0 | A1 |

**INA219 Power Monitor (via I2C from Pi):**
- The INA219 is on the main I2C bus connected to the Raspberry Pi.
- It communicates its readings to the Motor Arduino via serial commands from the Pi.

## 4. Arduino #2: Servo & IMU Controller

This Arduino manages servos, orientation sensing, and audio alerts.

**Power:**
- **VIN**: Connect to a stable 5V source (e.g., from the Pi's 5V rail or another regulator).
- **GND**: Connect to common ground.

**Servos (x4):**
- **VCC**: Connect to a 5V source capable of handling the current (e.g., the TB6612FNG's 5V output or a separate BEC).
- **GND**: Connect to common ground.

| Servo | Arduino Pin (Signal) |
|---|---|
| 1 (Pan) | D3 (PWM) |
| 2 (Tilt) | D5 (PWM) |
| 3 (Cam) | D6 (PWM) |
| 4 (Aux) | D9 (PWM) |

**MPU-6050 IMU (I2C):**
- **VCC**: Connect to Pi 3.3V.
- **GND**: Connect to common ground.
- **SDA**: Connect to Pi GPIO 2 (SDA).
- **SCL**: Connect to Pi GPIO 3 (SCL).

**Passive Buzzer:**
- **(+)**: Connect to Arduino #2, Pin D11.
- **(-)**: Connect to common ground.

## ASCII Art Overview

```
+---------------------+      +-----------------------+      +----------------------+
|   Raspberry Pi 4    |      |     Arduino #1        |      |    Arduino #2        |
|                     |      |   (Motor Controller)  |      |  (Servo Controller)  |
|          [USB0] <-----------> [USB]                 |      |           [USB] <---->
|          [USB1] <-----------------------------------------> [USB]                 |
|                     |      |                       |      |                      |
| [GPIO 2/3] SDA/SCL <----------+--------------------------+ |                      |
|                     |      | [D2/D3] Front Sensor  |      | [D3] Servo 1         |
| [GPIO 18] LED Data --->    | [D4/D5] Left Sensor   |      | [D5] Servo 2         |
|                     |      | [A0/A1] Right Sensor  |      | [D6] Servo 3         |
| [5V/GND] Power In   |      |                       |      | [D9] Servo 4         |
+---------------------+      | [D6-D12] TB6612FNG    |      |                      |
      ^       ^              |                       |      | [D11] Buzzer         |
      |       |              +-----------------------+      +----------------------+
      |       |                    ^       ^
      |       |                    |       |
+-----+-------+-----+              |       +----------------+  +--------------------+
| Buck Converter 5V |              |                        |  |   4x Servo Motors  |
+-------------------+              +------------------+     |  +--------------------+
      ^                            |  TB6612FNG       |     |
      |                            |------------------|     |
+-----+----------------------------+ Motor Power (VM) |     +---> Servo Power (5V)
| 7.4V Battery Pack + BMS + Switch | Motor Control    |---------> 4x DC Motors
+----------------------------------+ 5V Regulator Out |-----> Arduino #1 Power (VIN)
                                   +------------------+

I2C Bus (SDA/SCL from Pi)
  |--> INA219 Power Monitor
  |--> MPU-6050 IMU
```
