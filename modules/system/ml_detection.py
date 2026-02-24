"""
============================================================================
SYSTEM MODULE — ML OBJECT DETECTION (YOLOv8 / NCNN)
============================================================================
Wraps Ultralytics YOLOv8 inference with:
  • NCNN export preference for maximum Raspberry Pi performance
  • Frame-rate limiting to protect CPU headroom
  • Thread-safe detection result sharing
  • Annotated frame overlay injection into the camera pipeline
Falls back gracefully when ultralytics is not installed.
============================================================================
"""

import threading
import time
import logging
from config import ML_MODEL_NAME, ML_CONFIDENCE_THRESHOLD, ML_DETECTION_FPS

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    import numpy as np
    import cv2
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    logger.warning("[ML] ultralytics not installed — ML detection disabled.")


class MLDetector:
    """
    Runs YOLOv8 inference on camera frames and exposes detection results
    to the rest of the application. Designed to be injected into the
    CameraManager as an overlay function.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._available = False
        self._enabled = False
        self._detections: list = []
        self._frame_interval = 1.0 / ML_DETECTION_FPS
        self._last_run = 0.0

        if ULTRALYTICS_AVAILABLE:
            self._load_model()

    # ── Model Loading ────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        try:
            # Prefer NCNN export for Raspberry Pi performance
            ncnn_path = ML_MODEL_NAME.replace(".pt", "_ncnn_model")
            import os
            if os.path.isdir(ncnn_path):
                self._model = YOLO(ncnn_path, task="detect")
                logger.info(f"[ML] Loaded NCNN model from {ncnn_path}")
            else:
                self._model = YOLO(ML_MODEL_NAME)
                logger.info(f"[ML] Loaded PyTorch model {ML_MODEL_NAME}")
                logger.info("[ML] Tip: export to NCNN for ~3× faster inference on Pi.")
            self._available = True
        except Exception as exc:
            logger.error(f"[ML] Model load failed: {exc}")
            self._available = False

    # ── Overlay Function (injected into CameraManager) ───────────────────────

    def process_frame(self, frame_array):
        """
        Called by CameraManager for each captured frame.
        Returns the frame (annotated if ML is enabled and ready).
        """
        if not self._enabled or not self._available:
            return frame_array

        now = time.time()
        if now - self._last_run < self._frame_interval:
            # Return last annotated frame without re-running inference
            return frame_array

        self._last_run = now
        try:
            results = self._model.predict(
                frame_array,
                conf=ML_CONFIDENCE_THRESHOLD,
                verbose=False,
                stream=False,
            )
            detections = []
            annotated = frame_array.copy()
            for result in results:
                for box in result.boxes:
                    cls_id  = int(box.cls[0])
                    conf    = float(box.conf[0])
                    label   = self._model.names.get(cls_id, str(cls_id))
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                    detections.append({
                        "label": label,
                        "confidence": round(conf, 2),
                        "bbox": [x1, y1, x2, y2],
                    })
                    # Draw bounding box
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated, f"{label} {conf:.0%}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (0, 255, 0), 1
                    )

            with self._lock:
                self._detections = detections

            return annotated
        except Exception as exc:
            logger.debug(f"[ML] Inference error: {exc}")
            return frame_array

    # ── Control ──────────────────────────────────────────────────────────────

    def enable(self) -> bool:
        if not self._available:
            return False
        self._enabled = True
        logger.info("[ML] Detection enabled.")
        return True

    def disable(self) -> None:
        self._enabled = False
        logger.info("[ML] Detection disabled.")

    # ── Status ───────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        with self._lock:
            return {
                "available": self._available,
                "enabled":   self._enabled,
                "detections": list(self._detections),
                "model": ML_MODEL_NAME,
                "fps_limit": ML_DETECTION_FPS,
            }
