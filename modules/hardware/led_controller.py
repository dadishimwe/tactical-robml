"""
============================================================================
HARDWARE MODULE — LED CONTROLLER (WS2812B)
============================================================================
Manages the WS2812B addressable LED strip via the rpi_ws281x library.
Provides named lighting modes (status, night, alert) and a smooth
animation engine. Falls back gracefully when the library is unavailable.
============================================================================
"""

import threading
import time
import logging
from config import (
    LED_PIN, LED_COUNT, LED_BRIGHTNESS, LED_FREQ_HZ, LED_DMA, LED_INVERT,
    LED_COLOR_IDLE, LED_COLOR_MOVING, LED_COLOR_AUTONOMOUS,
    LED_COLOR_RECORDING, LED_COLOR_WARN, LED_COLOR_CRITICAL,
    LED_COLOR_NIGHT, LED_COLOR_ML, LED_COLOR_OFF
)

logger = logging.getLogger(__name__)

try:
    from rpi_ws281x import PixelStrip, Color
    WS281X_AVAILABLE = True
except ImportError:
    WS281X_AVAILABLE = False
    logger.warning("[LED] rpi_ws281x not available — LED control disabled.")


# ── Mode → colour mapping ───────────────────────────────────────────────────

MODE_COLORS = {
    "IDLE":      LED_COLOR_IDLE,
    "MOVING":    LED_COLOR_MOVING,
    "AUTO":      LED_COLOR_AUTONOMOUS,
    "RECORD":    LED_COLOR_RECORDING,
    "WARN":      LED_COLOR_WARN,
    "CRITICAL":  LED_COLOR_CRITICAL,
    "NIGHT":     LED_COLOR_NIGHT,
    "ML":        LED_COLOR_ML,
    "OFF":       LED_COLOR_OFF,
}


class LEDController:
    """
    Controls the WS2812B LED strip. Supports solid colours, blinking,
    and a night-mode headlight configuration (front half = white).
    """

    def __init__(self):
        self._strip = None
        self._available = False
        self._lock = threading.Lock()
        self._current_mode = "IDLE"
        self._blink_thread: threading.Thread | None = None
        self._blink_active = False
        self._night_mode = False

        if WS281X_AVAILABLE:
            try:
                self._strip = PixelStrip(
                    LED_COUNT, LED_PIN, LED_FREQ_HZ,
                    LED_DMA, LED_INVERT, LED_BRIGHTNESS
                )
                self._strip.begin()
                self._available = True
                logger.info("[LED] WS2812B strip initialised.")
                self.set_mode("IDLE")
            except Exception as exc:
                logger.warning(f"[LED] Strip init failed: {exc}")

    # ── Core Primitives ─────────────────────────────────────────────────────

    def _set_all(self, r: int, g: int, b: int) -> None:
        if not self._available:
            return
        with self._lock:
            for i in range(LED_COUNT):
                self._strip.setPixelColor(i, Color(r, g, b))
            self._strip.show()

    def _set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        if not self._available:
            return
        with self._lock:
            self._strip.setPixelColor(index, Color(r, g, b))
            self._strip.show()

    # ── Blink Engine ────────────────────────────────────────────────────────

    def _stop_blink(self) -> None:
        self._blink_active = False
        if self._blink_thread and self._blink_thread.is_alive():
            self._blink_thread.join(timeout=1.0)

    def _blink_loop(self, r: int, g: int, b: int, interval: float) -> None:
        state = True
        while self._blink_active:
            if state:
                self._set_all(r, g, b)
            else:
                self._set_all(0, 0, 0)
            state = not state
            time.sleep(interval)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        mode = mode.upper()
        self._stop_blink()
        self._current_mode = mode
        color = MODE_COLORS.get(mode, LED_COLOR_IDLE)
        r, g, b = color

        if mode == "CRITICAL":
            # Fast blink red for critical alerts
            self._blink_active = True
            self._blink_thread = threading.Thread(
                target=self._blink_loop, args=(r, g, b, 0.25), daemon=True
            )
            self._blink_thread.start()
        elif mode == "WARN":
            # Slow blink amber for warnings
            self._blink_active = True
            self._blink_thread = threading.Thread(
                target=self._blink_loop, args=(r, g, b, 0.75), daemon=True
            )
            self._blink_thread.start()
        elif mode == "NIGHT":
            self._apply_night_mode()
        else:
            self._set_all(r, g, b)

        logger.debug(f"[LED] Mode set to {mode}")

    def _apply_night_mode(self) -> None:
        """Front half of strip = white headlights, rear = dim red tail-lights."""
        if not self._available:
            return
        half = LED_COUNT // 2
        with self._lock:
            for i in range(half):
                self._strip.setPixelColor(i, Color(255, 255, 255))
            for i in range(half, LED_COUNT):
                self._strip.setPixelColor(i, Color(80, 0, 0))
            self._strip.show()

    def set_custom_color(self, r: int, g: int, b: int) -> None:
        self._stop_blink()
        self._set_all(r, g, b)

    def toggle_night_mode(self) -> bool:
        self._night_mode = not self._night_mode
        if self._night_mode:
            self.set_mode("NIGHT")
        else:
            self.set_mode(self._current_mode if self._current_mode != "NIGHT" else "IDLE")
        return self._night_mode

    def off(self) -> None:
        self._stop_blink()
        self._set_all(0, 0, 0)

    def get_status(self) -> dict:
        return {
            "available": self._available,
            "mode": self._current_mode,
            "night_mode": self._night_mode,
        }

    def cleanup(self) -> None:
        self._stop_blink()
        self.off()
