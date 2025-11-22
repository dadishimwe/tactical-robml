"""
============================================================================
ML OBJECT DETECTION MODULE
============================================================================

Optional module for object detection using YOLOv5 or MobileNet-SSD.

Features:
  - Real-time object detection
  - Bounding box overlay
  - Object tracking
  - Person/face detection

Installation:
  pip install torch torchvision
  pip install opencv-python
  pip install ultralytics  # For YOLOv5/YOLOv8

============================================================================
"""

import cv2
import threading
import time
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[ML] Ultralytics YOLO not available. Install with: pip install ultralytics")

class MLDetector:
    """Machine Learning object detector"""
    
    def __init__(self, camera, model_name='yolov8n.pt'):
        """
        Initialize ML detector
        
        Args:
            camera: CameraStream instance
            model_name: Model to use ('yolov8n.pt', 'yolov8s.pt', etc.)
        """
        self.camera = camera
        self.model_name = model_name
        self.model = None
        self.running = False
        self.thread = None
        
        self.detections = []
        self.detection_lock = threading.Lock()
        
        # Detection parameters
        self.confidence_threshold = 0.5
        self.target_classes = None  # None = all classes, or list of class IDs
        
        # Initialize model
        if YOLO_AVAILABLE:
            try:
                print(f"[ML] Loading model: {model_name}")
                self.model = YOLO(model_name)
                print("[ML] Model loaded successfully")
            except Exception as e:
                print(f"[ML] Failed to load model: {e}")
                self.model = None
        else:
            print("[ML] YOLO not available")
    
    def start(self):
        """Start object detection"""
        if not self.model:
            print("[ML] Model not loaded")
            return False
        
        if self.running:
            print("[ML] Already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        
        print("[ML] Detection started")
        return True
    
    def stop(self):
        """Stop object detection"""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        print("[ML] Detection stopped")
    
    def _detection_loop(self):
        """Main detection loop"""
        while self.running:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Run detection
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)
                
                # Parse results
                detections = []
                
                for result in results:
                    boxes = result.boxes
                    
                    for box in boxes:
                        # Get box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        
                        # Get class and confidence
                        cls = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())
                        
                        # Filter by target classes if specified
                        if self.target_classes and cls not in self.target_classes:
                            continue
                        
                        # Get class name
                        class_name = self.model.names[cls]
                        
                        detections.append({
                            'class': class_name,
                            'class_id': cls,
                            'confidence': conf,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)]
                        })
                
                # Update detections
                with self.detection_lock:
                    self.detections = detections
                
                # Control detection rate (5 FPS)
                time.sleep(0.2)
            
            except Exception as e:
                print(f"[ML] Detection error: {e}")
                time.sleep(0.5)
    
    def get_detections(self):
        """
        Get current detections
        
        Returns:
            list: List of detection dicts
        """
        with self.detection_lock:
            return self.detections.copy()
    
    def set_confidence_threshold(self, threshold):
        """Set confidence threshold (0.0 - 1.0)"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        print(f"[ML] Confidence threshold set to {self.confidence_threshold}")
    
    def set_target_classes(self, class_names):
        """
        Set target classes to detect
        
        Args:
            class_names: List of class names (e.g., ['person', 'car']) or None for all
        """
        if class_names is None:
            self.target_classes = None
            print("[ML] Detecting all classes")
        else:
            # Convert class names to IDs
            self.target_classes = []
            for name in class_names:
                for cls_id, cls_name in self.model.names.items():
                    if cls_name.lower() == name.lower():
                        self.target_classes.append(cls_id)
            
            print(f"[ML] Target classes: {class_names}")
    
    def is_running(self):
        """Check if detection is running"""
        return self.running
    
    def get_available_classes(self):
        """Get list of available class names"""
        if self.model:
            return list(self.model.names.values())
        return []


class PersonTracker:
    """
    Person tracking for camera follow functionality
    """
    
    def __init__(self, ml_detector, servo_controller):
        """
        Initialize person tracker
        
        Args:
            ml_detector: MLDetector instance
            servo_controller: ArduinoController instance
        """
        self.ml_detector = ml_detector
        self.servo = servo_controller
        self.running = False
        self.thread = None
        
        # Tracking parameters
        self.pan_servo = 1  # Servo for horizontal movement
        self.tilt_servo = 2  # Servo for vertical movement
        self.frame_center = (320, 240)  # Assume 640x480 resolution
        self.deadzone = 50  # Pixels from center to ignore
        self.speed_factor = 0.1  # Movement speed
    
    def start(self):
        """Start person tracking"""
        if self.running:
            return False
        
        # Ensure ML detection is running
        if not self.ml_detector.is_running():
            self.ml_detector.start()
        
        # Set to detect only persons
        self.ml_detector.set_target_classes(['person'])
        
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        print("[Tracker] Person tracking started")
        return True
    
    def stop(self):
        """Stop person tracking"""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        print("[Tracker] Person tracking stopped")
    
    def _tracking_loop(self):
        """Main tracking loop"""
        while self.running:
            try:
                detections = self.ml_detector.get_detections()
                
                # Find person with highest confidence
                person = None
                max_conf = 0
                
                for det in detections:
                    if det['class'] == 'person' and det['confidence'] > max_conf:
                        person = det
                        max_conf = det['confidence']
                
                if person:
                    # Calculate person center
                    bbox = person['bbox']
                    person_center_x = (bbox[0] + bbox[2]) / 2
                    person_center_y = (bbox[1] + bbox[3]) / 2
                    
                    # Calculate offset from frame center
                    offset_x = person_center_x - self.frame_center[0]
                    offset_y = person_center_y - self.frame_center[1]
                    
                    # Adjust servos if outside deadzone
                    if abs(offset_x) > self.deadzone:
                        # Pan servo (horizontal)
                        adjustment = int(offset_x * self.speed_factor)
                        # Get current position and adjust
                        # (This requires servo status query - simplified here)
                        # self.servo.send_servo_command(f'S{self.pan_servo}{new_angle:03d}')
                        pass
                    
                    if abs(offset_y) > self.deadzone:
                        # Tilt servo (vertical)
                        adjustment = int(offset_y * self.speed_factor)
                        # Similar adjustment for tilt
                        pass
                
                time.sleep(0.1)
            
            except Exception as e:
                print(f"[Tracker] Error: {e}")
                time.sleep(0.5)
    
    def is_running(self):
        """Check if tracking is active"""
        return self.running


# ============================================================================
# ALTERNATIVE: OpenCV DNN Module (No external dependencies)
# ============================================================================

class MLDetectorOpenCV:
    """
    Alternative detector using OpenCV's DNN module with MobileNet-SSD
    Requires only opencv-python (no torch/ultralytics)
    """
    
    def __init__(self, camera):
        """Initialize OpenCV DNN detector"""
        self.camera = camera
        self.net = None
        self.running = False
        self.detections = []
        self.detection_lock = threading.Lock()
        
        # COCO class names
        self.class_names = ["background", "person", "bicycle", "car", "motorcycle",
                           "airplane", "bus", "train", "truck", "boat"]
        
        # Try to load MobileNet-SSD model
        try:
            # Download model files first:
            # wget https://github.com/chuanqi305/MobileNet-SSD/raw/master/MobileNetSSD_deploy.prototxt
            # wget https://github.com/chuanqi305/MobileNet-SSD/raw/master/MobileNetSSD_deploy.caffemodel
            
            prototxt = "models/MobileNetSSD_deploy.prototxt"
            caffemodel = "models/MobileNetSSD_deploy.caffemodel"
            
            self.net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
            print("[ML-OpenCV] MobileNet-SSD loaded")
        except Exception as e:
            print(f"[ML-OpenCV] Failed to load model: {e}")
            print("[ML-OpenCV] Download model files to 'models/' directory")
    
    def start(self):
        """Start detection"""
        if not self.net:
            return False
        
        if self.running:
            return False
        
        self.running = True
        threading.Thread(target=self._detection_loop, daemon=True).start()
        return True
    
    def _detection_loop(self):
        """Detection loop"""
        while self.running:
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # Prepare blob
                blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
                self.net.setInput(blob)
                detections_raw = self.net.forward()
                
                # Parse detections
                h, w = frame.shape[:2]
                detections = []
                
                for i in range(detections_raw.shape[2]):
                    confidence = detections_raw[0, 0, i, 2]
                    
                    if confidence > 0.5:
                        class_id = int(detections_raw[0, 0, i, 1])
                        
                        if class_id < len(self.class_names):
                            box = detections_raw[0, 0, i, 3:7] * np.array([w, h, w, h])
                            x1, y1, x2, y2 = box.astype(int)
                            
                            detections.append({
                                'class': self.class_names[class_id],
                                'confidence': float(confidence),
                                'bbox': [x1, y1, x2, y2]
                            })
                
                with self.detection_lock:
                    self.detections = detections
                
                time.sleep(0.2)
            
            except Exception as e:
                print(f"[ML-OpenCV] Error: {e}")
                time.sleep(0.5)
    
    def stop(self):
        """Stop detection"""
        self.running = False
    
    def get_detections(self):
        """Get current detections"""
        with self.detection_lock:
            return self.detections.copy()
