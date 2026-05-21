#!/usr/bin/env python3
"""
LUNA — WonderEcho Voice Control with Snapshot Capture

This module connects the WonderEcho voice-recognition module to the TurboPi
movement system and camera capture workflow.

It supports:
- Voice-controlled movement: forward, backward, left, right, stop
- Voice-triggered snapshot capture
- I²C command reading from the WonderEcho module
- Simple debounce logic to avoid repeated command triggers

Note:
This script is designed for Raspberry Pi + Hiwonder TurboPi hardware.
It expects the HiwonderSDK and OpenCV dependencies to be installed on the robot.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from smbus2 import SMBus


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

I2C_ADDR = 0x34
ASR_RESULT_REG = 0x64

SDK_PATH = Path(os.getenv("LUNA_TURBOPI_SDK", "/home/pi/TurboPi"))
OVERRIDE_PATH = Path.home() / "voice_id_overrides.json"
SNAPSHOT_DIR = Path(os.getenv("LUNA_SNAPSHOT_DIR", "./snapshots"))

POLL_DELAY_SECONDS = 0.02
CAMERA_PROBE_INDEXES = (0, 1, 2)
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ---------------------------------------------------------------------------
# WonderEcho command IDs
# ---------------------------------------------------------------------------

ID_GO = 1
ID_BACK = 2
ID_LEFT = 3
ID_RIGHT = 4
ID_STOP = 9

# Custom WonderEcho action for taking a photo.
ID_SNAPSHOT = 131

DEFAULT_ID_TO_ACTION = {
    ID_GO: "go",
    ID_BACK: "back",
    ID_LEFT: "left",
    ID_RIGHT: "right",
    ID_STOP: "stop",
    ID_SNAPSHOT: "snapshot",
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
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MotionSettings:
    """Movement timing and speed settings for voice-controlled movement."""

    forward_speed_percent: int = 50
    forward_time_seconds: float = 0.8
    turn_yaw_rate: float = 0.7
    turn_time_seconds: float = 0.5


# ---------------------------------------------------------------------------
# WonderEcho helpers
# ---------------------------------------------------------------------------

def load_voice_overrides() -> dict[int, str]:
    """
    Load optional command-ID overrides from ~/voice_id_overrides.json.

    This makes the script easier to tune without editing the source code.

    Example:
    {
        "131": "snapshot",
        "9": "stop"
    }
    """
    command_map = dict(DEFAULT_ID_TO_ACTION)

    if not OVERRIDE_PATH.exists():
        return command_map

    try:
        with OVERRIDE_PATH.open("r", encoding="utf-8") as file:
            overrides = json.load(file)

        for key, value in overrides.items():
            command_map[int(key)] = str(value)

        logger.info("Loaded voice command overrides from %s", OVERRIDE_PATH)

    except (OSError, ValueError, json.JSONDecodeError) as error:
        logger.warning("Could not load voice overrides: %s", error)

    return command_map


def read_wonderecho_id(bus: SMBus) -> Optional[int]:
    """Read the latest command ID from the WonderEcho module."""
    try:
        data = bus.read_i2c_block_data(I2C_ADDR, ASR_RESULT_REG, 1)
        return data[0] if data else None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Robot motion
# ---------------------------------------------------------------------------

class MotionController:
    """Small wrapper around the Hiwonder mecanum chassis API."""

    def __init__(self, settings: Optional[MotionSettings] = None) -> None:
        self.settings = settings or MotionSettings()
        self.car = self._load_chassis()

    def _load_chassis(self):
        """
        Load the Hiwonder mecanum chassis class.

        The SDK is normally installed under /home/pi/TurboPi on the robot.
        """
        sys.path.insert(0, str(SDK_PATH))

        try:
            from HiwonderSDK import mecanum
            return mecanum.MecanumChassis()
        except ImportError as error:
            raise RuntimeError(
                "Could not import HiwonderSDK.mecanum. "
                "Check that the TurboPi SDK is installed and SDK_PATH is correct."
            ) from error

    def forward(self) -> None:
        self.car.set_velocity(self.settings.forward_speed_percent, 90, 0)
        time.sleep(self.settings.forward_time_seconds)
        self.stop()

    def back(self) -> None:
        self.car.set_velocity(self.settings.forward_speed_percent, 270, 0)
        time.sleep(self.settings.forward_time_seconds)
        self.stop()

    def left(self) -> None:
        self.car.set_velocity(0, 90, self.settings.turn_yaw_rate)
        time.sleep(self.settings.turn_time_seconds)
        self.stop()

    def right(self) -> None:
        self.car.set_velocity(0, 90, -self.settings.turn_yaw_rate)
        time.sleep(self.settings.turn_time_seconds)
        self.stop()

    def stop(self) -> None:
        self.car.set_velocity(0, 90, 0)


# ---------------------------------------------------------------------------
# Camera snapshot capture
# ---------------------------------------------------------------------------

class SnapshotCapture:
    """Handles camera probing and snapshot saving."""

    def __init__(self, output_dir: Path = SNAPSHOT_DIR) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """
        Try to open a camera from common Linux camera indexes.

        Different Raspberry Pi setups may expose the camera as /dev/video0,
        /dev/video1, or /dev/video2, so probing makes the script more flexible.
        """
        for index in CAMERA_PROBE_INDEXES:
            camera = cv2.VideoCapture(index, cv2.CAP_V4L2)

            if camera is None or not camera.isOpened():
                if camera is not None:
                    camera.release()
                continue

            camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            return camera

        return None

    def take_snapshot(self) -> Optional[Path]:
        """Capture one frame and save it as a timestamped JPG image."""
        camera = self._open_camera()

        if camera is None:
            logger.error("[SNAPSHOT] Could not open camera.")
            return None

        try:
            success, frame = camera.read()
        finally:
            camera.release()

        if not success or frame is None:
            logger.error("[SNAPSHOT] Failed to capture frame.")
            return None

        filename = f"luna_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        output_path = self.output_dir / filename

        if cv2.imwrite(str(output_path), frame):
            logger.info("[SNAPSHOT] Saved image: %s", output_path)
            return output_path

        logger.error("[SNAPSHOT] Could not write image to disk.")
        return None


# ---------------------------------------------------------------------------
# Main action handler
# ---------------------------------------------------------------------------

def handle_action(
    action: Optional[str],
    motion: MotionController,
    snapshot: SnapshotCapture,
) -> None:
    """Run the robot behaviour mapped to a WonderEcho action."""
    if action == "go":
        motion.forward()
    elif action == "back":
        motion.back()
    elif action == "left":
        motion.left()
    elif action == "right":
        motion.right()
    elif action == "stop":
        motion.stop()
    elif action == "snapshot":
        snapshot.take_snapshot()
    elif action is None:
        return
    else:
        logger.info("[ASR] Unmapped action ignored: %s", action)


def main() -> None:
    logger.info("=== LUNA WonderEcho Voice Control + Snapshot ===")
    logger.info("Supported actions: go, back, left, right, stop, snapshot")

    command_map = load_voice_overrides()
    motion = MotionController()
    snapshot = SnapshotCapture()

    last_id: Optional[int] = None

    try:
        with SMBus(1) as bus:
            while True:
                command_id = read_wonderecho_id(bus)

                if command_id is None:
                    time.sleep(POLL_DELAY_SECONDS)
                    continue

                # Debounce repeated command frames.
                if command_id == last_id:
                    time.sleep(POLL_DELAY_SECONDS)
                    continue

                last_id = command_id
                action = command_map.get(command_id)

                logger.info("[ASR] id=%s -> %s", command_id, action or "unmapped")
                handle_action(action, motion, snapshot)

    except KeyboardInterrupt:
        logger.info("[EXIT] Stopping LUNA voice snapshot controller.")
    finally:
        try:
            motion.stop()
        except Exception as error:
            logger.warning("Shutdown cleanup issue: %s", error)


if __name__ == "__main__":
    main()
