"""
============================================================================
CAMERA STREAMING MODULE
============================================================================

Handles Pi Camera streaming with low latency MJPEG encoding.

Features:
  - Live camera feed
  - Frame capture for recording
  - Resolution and FPS control
  - Thread-safe frame access

============================================================================
"""

import cv2
import threading
import time
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import io

class CameraStream:
    """Pi Camera streaming handler"""
    
    def __init__(self, resolution=(640, 480), framerate=30):
        """
        Initialize camera stream
        
        Args:
            resolution: Tuple of (width, height)
            framerate: Frames per second
        """
        self.resolution = resolution
        self.framerate = framerate
        self.frame = None
        self.lock = threading.Lock()
        self.camera = None
        self.running = False
        
        # Try to initialize camera
        try:
            self.camera = Picamera2()
            config = self.camera.create_preview_configuration(
                main={"size": resolution, "format": "RGB888"}
            )
            self.camera.configure(config)
            self.camera.start()
            self.running = True
            
            # Start capture thread
            self.thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.thread.start()
            
            print(f"[Camera] Initialized: {resolution[0]}x{resolution[1]} @ {framerate}fps")
        
        except Exception as e:
            print(f"[Camera] Failed to initialize: {e}")
            print("[Camera] Using dummy frames (for testing without camera)")
            self.running = False
    
    def _capture_frames(self):
        """Continuously capture frames from camera"""
        while self.running:
            try:
                # Capture frame
                frame = self.camera.capture_array()
                
                # Convert RGB to BGR for OpenCV
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Store frame with lock
                with self.lock:
                    self.frame = frame.copy()
                
                # Control framerate
                time.sleep(1.0 / self.framerate)
            
            except Exception as e:
                print(f"[Camera] Frame capture error: {e}")
                time.sleep(0.1)
    
    def get_frame(self):
        """
        Get current frame
        
        Returns:
            numpy.ndarray: Current frame or None
        """
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def generate_frames(self):
        """
        Generator for MJPEG streaming
        
        Yields:
            bytes: JPEG-encoded frame with multipart headers
        """
        while True:
            frame = self.get_frame()
            
            if frame is None:
                # Generate dummy frame if camera not available
                frame = self._generate_dummy_frame()
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if not ret:
                continue
            
            # Convert to bytes
            frame_bytes = buffer.tobytes()
            
            # Yield with multipart headers
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control streaming rate
            time.sleep(1.0 / self.framerate)
    
    def _generate_dummy_frame(self):
        """Generate a dummy frame for testing"""
        import numpy as np
        
        # Create black frame with text
        frame = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        
        text = "Camera Not Available"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (self.resolution[0] - text_size[0]) // 2
        text_y = (self.resolution[1] + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, 1, (255, 255, 255), 2)
        
        return frame
    
    def is_available(self):
        """Check if camera is available"""
        return self.camera is not None and self.running
    
    def stop(self):
        """Stop camera streaming"""
        self.running = False
        if self.camera:
            try:
                self.camera.stop()
                self.camera.close()
            except:
                pass
        print("[Camera] Stopped")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()


class CameraStreamOpenCV:
    """
    Alternative camera implementation using OpenCV (for USB cameras)
    Use this if you have a USB camera instead of Pi Camera Module
    """
    
    def __init__(self, camera_index=0, resolution=(640, 480), framerate=30):
        """
        Initialize OpenCV camera stream
        
        Args:
            camera_index: Camera device index (usually 0)
            resolution: Tuple of (width, height)
            framerate: Frames per second
        """
        self.resolution = resolution
        self.framerate = framerate
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        
        # Try to open camera
        try:
            self.camera = cv2.VideoCapture(camera_index)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, framerate)
            
            if self.camera.isOpened():
                self.running = True
                
                # Start capture thread
                self.thread = threading.Thread(target=self._capture_frames, daemon=True)
                self.thread.start()
                
                print(f"[Camera] OpenCV initialized: {resolution[0]}x{resolution[1]} @ {framerate}fps")
            else:
                raise Exception("Failed to open camera")
        
        except Exception as e:
            print(f"[Camera] Failed to initialize: {e}")
            self.camera = None
            self.running = False
    
    def _capture_frames(self):
        """Continuously capture frames"""
        while self.running:
            try:
                ret, frame = self.camera.read()
                
                if ret:
                    with self.lock:
                        self.frame = frame.copy()
                
                time.sleep(1.0 / self.framerate)
            
            except Exception as e:
                print(f"[Camera] Frame capture error: {e}")
                time.sleep(0.1)
    
    def get_frame(self):
        """Get current frame"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def generate_frames(self):
        """Generator for MJPEG streaming"""
        while True:
            frame = self.get_frame()
            
            if frame is None:
                time.sleep(0.1)
                continue
            
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(1.0 / self.framerate)
    
    def is_available(self):
        """Check if camera is available"""
        return self.camera is not None and self.running
    
    def stop(self):
        """Stop camera"""
        self.running = False
        if self.camera:
            self.camera.release()
        print("[Camera] Stopped")
    
    def __del__(self):
        """Cleanup"""
        self.stop()
