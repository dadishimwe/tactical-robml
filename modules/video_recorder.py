"""
============================================================================
VIDEO RECORDER MODULE
============================================================================

Handles video recording from camera stream with timestamps.

Features:
  - Record video clips with timestamps
  - List and manage recordings
  - Automatic file naming
  - Thread-safe recording

============================================================================
"""

import cv2
import threading
import time
import os
from datetime import datetime

class VideoRecorder:
    """Video recording handler"""
    
    def __init__(self, output_dir='data/videos', fps=20, resolution=(640, 480)):
        """
        Initialize video recorder
        
        Args:
            output_dir: Directory to save recordings
            fps: Frames per second for recording
            resolution: Video resolution (width, height)
        """
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution
        self.recording = False
        self.current_file = None
        self.writer = None
        self.camera = None
        self.record_thread = None
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[Recorder] Initialized: {output_dir}")
    
    def start_recording(self, camera):
        """
        Start recording video
        
        Args:
            camera: CameraStream object to record from
        
        Returns:
            str: Filename of the recording
        """
        if self.recording:
            print("[Recorder] Already recording")
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recording_{timestamp}.avi"
        filepath = os.path.join(self.output_dir, filename)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(
            filepath,
            fourcc,
            self.fps,
            self.resolution
        )
        
        if not self.writer.isOpened():
            print("[Recorder] Failed to open video writer")
            return None
        
        self.camera = camera
        self.current_file = filename
        self.recording = True
        
        # Start recording thread
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.record_thread.start()
        
        print(f"[Recorder] Started: {filename}")
        return filename
    
    def _record_loop(self):
        """Recording loop (runs in separate thread)"""
        frame_time = 1.0 / self.fps
        
        while self.recording:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                
                if frame is not None:
                    # Resize if necessary
                    if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                        frame = cv2.resize(frame, self.resolution)
                    
                    # Write frame
                    self.writer.write(frame)
                
                # Control recording rate
                time.sleep(frame_time)
            
            except Exception as e:
                print(f"[Recorder] Recording error: {e}")
                break
        
        # Cleanup
        if self.writer:
            self.writer.release()
        
        print(f"[Recorder] Stopped: {self.current_file}")
    
    def stop_recording(self):
        """
        Stop current recording
        
        Returns:
            str: Filename of the completed recording
        """
        if not self.recording:
            print("[Recorder] Not recording")
            return None
        
        filename = self.current_file
        self.recording = False
        
        # Wait for recording thread to finish
        if self.record_thread:
            self.record_thread.join(timeout=2.0)
        
        self.current_file = None
        self.camera = None
        
        return filename
    
    def list_recordings(self):
        """
        List all recorded videos
        
        Returns:
            list: List of recording info dicts
        """
        recordings = []
        
        try:
            for filename in os.listdir(self.output_dir):
                if filename.endswith(('.avi', '.mp4')):
                    filepath = os.path.join(self.output_dir, filename)
                    stat = os.stat(filepath)
                    
                    recordings.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'duration': self._get_video_duration(filepath)
                    })
            
            # Sort by creation time (newest first)
            recordings.sort(key=lambda x: x['created'], reverse=True)
        
        except Exception as e:
            print(f"[Recorder] List error: {e}")
        
        return recordings
    
    def _get_video_duration(self, filepath):
        """
        Get video duration in seconds
        
        Args:
            filepath: Path to video file
        
        Returns:
            float: Duration in seconds
        """
        try:
            cap = cv2.VideoCapture(filepath)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            
            if fps > 0:
                return frame_count / fps
        
        except:
            pass
        
        return 0.0
    
    def delete_recording(self, filename):
        """
        Delete a recording
        
        Args:
            filename: Name of file to delete
        
        Returns:
            bool: True if successful
        """
        try:
            filepath = os.path.join(self.output_dir, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[Recorder] Deleted: {filename}")
                return True
        
        except Exception as e:
            print(f"[Recorder] Delete error: {e}")
        
        return False
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording
