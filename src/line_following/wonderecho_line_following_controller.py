#!/usr/bin/env python3
"""
LUNA — WonderEcho Line-Following Controller

This module connects WonderEcho voice commands to the TurboPi robot movement
system and line-following behaviour.

It supports:
- Basic voice-controlled movement: forward, backward, left, right, stop
- Starting a line-following routine using a voice command
- Stopping line-following when manual movement commands are triggered
- Logging recognised command IDs for troubleshooting

Note:
This script expects the Hiwonder TurboPi SDK to be installed on the Raspberry Pi.
The line-following routine is launched as a subprocess. If you have a custom
line-following script, update LINE_SCRIPT_PATH or set the LUNA_LINE_SCRIPT
environment variable.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from smbus2 import SMBus


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

I2C_ADDR = 0x34
ASR_RESULT_REG = 0x64

SDK_PATH = Path(os.getenv("LUNA_TURBOPI_SDK", "/home/pi/TurboPi"))
LINE_SCRIPT_PATH = Path(
    os.getenv("LUNA_LINE_SCRIPT", "/home/pi/TurboPi/Functions/VisualPatrol.py")
)

OVERRIDE_PATH = Path.home() / "voice_id_overrides.json"
LOG_PATH = Path.home() / "luna_voice_line_follow.log"

POLL_DELAY_SECONDS = 0.02


# ---------------------------------------------------------------------------
# WonderEcho command IDs
# ---------------------------------------------------------------------------

ID_GO = 1
ID_BACK = 2
ID_LEFT = 3
ID_RIGHT = 4
ID_STOP = 9

# WonderEcho custom action used to start line-following behaviour.
ID_START_LINE = 102

DEFAULT_ID_TO_ACTION = {
    ID_GO: "go",
    ID_BACK: "back",
    ID_LEFT: "left",
    ID_RIGHT: "right",
    ID_STOP: "stop",
    ID_START_LINE: "line_on",
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console)


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

    Example file:
    {
        "102": "line_on",
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

        logging.info("Loaded voice command overrides from %s", OVERRIDE_PATH)

    except (OSError, ValueError, json.JSONDecodeError) as error:
        logging.warning("Could not load voice overrides: %s", error)

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
# Line-following process control
# ---------------------------------------------------------------------------

class LineFollowerProcess:
    """Starts and stops the line-following routine as a subprocess."""

    def __init__(self, script_path: Path = LINE_SCRIPT_PATH) -> None:
        self.script_path = script_path
        self.process: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        if self.is_running():
            logging.info("[LINE] Line-following is already running.")
            return

        if not self.script_path.exists():
            logging.error("[LINE] Script not found: %s", self.script_path)
            return

        logging.info("[LINE] Starting line-following: %s", self.script_path)

        self.process = subprocess.Popen(
            [sys.executable, str(self.script_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def stop(self) -> None:
        if not self.is_running():
            return

        logging.info("[LINE] Stopping line-following.")

        try:
            self.process.send_signal(signal.SIGINT)
            self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            logging.warning("[LINE] Graceful stop timed out. Terminating process.")
            self.process.terminate()

            try:
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                logging.warning("[LINE] Terminate timed out. Killing process.")
                self.process.kill()
        finally:
            self.process = None
            logging.info("[LINE] Line-following stopped.")


# ---------------------------------------------------------------------------
# Main control loop
# ---------------------------------------------------------------------------

def handle_action(
    action: Optional[str],
    motion: MotionController,
    line_follower: LineFollowerProcess,
) -> None:
    """Run the robot behaviour mapped to a WonderEcho action."""
    if action in {"go", "back", "left", "right"}:
        # Manual movement takes priority so it does not fight line-following.
        line_follower.stop()

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
        line_follower.stop()
    elif action == "line_on":
        line_follower.start()
    elif action is None:
        return
    else:
        logging.info("[ASR] Unmapped action ignored: %s", action)


def main() -> None:
    logging.info("=== LUNA WonderEcho Line-Following Controller ===")
    logging.info("Supported actions: go, back, left, right, stop, line_on")

    command_map = load_voice_overrides()
    motion = MotionController()
    line_follower = LineFollowerProcess()

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

                logging.info("[ASR] id=%s -> %s", command_id, action or "unmapped")
                handle_action(action, motion, line_follower)

    except KeyboardInterrupt:
        logging.info("[EXIT] Stopping LUNA controller.")
    finally:
        try:
            motion.stop()
            line_follower.stop()
        except Exception as error:
            logging.warning("Shutdown cleanup issue: %s", error)


if __name__ == "__main__":
    main()
