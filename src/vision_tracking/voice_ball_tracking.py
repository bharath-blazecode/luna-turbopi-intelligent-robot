#!/usr/bin/env python3
"""
LUNA — WonderEcho Voice Control with Ball Tracking

Stand-alone script that combines WonderEcho voice commands with
camera-based ball tracking. Voice commands trigger tracking start/stop:

  ID 128 (EXECUTE-ACTION-ONE)   → track RED ball
  ID 129 (EXECUTE-ACTION-TWO)   → track GREEN ball
  ID 130 (EXECUTE-ACTION-THREE) → track BLUE ball
  ID 9   (stop)                 → stop tracking

This script implements its own tracking loop (head + wheels) without
the Flask server. It is suited for standalone use on the robot when the
GUI control app is not needed.

The Tracker class uses:
  - LAB colour-space detection loaded from Hiwonder YAML config
  - Proportional + small integral gimbal control (head thread, ~55 Hz)
  - PID-based chassis following (wheel thread, ~50 Hz)
  - Raster scan when the target is lost

Dependencies (pip): smbus2, opencv-python, numpy
SDK (on-device): HiwonderSDK, Camera, yaml_handle — installed with TurboPi.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from smbus2 import SMBus


# ---------------------------------------------------------------------------
# SDK path
# ---------------------------------------------------------------------------

SDK_PATH = Path(os.getenv("LUNA_TURBOPI_SDK", "/home/pi/TurboPi"))
sys.path.insert(0, str(SDK_PATH))

try:
    import Camera
    import yaml_handle
    import HiwonderSDK.Board as Board
    import HiwonderSDK.Misc as Misc
    import HiwonderSDK.PID as PID
    import HiwonderSDK.mecanum as mecanum
except ImportError:
    # Allow import resolution from local copies during development
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import Camera
    import yaml_handle
    import HiwonderSDK.Board as Board
    import HiwonderSDK.Misc as Misc
    import HiwonderSDK.PID as PID
    import HiwonderSDK.mecanum as mecanum
    print("[WARN] Using local SDK copies.")


# ---------------------------------------------------------------------------
# WonderEcho I²C
# ---------------------------------------------------------------------------

ASR_I2C_ADDR = 0x34
ASR_RESULT_REG = 0x64

ID_TRACK_RED   = 128
ID_TRACK_GREEN = 129
ID_TRACK_BLUE  = 130
ID_STOP        = 9


def read_asr_id(bus: SMBus) -> int:
    """Read the latest WonderEcho command ID. Returns 0 on error."""
    try:
        d = bus.read_i2c_block_data(ASR_I2C_ADDR, ASR_RESULT_REG, 1)
        return d[0] if d else 0
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Frame and servo constants
# ---------------------------------------------------------------------------

FRAME_SIZE = (640, 480)

SERVO_X_LIMITS = (800, 2200)   # pan servo pulse range
SERVO_Y_LIMITS = (1200, 1900)  # tilt servo pulse range

YAW_SIGN   = +1
PITCH_SIGN = +1

# Head control gains
KP_YAW_PULSE_PER_PX   = 0.40
KP_PITCH_PULSE_PER_PX = 0.44
KI_YAW_PULSE_PER_PX_S   = 0.020   # small integral term (per second)
KI_PITCH_PULSE_PER_PX_S = 0.025
I_CLAMP = 180                      # anti-windup clamp (± pulses)

HEAD_DT = 0.018  # ~55 Hz head update loop

# Raster scan parameters
PAN_RANGE_PULSE  = 420
TILT_RANGE_PULSE = 260
ROW_STEP_PULSE   = 60
PAN_SPEED_PULSE  = 38
SCAN_TICK        = 0.06

# Lock/unlock system — requires this many consecutive detections
LOCK_FRAMES    = 4
UNLOCK_TIMEOUT = 0.50
CENTER_DB_PX   = 6   # deadband in px before treating target as centred

# Chassis PID parameters
car = mecanum.MecanumChassis()
car_x_pid = PID.PID(P=0.15, I=0.001, D=0.0001)
car_y_pid = PID.PID(P=1.00, I=0.001, D=0.0001)

TARGET_RADIUS = 100  # px — safe following distance (by apparent ball radius)
DX_DEADBAND   = 15   # px — ignore small lateral errors
DY_DEADBAND   = 15   # px — ignore small distance errors
MAX_SPEED     = 80   # max chassis speed %


# ---------------------------------------------------------------------------
# LAB colour thresholds
# ---------------------------------------------------------------------------

LAB: Optional[dict] = None


def load_lab() -> None:
    global LAB
    LAB = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)


# ---------------------------------------------------------------------------
# Target data model
# ---------------------------------------------------------------------------

@dataclass
class Target:
    cx: int = -1
    cy: int = -1
    r: int = 0
    color: str = "None"


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# ---------------------------------------------------------------------------
# Tracker (head + wheel threads)
# ---------------------------------------------------------------------------

class Tracker:
    """
    Tracks a coloured ball using the camera.

    Head thread (~55 Hz):
      - Applies a PI controller to keep the detected target centred in the frame.
      - Falls through to a raster scan when the target is lost.

    Wheel thread (~50 Hz):
      - Drives the chassis toward the target based on apparent ball radius (distance)
        and the pan servo error (lateral position).
      - Uses HiwonderSDK PID controllers for both axes.
    """

    def __init__(self) -> None:
        load_lab()

        servo_cfg = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)
        self.cx0 = int(servo_cfg.get("servo2", 1500))  # pan centre pulse
        self.cy0 = int(servo_cfg.get("servo1", 1500))  # tilt centre pulse

        self.sx = clamp(self.cx0, *SERVO_X_LIMITS)
        self.sy = clamp(self.cy0, *SERVO_Y_LIMITS)

        half_pan  = PAN_RANGE_PULSE  // 2
        half_tilt = TILT_RANGE_PULSE // 2
        self.pan_min  = clamp(self.cx0 - half_pan,  *SERVO_X_LIMITS)
        self.pan_max  = clamp(self.cx0 + half_pan,  *SERVO_X_LIMITS)
        self.tilt_min = clamp(self.cy0 - half_tilt, *SERVO_Y_LIMITS)
        self.tilt_max = clamp(self.cy0 + half_tilt, *SERVO_Y_LIMITS)

        self.scan_dir = +1
        self.scan_row = self.sy

        self.colors: tuple = ("red",)
        self.cam: Optional[Camera.Camera] = None
        self.size = FRAME_SIZE
        self.t = Target()
        self.running = False

        self.locked = False
        self._lock_ok = 0
        self.last_seen = 0.0

        # Head PI integrators
        self.iy = 0.0
        self.ip = 0.0
        self.last_head_t = 0.0

        self._th_head   = threading.Thread(target=self._head_loop,  daemon=True)
        self._th_wheels = threading.Thread(target=self._wheel_loop, daemon=True)

        Board.setPWMServoPulse(2, self.sx, 600)
        Board.setPWMServoPulse(1, self.sy, 600)

    def start(self, cam: Camera.Camera, colors: tuple = ("red",)) -> None:
        self.colors = colors
        self.cam = cam
        self.running = True
        if not self._th_head.is_alive():
            self._th_head.start()
        if not self._th_wheels.is_alive():
            self._th_wheels.start()
        print(f"[TRACK] start — target colours: {self.colors}")

    def stop(self) -> None:
        self.running = False
        self.locked = False
        self._lock_ok = 0
        self._car_stop()
        print("[TRACK] stop")

    def _car_stop(self) -> None:
        car.translation(0, 0)

    def _vision(self, img: np.ndarray) -> None:
        """Detect the target colour in the frame and update self.t."""
        frame = cv2.resize(img, self.size, interpolation=cv2.INTER_NEAREST)
        lab = cv2.cvtColor(cv2.GaussianBlur(frame, (3, 3), 3), cv2.COLOR_BGR2LAB)

        best_cnt  = None
        best_area = 0
        best_color = "None"

        for c in self.colors:
            if c not in LAB:
                continue
            lo = tuple(LAB[c]["min"])
            hi = tuple(LAB[c]["max"])
            mask   = cv2.inRange(lab, lo, hi)
            opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  np.ones((3, 3), np.uint8))
            closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]

            for cnt in (contours or []):
                area = abs(cv2.contourArea(cnt))
                if area > best_area and area > 300:
                    best_area, best_cnt, best_color = area, cnt, c

        if best_cnt is None:
            self.t = Target(-1, -1, 0, "None")
            return

        (cx, cy), rad = cv2.minEnclosingCircle(best_cnt)
        cx  = int(Misc.map(cx,  0, self.size[0], 0, self.size[0]))
        cy  = int(Misc.map(cy,  0, self.size[1], 0, self.size[1]))
        r   = int(Misc.map(rad, 0, self.size[0], 0, self.size[0]))

        if r > 300:
            self.t = Target(-1, -1, 0, "None")
            return

        self.t = Target(cx, cy, r, best_color)

    def _head_loop(self) -> None:
        """Continuously update servo positions to track the target (head/gimbal thread)."""
        while True:
            if not self.running:
                time.sleep(0.02)
                continue

            img = self.cam.frame if self.cam else None
            if img is not None:
                self._vision(img)

            now  = time.time()
            seen = (self.t.cx != -1)

            # Lock/unlock logic — requires LOCK_FRAMES consecutive hits to engage
            if seen:
                self._lock_ok = min(LOCK_FRAMES, self._lock_ok + 1)
                self.last_seen = now
                if self._lock_ok >= LOCK_FRAMES:
                    self.locked = True
            else:
                if self.locked and (now - self.last_seen > UNLOCK_TIMEOUT):
                    self.locked = False
                    self._lock_ok = 0
                    # Reset integrators to avoid carrying bias into the next lock
                    self.iy = 0.0
                    self.ip = 0.0

            if not self.locked:
                # Raster scan
                self.sx += self.scan_dir * PAN_SPEED_PULSE
                if self.sx >= self.pan_max:
                    self.sx = self.pan_max
                    self.scan_dir = -1
                    self.scan_row = clamp(self.scan_row - ROW_STEP_PULSE, self.tilt_min, self.tilt_max)
                    if self.scan_row <= self.tilt_min:
                        self.scan_row = self.tilt_max
                elif self.sx <= self.pan_min:
                    self.sx = self.pan_min
                    self.scan_dir = +1
                    self.scan_row = clamp(self.scan_row - ROW_STEP_PULSE, self.tilt_min, self.tilt_max)
                    if self.scan_row <= self.tilt_min:
                        self.scan_row = self.tilt_max

                self.sy = self.scan_row
                Board.setPWMServoPulse(2, self.sx, 18)
                Board.setPWMServoPulse(1, self.sy, 18)
                time.sleep(SCAN_TICK)
                continue

            # Locked: PI controller to keep target centred
            if now - self.last_head_t >= HEAD_DT:
                dt = max(1e-3, now - self.last_head_t)
                self.last_head_t = now

                w, h   = self.size
                cx, cy = self.t.cx, self.t.cy

                if abs(cx - w / 2.0) < CENTER_DB_PX:
                    cx = int(w / 2.0)
                if abs(cy - h / 2.0) < CENTER_DB_PX:
                    cy = int(h / 2.0)

                ex = (w / 2.0) - cx  # +ex → target left of centre → pan left
                ey = (h / 2.0) - cy  # +ey → target above centre → tilt up

                self.iy = clamp(self.iy + ex * KI_YAW_PULSE_PER_PX_S   * dt, -I_CLAMP, I_CLAMP)
                self.ip = clamp(self.ip + ey * KI_PITCH_PULSE_PER_PX_S * dt, -I_CLAMP, I_CLAMP)

                dx_pulse = int(YAW_SIGN   * (KP_YAW_PULSE_PER_PX   * ex) + self.iy)
                dy_pulse = int(PITCH_SIGN * (KP_PITCH_PULSE_PER_PX * ey) + self.ip)

                self.sx = clamp(self.sx + dx_pulse, *SERVO_X_LIMITS)
                self.sy = clamp(self.sy + dy_pulse, *SERVO_Y_LIMITS)

                Board.setPWMServoPulse(2, self.sx, 16)
                Board.setPWMServoPulse(1, self.sy, 16)

            time.sleep(0.003)

    def _wheel_loop(self) -> None:
        """Drive chassis toward the target based on radius (distance) and pan error."""
        while True:
            if not self.running or not self.locked or self.t.cx == -1:
                self._car_stop()
                time.sleep(0.03)
                continue

            car_y_pid.SetPoint = TARGET_RADIUS
            car_y_pid.update(self.t.r)
            dy = car_y_pid.output
            dy = 0 if abs(dy) < DY_DEADBAND else dy

            ex_pulse = self.sx - self.cx0
            car_x_pid.SetPoint = 0
            car_x_pid.update(ex_pulse)
            dx = car_x_pid.output
            dx = 0 if abs(dx) < DX_DEADBAND else dx

            dx = int(clamp(dx, -MAX_SPEED, MAX_SPEED))
            dy = int(clamp(dy, -MAX_SPEED, MAX_SPEED))
            car.translation(dx, dy)
            time.sleep(0.02)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== LUNA Voice + Ball Tracking ===")
    print("Say after wake word:")
    print("  ID 128 → track RED")
    print("  ID 129 → track GREEN")
    print("  ID 130 → track BLUE")
    print("  ID 9   → stop")

    tracker = Tracker()
    cam = Camera.Camera()
    cam.camera_open(correction=True)

    def on_sigint(signum, frame):
        print("\n[EXIT] Stopping...")
        tracker.stop()
        cam.camera_close()
        Board.setPWMServoPulse(1, tracker.cy0, 600)
        Board.setPWMServoPulse(2, tracker.cx0, 600)
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)

    last_id = 0
    with SMBus(1) as bus:
        while True:
            vid = read_asr_id(bus)
            if vid == 0 or vid == last_id:
                time.sleep(0.02)
                continue
            last_id = vid

            if vid == ID_TRACK_RED:
                tracker.start(cam, colors=("red",))
            elif vid == ID_TRACK_GREEN:
                tracker.start(cam, colors=("green",))
            elif vid == ID_TRACK_BLUE:
                tracker.start(cam, colors=("blue",))
            elif vid == ID_STOP:
                tracker.stop()


if __name__ == "__main__":
    main()
