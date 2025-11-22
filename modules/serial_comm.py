"""
============================================================================
SERIAL COMMUNICATION MODULE
============================================================================

Handles serial communication with both Arduino controllers.

Features:
  - Auto-detection of Arduino ports
  - Command queuing and response parsing
  - Connection monitoring
  - Thread-safe operations

============================================================================
"""

import serial
import serial.tools.list_ports
import threading
import time
import queue

class ArduinoController:
    """Manages communication with both Arduino controllers"""
    
    def __init__(self, motor_port=None, servo_port=None, baud_rate=115200):
        """
        Initialize Arduino controllers
        
        Args:
            motor_port: Serial port for motor controller (auto-detect if None)
            servo_port: Serial port for servo controller (auto-detect if None)
            baud_rate: Serial baud rate (must match Arduino code)
        """
        self.baud_rate = baud_rate
        self.motor_serial = None
        self.servo_serial = None
        self.motor_connected = False
        self.servo_connected = False
        
        self.motor_lock = threading.Lock()
        self.servo_lock = threading.Lock()
        
        # Response queues
        self.motor_responses = queue.Queue()
        self.servo_responses = queue.Queue()
        
        # Auto-detect and connect
        if motor_port is None or servo_port is None:
            motor_port, servo_port = self._auto_detect_ports()
        
        self._connect_motor(motor_port)
        self._connect_servo(servo_port)
        
        # Start response listener threads
        if self.motor_connected:
            threading.Thread(target=self._listen_motor, daemon=True).start()
        
        if self.servo_connected:
            threading.Thread(target=self._listen_servo, daemon=True).start()
    
    def _auto_detect_ports(self):
        """
        Auto-detect Arduino ports by looking for MOTOR_READY and SERVO_READY messages
        
        Returns:
            tuple: (motor_port, servo_port) or (None, None)
        """
        print("[Arduino] Auto-detecting ports...")
        
        ports = list(serial.tools.list_ports.comports())
        motor_port = None
        servo_port = None
        
        for port in ports:
            # Skip non-USB ports
            if 'USB' not in port.description and 'ACM' not in port.device:
                continue
            
            try:
                # Try to connect and read initial message
                ser = serial.Serial(port.device, self.baud_rate, timeout=2)
                time.sleep(2)  # Wait for Arduino to boot
                
                # Read any available data
                if ser.in_waiting > 0:
                    message = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if 'MOTOR_READY' in message:
                        motor_port = port.device
                        print(f"[Arduino] Motor controller found on {port.device}")
                    elif 'SERVO_READY' in message:
                        servo_port = port.device
                        print(f"[Arduino] Servo controller found on {port.device}")
                
                ser.close()
            
            except Exception as e:
                print(f"[Arduino] Error checking {port.device}: {e}")
        
        return motor_port, servo_port
    
    def _connect_motor(self, port):
        """Connect to motor controller"""
        if port is None:
            print("[Arduino] Motor controller port not specified")
            return
        
        try:
            self.motor_serial = serial.Serial(port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            self.motor_connected = True
            print(f"[Arduino] Motor controller connected on {port}")
        
        except Exception as e:
            print(f"[Arduino] Failed to connect motor controller: {e}")
            self.motor_connected = False
    
    def _connect_servo(self, port):
        """Connect to servo controller"""
        if port is None:
            print("[Arduino] Servo controller port not specified")
            return
        
        try:
            self.servo_serial = serial.Serial(port, self.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            self.servo_connected = True
            print(f"[Arduino] Servo controller connected on {port}")
        
        except Exception as e:
            print(f"[Arduino] Failed to connect servo controller: {e}")
            self.servo_connected = False
    
    def _listen_motor(self):
        """Listen for motor controller responses"""
        while self.motor_connected:
            try:
                if self.motor_serial and self.motor_serial.in_waiting > 0:
                    response = self.motor_serial.readline().decode('utf-8', errors='ignore').strip()
                    if response:
                        self.motor_responses.put(response)
                        print(f"[Motor] {response}")
                
                time.sleep(0.01)
            
            except Exception as e:
                print(f"[Motor] Listen error: {e}")
                self.motor_connected = False
                break
    
    def _listen_servo(self):
        """Listen for servo controller responses"""
        while self.servo_connected:
            try:
                if self.servo_serial and self.servo_serial.in_waiting > 0:
                    response = self.servo_serial.readline().decode('utf-8', errors='ignore').strip()
                    if response:
                        self.servo_responses.put(response)
                        print(f"[Servo] {response}")
                
                time.sleep(0.01)
            
            except Exception as e:
                print(f"[Servo] Listen error: {e}")
                self.servo_connected = False
                break
    
    def send_motor_command(self, command):
        """
        Send command to motor controller
        
        Args:
            command: Command string (e.g., 'F', 'B', 'L', 'R', 'S', 'SP200')
        
        Returns:
            bool: True if command sent successfully
        """
        if not self.motor_connected:
            print("[Motor] Not connected")
            return False
        
        try:
            with self.motor_lock:
                self.motor_serial.write(f"{command}\n".encode('utf-8'))
                self.motor_serial.flush()
            
            return True
        
        except Exception as e:
            print(f"[Motor] Send error: {e}")
            return False
    
    def send_servo_command(self, command):
        """
        Send command to servo controller
        
        Args:
            command: Command string (e.g., 'S1090', 'P0', 'C')
        
        Returns:
            bool: True if command sent successfully
        """
        if not self.servo_connected:
            print("[Servo] Not connected")
            return False
        
        try:
            with self.servo_lock:
                self.servo_serial.write(f"{command}\n".encode('utf-8'))
                self.servo_serial.flush()
            
            return True
        
        except Exception as e:
            print(f"[Servo] Send error: {e}")
            return False
    
    def get_distance(self):
        """
        Get distance reading from ultrasonic sensor
        
        Returns:
            int: Distance in centimeters (0-400)
        """
        if not self.motor_connected:
            return 0
        
        try:
            # Clear response queue
            while not self.motor_responses.empty():
                self.motor_responses.get()
            
            # Send distance request
            self.send_motor_command('D')
            
            # Wait for response (timeout 1 second)
            timeout = time.time() + 1.0
            while time.time() < timeout:
                if not self.motor_responses.empty():
                    response = self.motor_responses.get()
                    
                    # Parse DIST:123 format
                    if response.startswith('DIST:'):
                        distance = int(response.split(':')[1])
                        return distance
                
                time.sleep(0.01)
            
            return 0
        
        except Exception as e:
            print(f"[Motor] Distance error: {e}")
            return 0
    
    def get_motor_status(self):
        """
        Get motor controller status
        
        Returns:
            dict: Status information
        """
        if not self.motor_connected:
            return {'connected': False}
        
        try:
            # Clear response queue
            while not self.motor_responses.empty():
                self.motor_responses.get()
            
            # Send status request
            self.send_motor_command('?')
            
            # Wait for response
            timeout = time.time() + 1.0
            while time.time() < timeout:
                if not self.motor_responses.empty():
                    response = self.motor_responses.get()
                    
                    # Parse STATUS:200,FORWARD,47 format
                    if response.startswith('STATUS:'):
                        parts = response.split(':')[1].split(',')
                        return {
                            'connected': True,
                            'speed': int(parts[0]),
                            'direction': parts[1],
                            'distance': int(parts[2])
                        }
                
                time.sleep(0.01)
            
            return {'connected': True, 'speed': 0, 'direction': 'UNKNOWN', 'distance': 0}
        
        except Exception as e:
            print(f"[Motor] Status error: {e}")
            return {'connected': False}
    
    def get_servo_status(self):
        """
        Get servo controller status
        
        Returns:
            dict: Status information
        """
        if not self.servo_connected:
            return {'connected': False}
        
        try:
            # Clear response queue
            while not self.servo_responses.empty():
                self.servo_responses.get()
            
            # Send status request
            self.send_servo_command('?')
            
            # Wait for response
            timeout = time.time() + 1.0
            while time.time() < timeout:
                if not self.servo_responses.empty():
                    response = self.servo_responses.get()
                    
                    # Parse STATUS:90,90,90,90 format
                    if response.startswith('STATUS:'):
                        positions = [int(x) for x in response.split(':')[1].split(',')]
                        return {
                            'connected': True,
                            'positions': positions
                        }
                
                time.sleep(0.01)
            
            return {'connected': True, 'positions': [0, 0, 0, 0]}
        
        except Exception as e:
            print(f"[Servo] Status error: {e}")
            return {'connected': False}
    
    def close(self):
        """Close all serial connections"""
        self.motor_connected = False
        self.servo_connected = False
        
        if self.motor_serial:
            try:
                self.motor_serial.close()
            except:
                pass
        
        if self.servo_serial:
            try:
                self.servo_serial.close()
            except:
                pass
        
        print("[Arduino] Connections closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
