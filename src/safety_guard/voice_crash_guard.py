#!/usr/bin/env python3
"""
LUNA — WonderEcho Voice Control with Ultrasonic Crash Guard

Connects WonderEcho voice commands to the TurboPi movement system.
Adds a sonar-based safety gate to the "go" (forward) command: if an obstacle
is detected within the configured distance threshold, the robot stops early.

Only forward movement is guarded — all other commands behave identically to
standard voice control. If no ultrasonic sensor is found at startup, the guard
disables itself silently so the script still works without the sonar attached.

Supported voice commands: go, back, left, right, stop
Voice command IDs can be customised at runtime via ~/voice_id_overrides.json.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from smbus2 import SMBus


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SDK_PATH = Path(os.getenv("LUNA_TURBOPI_SDK", "/home/pi/TurboPi"))
OVERRIDE_PATH = Path.home() / "voice_id_overrides.json"

# WonderEcho I²C interface
I2C_ADDR = 0x34
ASR_RESULT_REG = 0x64
POLL_DELAY_SECONDS = 0.02

# Ultrasonic sonar I²C address (Hiwonder sonar board)
SONAR_I2C_ADDR = 0x77

# Default crash-guard threshold. Adjust to taste — 200 cm is conservative
# for indoor use; lower values (e.g., 30–50 cm) are safer in tight spaces.
DEFAULT_THRESHOLD_CM = 200

# Sonar polling rate inside the forward burst
SONAR_POLL_HZ = 20


# ---------------------------------------------------------------------------
# WonderEcho command IDs
# ---------------------------------------------------------------------------

ID_GO = 1
ID_BACK = 2
ID_LEFT = 3
ID_RIGHT = 4
ID_STOP = 9

DEFAULT_ID_TO_ACTION: dict[int, str] = {
    ID_GO: "go",
    ID_BACK: "back",
    ID_LEFT: "left",
    ID_RIGHT: "right",
    ID_STOP: "stop",
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WonderEcho helpers
# ---------------------------------------------------------------------------

def load_voice_overrides() -> dict[int, str]:
    """
    Load optional command-ID overrides from ~/voice_id_overrides.json.

    Example file:
    {
        "1": "go",
        "9": "stop"
    }
    """
    command_map = dict(DEFAULT_ID_TO_ACTION)

    if not OVERRIDE_PATH.exists():
        return command_map

    try:
        with OVERRIDE_PATH.open("r", encoding="utf-8") as f:
            overrides = json.load(f)
        for key, value in overrides.items():
            command_map[int(key)] = str(value)
        logger.info("Loaded voice overrides from %s", OVERRIDE_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logger.warning("Could not load voice overrides: %s", error)

    return command_map


def read_wonderecho_id(bus: SMBus) -> Optional[int]:
    """Read the latest command ID from the WonderEcho module over I²C."""
    try:
        data = bus.read_i2c_block_data(I2C_ADDR, ASR_RESULT_REG, 1)
        return data[0] if data else None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Robot motion
# ---------------------------------------------------------------------------

class MotionController:
    """Wrapper around the Hiwonder mecanum chassis API."""

    FWD_SPEED_PERCENT: int = 50
    FWD_TIME_SECONDS: float = 0.8
    TURN_YAW_RATE: float = 0.7
    TURN_TIME_SECONDS: float = 0.5

    def __init__(self) -> None:
        self.car = self._load_chassis()

    def _load_chassis(self):
        sys.path.insert(0, str(SDK_PATH))
        try:
            from HiwonderSDK import mecanum
            return mecanum.MecanumChassis()
        except ImportError as error:
            raise RuntimeError(
                "Could not import HiwonderSDK.mecanum. "
                "Ensure the TurboPi SDK is installed and SDK_PATH is correct."
            ) from error

    def forward(self) -> None:
        self.car.set_velocity(self.FWD_SPEED_PERCENT, 90, 0)
        time.sleep(self.FWD_TIME_SECONDS)
        self.stop()

    def back(self) -> None:
        self.car.set_velocity(self.FWD_SPEED_PERCENT, 270, 0)
        time.sleep(self.FWD_TIME_SECONDS)
        self.stop()

    def left(self) -> None:
        self.car.set_velocity(0, 90, self.TURN_YAW_RATE)
        time.sleep(self.TURN_TIME_SECONDS)
        self.stop()

    def right(self) -> None:
        self.car.set_velocity(0, 90, -self.TURN_YAW_RATE)
        time.sleep(self.TURN_TIME_SECONDS)
        self.stop()

    def stop(self) -> None:
        self.car.set_velocity(0, 90, 0)


# ---------------------------------------------------------------------------
# Crash guard
# ---------------------------------------------------------------------------

class CrashGuard:
    """
    Sonar-based safety gate for forward movement.

    Uses the Hiwonder I²C ultrasonic sensor. If the sensor is not present
    at startup, the guard disables itself — safe_forward() falls back to
    normal forward movement without any sonar check.
    """

    def __init__(self, threshold_cm: int = DEFAULT_THRESHOLD_CM) -> None:
        self.threshold_cm = threshold_cm
        self._sonar = None
        self._board = None
        self._enabled = False

        self._init_sonar()

    def _init_sonar(self) -> None:
        """Try to import and initialise the Hiwonder sonar and LED board."""
        sys.path.insert(0, str(SDK_PATH))

        try:
            import Sonar as SonarModule
            import HiwonderSDK.Board as Board

            self._sonar = SonarModule.Sonar()
            self._board = Board

            # Turn off LEDs at startup
            Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
            Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
            Board.RGB.show()

            self._enabled = True
            logger.info("[GUARD] Crash guard ON — threshold %d cm", self.threshold_cm)

        except Exception:
            logger.info("[GUARD] Sonar not found — crash guard OFF, running in normal mode.")

    def _distance_cm(self) -> Optional[int]:
        """Return current sonar distance in cm, or None on error."""
        if not self._sonar:
            return None
        try:
            return int(self._sonar.getDistance()) // 10  # mm → cm
        except Exception:
            return None

    def _alert(self) -> None:
        """Flash LEDs red once to signal a crash-guard stop."""
        if not self._board:
            return
        try:
            self._board.RGB.setPixelColor(0, self._board.PixelColor(255, 0, 0))
            self._board.RGB.setPixelColor(1, self._board.PixelColor(255, 0, 0))
            self._board.RGB.show()
            time.sleep(0.25)
            self._board.RGB.setPixelColor(0, self._board.PixelColor(0, 0, 0))
            self._board.RGB.setPixelColor(1, self._board.PixelColor(0, 0, 0))
            self._board.RGB.show()
        except Exception:
            pass

    def safe_forward(self, motion: MotionController) -> None:
        """
        Drive forward for the normal duration, but poll the sonar and stop
        early if an obstacle is detected within the threshold.

        Falls back to normal motion.forward() if sonar is not available.
        """
        if not self._enabled:
            motion.forward()
            return

        motion.car.set_velocity(motion.FWD_SPEED_PERCENT, 90, 0)
        t_start = time.time()
        poll_interval = 1.0 / SONAR_POLL_HZ

        try:
            while time.time() - t_start < motion.FWD_TIME_SECONDS:
                distance = self._distance_cm()
                if distance is not None and distance < self.threshold_cm:
                    logger.info("[GUARD] Obstacle at %d cm — stopping early.", distance)
                    motion.car.set_velocity(0, 90, 0)
                    self._alert()
                    return
                time.sleep(poll_interval)
        finally:
            motion.car.set_velocity(0, 90, 0)


# ---------------------------------------------------------------------------
# Main control loop
# ---------------------------------------------------------------------------

def handle_action(
    action: Optional[str],
    motion: MotionController,
    guard: CrashGuard,
) -> None:
    """Route a WonderEcho action to the appropriate robot behaviour."""
    if action == "go":
        guard.safe_forward(motion)  # guarded forward only
    elif action == "back":
        motion.back()
    elif action == "left":
        motion.left()
    elif action == "right":
        motion.right()
    elif action == "stop":
        motion.stop()
    elif action is None:
        return
    else:
        logger.info("[ASR] Unmapped action ignored: %s", action)


def main() -> None:
    logger.info("=== LUNA Voice Control + Crash Guard ===")
    logger.info("Commands: go (guarded), back, left, right, stop")

    command_map = load_voice_overrides()
    motion = MotionController()
    guard = CrashGuard(threshold_cm=DEFAULT_THRESHOLD_CM)

    last_id: Optional[int] = None

    try:
        with SMBus(1) as bus:
            while True:
                command_id = read_wonderecho_id(bus)

                if command_id is None:
                    time.sleep(POLL_DELAY_SECONDS)
                    continue

                if command_id == last_id:
                    time.sleep(POLL_DELAY_SECONDS)
                    continue

                last_id = command_id
                action = command_map.get(command_id)

                logger.info("[ASR] id=%s -> %s", command_id, action or "unmapped")
                handle_action(action, motion, guard)

    except KeyboardInterrupt:
        logger.info("[EXIT] Shutting down.")
    finally:
        try:
            motion.stop()
        except Exception as error:
            logger.warning("Shutdown error: %s", error)


if __name__ == "__main__":
    main()
