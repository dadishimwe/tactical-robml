"""
============================================================================
HARDWARE MODULE — CAMERA MANAGER
============================================================================
Manages the primary Pi Camera (via picamera2) and an optional secondary
ESP32-CAM stream. Provides MJPEG frame generation for Flask streaming
and supports ML overlay injection. Falls back to a test pattern when no
camera hardware is available.
============================================================================
"""

import io
import time
import threading
import logging
from config import (
    CAMERA_RESOLUTION, CAMERA_FRAMERATE, CAMERA_JPEG_QUALITY, ESP32_CAM_URL
)

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logger.warning("[Camera] picamera2 not available — using test pattern.")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class CameraManager:
    """
    Provides a thread-safe MJPEG frame source. Supports:
      • Primary  — Raspberry Pi Camera Module (CSI)
      • Secondary — ESP32-CAM over HTTP (optional)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frame: bytes | None = None
        self._camera = None
        self._available = False
        self._active_source = "primary"
        self._ml_overlay_fn = None   # Callable injected by ML module
        self._recording = False
        self._video_writer = None

        self._init_primary()

    # ── Initialisation ───────────────────────────────────────────────────────

    def _init_primary(self) -> None:
        if not PICAMERA2_AVAILABLE:
            logger.warning("[Camera] Pi Camera not available.")
            threading.Thread(target=self._test_pattern_loop, daemon=True).start()
            return
        try:
            self._camera = Picamera2()
            config = self._camera.create_video_configuration(
                main={"size": CAMERA_RESOLUTION, "format": "RGB888"},
                controls={"FrameRate": CAMERA_FRAMERATE},
            )
            self._camera.configure(config)
            self._camera.start()
            self._available = True
            logger.info("[Camera] Pi Camera started.")
            threading.Thread(target=self._capture_loop, daemon=True, name="CameraCapture").start()
        except Exception as exc:
            logger.error(f"[Camera] Pi Camera init failed: {exc}")
            threading.Thread(target=self._test_pattern_loop, daemon=True).start()

    # ── Capture Loops ────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        while True:
            try:
                frame_array = self._camera.capture_array()
                if self._ml_overlay_fn:
                    frame_array = self._ml_overlay_fn(frame_array)
                if CV2_AVAILABLE:
                    _, jpeg = cv2.imencode(
                        ".jpg", frame_array,
                        [cv2.IMWRITE_JPEG_QUALITY, CAMERA_JPEG_QUALITY]
                    )
                    frame_bytes = jpeg.tobytes()
                else:
                    import PIL.Image as PILImage
                    img = PILImage.fromarray(frame_array)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=CAMERA_JPEG_QUALITY)
                    frame_bytes = buf.getvalue()

                with self._lock:
                    self._frame = frame_bytes

                if self._recording and self._video_writer and CV2_AVAILABLE:
                    self._video_writer.write(frame_array)

            except Exception as exc:
                logger.debug(f"[Camera] Capture error: {exc}")
            time.sleep(1.0 / CAMERA_FRAMERATE)

    def _test_pattern_loop(self) -> None:
        """Generate a grey test-card frame when no camera is present."""
        if not CV2_AVAILABLE:
            return
        w, h = CAMERA_RESOLUTION
        while True:
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            ts = time.strftime("%H:%M:%S")
            cv2.putText(frame, "NO CAMERA", (w // 2 - 100, h // 2 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 0), 2)
            cv2.putText(frame, ts, (w // 2 - 50, h // 2 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 1)
            _, jpeg = cv2.imencode(".jpg", frame)
            with self._lock:
                self._frame = jpeg.tobytes()
            time.sleep(1.0 / 10)

    # ── MJPEG Generator ──────────────────────────────────────────────────────

    def generate_frames(self):
        """Yield MJPEG multipart frames for Flask streaming response."""
        while True:
            with self._lock:
                frame = self._frame
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(1.0 / CAMERA_FRAMERATE)

    # ── Recording ────────────────────────────────────────────────────────────

    def start_recording(self, filepath: str) -> bool:
        if not CV2_AVAILABLE or self._recording:
            return False
        w, h = CAMERA_RESOLUTION
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._video_writer = cv2.VideoWriter(filepath, fourcc, CAMERA_FRAMERATE, (w, h))
        self._recording = True
        logger.info(f"[Camera] Recording started → {filepath}")
        return True

    def stop_recording(self) -> bool:
        if not self._recording:
            return False
        self._recording = False
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
        logger.info("[Camera] Recording stopped.")
        return True

    # ── ML Overlay ───────────────────────────────────────────────────────────

    def set_ml_overlay(self, fn) -> None:
        """Inject an ML overlay function (frame_array → annotated_frame_array)."""
        self._ml_overlay_fn = fn

    def clear_ml_overlay(self) -> None:
        self._ml_overlay_fn = None

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "available": self._available,
            "source": self._active_source,
            "recording": self._recording,
            "resolution": CAMERA_RESOLUTION,
            "framerate": CAMERA_FRAMERATE,
            "esp32_cam_url": ESP32_CAM_URL,
        }

    def cleanup(self) -> None:
        self.stop_recording()
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
