"""
============================================================================
AUTONOMOUS CONTROL MODULE
============================================================================

Handles autonomous robot behaviors including obstacle avoidance and patrol.

Features:
  - Obstacle avoidance
  - Patrol patterns
  - Emergency stop
  - State management

============================================================================
"""

import threading
import time
import random

class AutonomousController:
    """Autonomous robot behavior controller"""
    
    def __init__(self, arduino_controller, camera=None):
        """
        Initialize autonomous controller
        
        Args:
            arduino_controller: ArduinoController instance
            camera: CameraStream instance (optional, for future ML integration)
        """
        self.arduino = arduino_controller
        self.camera = camera
        self.running = False
        self.thread = None
        
        # Parameters
        self.obstacle_distance = 25  # cm - stop distance
        self.safe_distance = 40      # cm - comfortable distance
        self.scan_interval = 0.2     # seconds between distance checks
        self.patrol_mode = 'explore' # 'explore', 'patrol', 'follow_wall'
        
        print("[Autonomous] Initialized")
    
    def start(self, mode='explore'):
        """
        Start autonomous mode
        
        Args:
            mode: Autonomous mode ('explore', 'patrol', 'follow_wall')
        
        Returns:
            bool: True if started successfully
        """
        if self.running:
            print("[Autonomous] Already running")
            return False
        
        if not self.arduino.motor_connected:
            print("[Autonomous] Motor controller not connected")
            return False
        
        self.patrol_mode = mode
        self.running = True
        
        # Start autonomous thread
        self.thread = threading.Thread(target=self._autonomous_loop, daemon=True)
        self.thread.start()
        
        print(f"[Autonomous] Started in '{mode}' mode")
        return True
    
    def stop(self):
        """Stop autonomous mode"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=2.0)
        
        # Stop motors
        self.arduino.send_motor_command('S')
        
        print("[Autonomous] Stopped")
    
    def _autonomous_loop(self):
        """Main autonomous control loop"""
        try:
            if self.patrol_mode == 'explore':
                self._explore_mode()
            elif self.patrol_mode == 'patrol':
                self._patrol_mode()
            elif self.patrol_mode == 'follow_wall':
                self._follow_wall_mode()
            else:
                self._explore_mode()
        
        except Exception as e:
            print(f"[Autonomous] Error: {e}")
            self.running = False
    
    def _explore_mode(self):
        """
        Explore mode: Move forward, avoid obstacles, random turns
        """
        print("[Autonomous] Explore mode active")
        
        # Start moving forward
        self.arduino.send_motor_command('F')
        
        while self.running:
            # Check distance
            distance = self.arduino.get_distance()
            
            # Obstacle detected
            if distance < self.obstacle_distance and distance > 0:
                print(f"[Autonomous] Obstacle at {distance}cm - avoiding")
                
                # Stop
                self.arduino.send_motor_command('S')
                time.sleep(0.3)
                
                # Back up
                self.arduino.send_motor_command('B')
                time.sleep(0.5)
                
                # Stop
                self.arduino.send_motor_command('S')
                time.sleep(0.2)
                
                # Turn random direction
                turn_direction = random.choice(['L', 'R'])
                turn_time = random.uniform(0.5, 1.5)
                
                self.arduino.send_motor_command(turn_direction)
                time.sleep(turn_time)
                
                # Stop and check
                self.arduino.send_motor_command('S')
                time.sleep(0.2)
                
                # Resume forward
                self.arduino.send_motor_command('F')
            
            # Random course corrections
            elif random.random() < 0.02:  # 2% chance per iteration
                # Small random turn to explore
                turn_direction = random.choice(['L', 'R'])
                self.arduino.send_motor_command(turn_direction)
                time.sleep(0.3)
                self.arduino.send_motor_command('F')
            
            time.sleep(self.scan_interval)
        
        # Stop when exiting
        self.arduino.send_motor_command('S')
    
    def _patrol_mode(self):
        """
        Patrol mode: Follow a square pattern
        """
        print("[Autonomous] Patrol mode active")
        
        # Square patrol parameters
        forward_time = 3.0  # seconds per side
        turn_time = 0.7     # 90-degree turn time
        
        while self.running:
            # Move forward
            self.arduino.send_motor_command('F')
            
            # Check for obstacles while moving
            start_time = time.time()
            while time.time() - start_time < forward_time and self.running:
                distance = self.arduino.get_distance()
                
                if distance < self.obstacle_distance and distance > 0:
                    print(f"[Autonomous] Obstacle detected - adjusting patrol")
                    break
                
                time.sleep(self.scan_interval)
            
            if not self.running:
                break
            
            # Stop
            self.arduino.send_motor_command('S')
            time.sleep(0.3)
            
            # Turn right (90 degrees)
            self.arduino.send_motor_command('R')
            time.sleep(turn_time)
            
            # Stop
            self.arduino.send_motor_command('S')
            time.sleep(0.3)
        
        # Stop when exiting
        self.arduino.send_motor_command('S')
    
    def _follow_wall_mode(self):
        """
        Wall following mode: Keep a constant distance from wall on right side
        (Requires additional side-facing distance sensor - simplified version)
        """
        print("[Autonomous] Wall following mode active (simplified)")
        
        # This is a simplified version without side sensors
        # It alternates between forward and slight right turns
        
        while self.running:
            # Check front distance
            distance = self.arduino.get_distance()
            
            if distance < self.obstacle_distance and distance > 0:
                # Too close - turn left
                self.arduino.send_motor_command('L')
                time.sleep(0.5)
            
            elif distance > self.safe_distance or distance == 0:
                # Far from wall - turn right slightly
                self.arduino.send_motor_command('R')
                time.sleep(0.2)
                self.arduino.send_motor_command('F')
                time.sleep(0.5)
            
            else:
                # Good distance - move forward
                self.arduino.send_motor_command('F')
                time.sleep(0.5)
            
            time.sleep(self.scan_interval)
        
        # Stop when exiting
        self.arduino.send_motor_command('S')
    
    def set_obstacle_distance(self, distance):
        """
        Set obstacle detection distance
        
        Args:
            distance: Distance in centimeters
        """
        self.obstacle_distance = max(10, min(100, distance))
        print(f"[Autonomous] Obstacle distance set to {self.obstacle_distance}cm")
    
    def set_scan_interval(self, interval):
        """
        Set distance scanning interval
        
        Args:
            interval: Interval in seconds
        """
        self.scan_interval = max(0.1, min(1.0, interval))
        print(f"[Autonomous] Scan interval set to {self.scan_interval}s")
    
    def is_running(self):
        """Check if autonomous mode is active"""
        return self.running
    
    def get_status(self):
        """Get autonomous controller status"""
        return {
            'running': self.running,
            'mode': self.patrol_mode,
            'obstacle_distance': self.obstacle_distance,
            'scan_interval': self.scan_interval
        }
