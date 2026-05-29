#!/usr/bin/env python3
"""
LUNA — Flask Robot Control Server

Exposes HTTP endpoints used by the companion Tkinter control app.
Handles chassis movement, camera access, gimbal control, LAB colour
detection, and threaded ball-tracking with an optional vehicle follower.

Design notes:
  - All chassis movement goes through _linear() or _turn() so timing and
    direction offset are applied consistently.
  - Command frequency is limited inside Tracker and VehicleFollower to
    reduce servo bus chatter and prevent oscillations.
  - The Tracker thread drives the gimbal; VehicleFollower drives the chassis.
  - /track/status is intended for frequent UI polling (~2 Hz is fine).

Endpoints (selected):
  GET /health                          readiness probe
  GET /stop                            stop all motion and tracking
  GET /move_forward?speed&ms           linear forward
  GET /move_backward?speed&ms          linear backward
  GET /strafe_left?speed&ms            lateral left (mecanum)
  GET /strafe_right?speed&ms           lateral right (mecanum)
  GET /turn_left?yaw&ms                in-place left turn
  GET /turn_right?yaw&ms               in-place right turn
  GET /config/angle?forward=deg        adjust forward direction offset
  GET /camera/open?correction=0|1      (re)open camera
  GET /frame.jpg                       current frame as JPEG
  GET /gimbal/center                   center gimbal
  GET /gimbal/angle?yaw&pitch          set absolute gimbal angles
  GET /gimbal/step?dx&dy&big           relative gimbal step
  GET /track/start                     start tracker (+ optional follower)
  GET /track/stop                      stop tracker and follower
  GET /track/status                    JSON status for UI polling

Dependencies (pip): flask, opencv-python, numpy
SDK (on-device): HiwonderSDK, Camera, yaml_handle — installed with TurboPi.
"""

from __future__ import annotations

import atexit
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from flask import Flask, make_response, request, jsonify


# ---------------------------------------------------------------------------
# SDK path
# ---------------------------------------------------------------------------

SDK_PATH = Path(os.getenv("LUNA_TURBOPI_SDK", "/home/pi/TurboPi"))
sys.path.insert(0, str(SDK_PATH))

import HiwonderSDK.mecanum as mecanum
import HiwonderSDK.Misc as Misc
import yaml_handle
import Camera

try:
    import HiwonderSDK.Board as Board
    HAVE_BOARD = True
except Exception:
    # Board PWM may be absent in non-robot environments; use a no-op stub.
    class _Stub:
        def setPWMServoPulse(self, *a, **k): pass
        def setBuzzer(self, *a, **k): pass
    Board = _Stub()
    HAVE_BOARD = False


# ---------------------------------------------------------------------------
# Flask app and chassis
# ---------------------------------------------------------------------------

app = Flask(__name__)

chassis = mecanum.MecanumChassis()
_forward_offset_deg: int = 0


# ---------------------------------------------------------------------------
# Motion helpers
# ---------------------------------------------------------------------------

def _clamp(v, lo, hi):
    """Clamp v to [lo, hi]; return lo if v cannot be converted to float."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def _timed(do_fn, ms: int) -> None:
    """
    Run do_fn immediately; if ms > 0, stop the chassis after ms milliseconds.
    Used for short nudge-style movements that auto-stop after a fixed duration.
    """
    if ms is None or ms <= 0:
        do_fn()
        return

    def _worker():
        try:
            do_fn()
            time.sleep(ms / 1000.0)
        finally:
            try:
                chassis.set_velocity(0, 90, 0)
            except Exception:
                pass

    threading.Thread(target=_worker, daemon=True).start()


def _linear(deg: float, speed: float, ms: int) -> None:
    """
    Drive the chassis linearly at speed [0..100] toward absolute angle deg.
    Applies the forward direction offset before sending to the SDK.
    """
    angle = (float(deg) + _forward_offset_deg) % 360.0
    s = _clamp(speed, 0, 100)
    _timed(lambda: chassis.set_velocity(s, angle, 0), ms)


def _turn(yawrate: float, ms: int) -> None:
    """Turn in place at yawrate [-2..+2] (SDK convention) for ms milliseconds."""
    y = _clamp(yawrate, -2, 2)
    _timed(lambda: chassis.set_velocity(0, 90, y), ms)


# ---------------------------------------------------------------------------
# Routes: movement
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    """Readiness probe — returns ok=True if server is responsive."""
    return jsonify(ok=True)


@app.route("/stop")
def stop():
    """Stop follower/tracker, stop chassis, center gimbal (best effort)."""
    tracker_stop()
    try:
        chassis.set_velocity(0, 90, 0)
    except Exception:
        pass
    return jsonify(ok=True)


@app.route("/move_forward")
def fwd():
    """Move forward. Query args: speed [0..100], ms (duration)."""
    _linear(90, float(request.args.get("speed", "50")), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/move_backward")
def back():
    """Move backward. Query args: speed [0..100], ms (duration)."""
    _linear(270, float(request.args.get("speed", "50")), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/strafe_left")
def sl():
    """Strafe left (mecanum). Query args: speed [0..100], ms (duration)."""
    _linear(180, float(request.args.get("speed", "50")), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/strafe_right")
def sr():
    """Strafe right (mecanum). Query args: speed [0..100], ms (duration)."""
    _linear(0, float(request.args.get("speed", "50")), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/turn_left")
def tl():
    """Turn left in place. Query args: yaw (±2 range), ms (duration)."""
    _turn(-abs(float(request.args.get("yaw", "0.3"))), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/turn_right")
def tr():
    """Turn right in place. Query args: yaw (±2 range), ms (duration)."""
    _turn(+abs(float(request.args.get("yaw", "0.3"))), int(request.args.get("ms", "600")))
    return jsonify(ok=True)


@app.route("/config/angle")
def cfg_angle():
    """
    Set the forward calibration offset in degrees (0..359).
    Example: /config/angle?forward=180 reverses the forward direction.
    Useful when the SDK angle reference doesn't match the physical chassis orientation.
    """
    global _forward_offset_deg
    try:
        _forward_offset_deg = int(request.args.get("forward", "0")) % 360
        return jsonify(ok=True, forward=_forward_offset_deg)
    except (TypeError, ValueError):
        return jsonify(ok=False, msg="forward must be an integer"), 400


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class Cam:
    """Lightweight wrapper around the Hiwonder Camera module."""

    def __init__(self, w: int = 640, h: int = 480, correction: bool = False) -> None:
        self.cam = Camera.Camera(resolution=(w, h))
        self.cam.camera_open(correction=correction)
        self.correction = correction

    def reopen(self, correction: bool = False) -> None:
        """Re-open with optional lens correction. Some devices need a short delay."""
        try:
            self.cam.camera_close()
        except Exception:
            pass
        time.sleep(0.1)
        self.cam.camera_open(correction=bool(correction))
        self.correction = bool(correction)

    def get(self) -> Optional[np.ndarray]:
        """Return a copy of the most recent BGR frame, or None if unavailable."""
        f = self.cam.frame
        return None if f is None else f.copy()


camera = Cam(640, 480, False)


@app.route("/frame.jpg")
def frame_jpg():
    """
    Return the current camera frame as JPEG (80% quality).
    If the tracker is active with overlay enabled, detection markers are drawn.
    """
    f = camera.get()
    if f is None:
        f = np.zeros((480, 640, 3), np.uint8)
    if _tracker is not None and _tracker.overlay:
        _tracker.draw_overlay(f)
    ok, buf = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    resp = make_response(buf.tobytes())
    resp.headers["Content-Type"] = "image/jpeg"
    return resp


@app.route("/camera/open")
def camera_open():
    """(Re)open camera. Query arg: correction=0|1."""
    corr = request.args.get("correction", "0") in ("1", "true", "True")
    camera.reopen(correction=corr)
    return jsonify(ok=True, correction=corr)


# ---------------------------------------------------------------------------
# Gimbal
# ---------------------------------------------------------------------------

class Gimbal:
    """
    Two-axis servo gimbal with rate limiting and soft angle clamping.
    Angles are expressed in degrees [0..180].
    """

    def __init__(self) -> None:
        self.yaw_ch = 2
        self.pitch_ch = 1
        self.inv_yaw = 0
        self.inv_pitch = 0

        try:
            sv = yaml_handle.get_yaml_data(yaml_handle.servo_file_path) or {}
            self.yaw_ch = int(sv.get("yaw_ch", self.yaw_ch))
            self.pitch_ch = int(sv.get("pitch_ch", self.pitch_ch))
            self.inv_yaw = int(sv.get("inv_yaw", self.inv_yaw))
            self.inv_pitch = int(sv.get("inv_pitch", self.inv_pitch))
        except Exception:
            pass

        self.yaw = 90.0
        self.pitch = 90.0
        self.pitch_min = 55
        self.pitch_max = 125

        self._last_cmd_time = 0.0
        self._min_cmd_interval = 0.07  # 70 ms minimum between PWM commands

        self._apply(90, 90, 300)

    @staticmethod
    def _pulse(deg: float) -> int:
        """Map degrees [0..180] to servo pulse width [500..2500] μs."""
        d = max(0.0, min(180.0, float(deg)))
        return int(500 + d / 180.0 * 2000)

    def _apply(self, yaw: float, pitch: float, ms: int = 90) -> None:
        """Apply (yaw, pitch) with soft clamping and command-rate limiting."""
        now = time.time()
        if now - self._last_cmd_time < self._min_cmd_interval:
            return
        self._last_cmd_time = now

        self.yaw = max(10.0, min(170.0, float(yaw)))
        self.pitch = max(float(self.pitch_min), min(float(self.pitch_max), float(pitch)))

        if HAVE_BOARD:
            Board.setPWMServoPulse(self.yaw_ch, self._pulse(self.yaw), ms)
            Board.setPWMServoPulse(self.pitch_ch, self._pulse(self.pitch), ms)

    def center(self) -> dict:
        """Center both axes to (90°, 90°)."""
        self._apply(90, 90, 200)
        return {"yaw": self.yaw, "pitch": self.pitch}

    def angle(self, yaw=None, pitch=None, ms: int = 80) -> dict:
        """Set absolute yaw/pitch if provided; keep previous value otherwise."""
        if yaw is not None:
            self.yaw = float(yaw)
        if pitch is not None:
            self.pitch = float(pitch)
        self._apply(self.yaw, self.pitch, ms)
        return {"yaw": self.yaw, "pitch": self.pitch}

    def step_deg(self, dyaw: float = 0.0, dpitch: float = 0.0, ms: int = 60) -> dict:
        """Relative step in degrees; signs honour optional inversion flags from YAML."""
        dy = -dyaw if self.inv_yaw else dyaw
        dp = -dpitch if self.inv_pitch else dpitch
        return self.angle(self.yaw + dy, self.pitch + dp, ms)


gimbal = Gimbal()


@app.route("/gimbal/center")
def g_center():
    """Center gimbal; returns resulting angles."""
    return jsonify(ok=True, **gimbal.center())


@app.route("/gimbal/angle")
def g_angle():
    """Set absolute yaw/pitch (degrees). Query: yaw=.., pitch=.."""
    y = request.args.get("yaw")
    p = request.args.get("pitch")
    return jsonify(
        ok=True,
        **gimbal.angle(
            None if y is None else float(y),
            None if p is None else float(p),
        ),
    )


@app.route("/gimbal/step")
def g_step():
    """
    Relative step. Query: dx, dy (unitless), big=0|1.
    Each unit maps to ~2°; big=1 maps to ~8° per unit.
    """
    dx = float(request.args.get("dx", "0"))
    dy = float(request.args.get("dy", "0"))
    big = request.args.get("big", "0") in ("1", "true", "True")
    step = 8.0 if big else 2.0
    return jsonify(ok=True, **gimbal.step_deg(step * dx, step * dy, 60))


# ---------------------------------------------------------------------------
# Colour detection (LAB)
# ---------------------------------------------------------------------------

lab = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)


def _detect_one(lab_img, cname: str) -> Tuple[Optional[Tuple], float]:
    """
    Detect the largest blob for a single colour using LAB thresholds from YAML.
    Returns ((cx, cy, r), area) or (None, 0) if nothing is found.
    """
    if cname not in lab:
        return None, 0
    lo = tuple(lab[cname]["min"])
    hi = tuple(lab[cname]["max"])
    mask = cv2.inRange(lab_img, lo, hi)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]
    best = None
    area = 0
    for c in contours:
        a = abs(cv2.contourArea(c))
        if a > area and a > 300:
            area = a
            best = c
    if best is None:
        return None, 0
    (cx, cy), r = cv2.minEnclosingCircle(best)
    return (int(cx), int(cy), int(r)), area


def detect_ball(
    frame_bgr: np.ndarray, color: str
) -> Optional[Tuple[int, int, int]]:
    """
    Return detected (X, Y, R) in frame pixel coordinates, or None.
    Selects the best of red/green/blue if color='auto'.
    """
    size = (640, 480)
    fr = cv2.resize(frame_bgr, size, interpolation=cv2.INTER_NEAREST)
    gb = cv2.GaussianBlur(fr, (3, 3), 3)
    lab_img = cv2.cvtColor(gb, cv2.COLOR_BGR2LAB)

    if color in ("red", "green", "blue"):
        ball, _ = _detect_one(lab_img, color)
    else:
        best = None
        best_area = 0
        for c in ("red", "green", "blue"):
            t, a = _detect_one(lab_img, c)
            if t and a > best_area:
                best_area = a
                best = t
        ball = best

    if not ball:
        return None

    cx, cy, r = ball
    h, w = frame_bgr.shape[:2]
    R = int(Misc.map(r, 0, size[0], 0, w))
    X = int(Misc.map(cx, 0, size[0], 0, w))
    Y = int(Misc.map(cy, 0, size[1], 0, h))
    return X, Y, R


# ---------------------------------------------------------------------------
# Tracker thread
# ---------------------------------------------------------------------------

class Tracker(threading.Thread):
    """
    Image-based target tracker that drives the gimbal.

    Features:
    - Deadbands and centre-lock to reduce jitter near centre.
    - Step-based circular scan when the target is missing.
    - Command-rate limiting to reduce servo bus chatter.
    - Adaptive pitch gains based on apparent ball radius (near vs far).
    - Publishes shared state dict consumed by VehicleFollower.
    """

    def __init__(
        self,
        color: str = "red",
        use_pitch=True,
        overlay: bool = True,
        vehicle_mode: bool = False,
        lost_timeout: float = 1.0,
        scan_center_yaw: float = 90.0,
        scan_center_pitch: float = 90.0,
        scan_radius_yaw: float = 25.0,
        scan_radius_pitch: float = 12.0,
        scan_omega_dps: float = 36.0,
        scan_step_deg: float = 3.0,
    ) -> None:
        super().__init__(daemon=True)
        self.color = color
        self.use_pitch = bool(int(use_pitch)) if isinstance(use_pitch, str) else bool(use_pitch)
        self.overlay = overlay
        self.vehicle_mode = bool(vehicle_mode)
        self.running = False

        # Tracking gains
        self.alpha = 0.6
        self.alpha_ey = 0.6
        self.dead_x_base = 0.10
        self.kp_yaw_deg = 10.0
        self.kd_yaw_deg = 3.0
        self.max_step_yaw = 2.0
        self.min_move_deg = 1.2
        self.center_lock_ms = 350

        # Near/far adaptive pitch gains
        self.dead_y_lo_far = 0.05; self.dead_y_hi_far = 0.10
        self.kp_pit_far = 6.0;     self.kd_pit_far = 2.0;    self.max_step_far = 1.5
        self.dead_y_lo_near = 0.08; self.dead_y_hi_near = 0.16
        self.kp_pit_near = 4.0;    self.kd_pit_near = 2.5;   self.max_step_near = 0.8
        self.r_far = 40;           self.r_near = 140

        # Scan parameters
        self.scan_cy = float(scan_center_yaw)
        self.scan_cp = float(scan_center_pitch)
        self.Ry = float(scan_radius_yaw)
        self.Rp = float(scan_radius_pitch)
        self.scan_step = float(scan_step_deg)
        self.theta = 0.0
        self.last_scan_cmd_time = 0.0
        self.scan_cmd_interval = 0.12

        self.lost_timeout = float(lost_timeout)
        self.last_seen_t = 0.0
        self.was_scanning = False

        self.last_track_cmd_time = 0.0
        self.track_cmd_interval = 0.08

        # Internal state
        self.cx_e = self.cy_e = self.r_e = None
        self.ey_f = None
        self._ey_prev = 0.0
        self._lock_until = 0.0
        self._found = False
        self._cx = self._cy = self._r = 0
        self.yaw_center_deg = 90.0
        self.yaw_center_band = 3.5

        # Published state for VehicleFollower
        self.shared: dict = {
            "t": 0.0, "found": False, "ex": 0.0, "ey": 0.0,
            "r": 0.0, "yaw": 90.0, "pitch": 90.0, "scan": False, "just_found": False,
        }

    def stop(self) -> None:
        self.running = False

    @staticmethod
    def _lerp(a, b, t):
        return a + (b - a) * max(0.0, min(1.0, t))

    def _circle_scan_step(self, now: float) -> None:
        """Advance one step of the circular scan pattern."""
        if now - self.last_scan_cmd_time < self.scan_cmd_interval:
            return
        self.last_scan_cmd_time = now
        self.theta = (self.theta + math.radians(self.scan_step)) % (2 * math.pi)
        y = max(10.0, min(170.0, self.scan_cy + self.Ry * math.sin(self.theta)))
        p = max(gimbal.pitch_min, min(gimbal.pitch_max, self.scan_cp + self.Rp * math.cos(self.theta)))
        gimbal.angle(yaw=y, pitch=p, ms=90)

    def draw_overlay(self, f: np.ndarray) -> None:
        """Draw a crosshair and detection circle on the frame."""
        if not self.overlay:
            return
        h, w = f.shape[:2]
        cv2.drawMarker(f, (w // 2, h // 2), (255, 255, 255), cv2.MARKER_CROSS, 14, 1)
        if self._found:
            cv2.circle(f, (int(self._cx), int(self._cy)), int(self._r), (0, 255, 0), 2)
        mode = "TRACK" if self._found else "SCAN"
        cv2.putText(f, f"mode={mode} veh={int(self.vehicle_mode)}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def run(self) -> None:
        self.running = True
        gimbal.angle(yaw=self.scan_cy, pitch=self.scan_cp, ms=200)
        time.sleep(0.3)
        self.last_seen_t = 0.0
        self.was_scanning = False

        while self.running:
            f = camera.get()
            now = time.time()
            if f is None:
                time.sleep(0.03)
                continue

            det = detect_ball(f, self.color)

            if not det:
                scan_active = (self.last_seen_t <= 0) or (now - self.last_seen_t >= self.lost_timeout)
                if scan_active:
                    self._found = False
                    self.was_scanning = True
                    self._circle_scan_step(now)
                self.shared.update({
                    "t": now, "found": False, "ex": 0.0, "ey": 0.0, "r": 0.0,
                    "yaw": gimbal.yaw, "pitch": gimbal.pitch, "scan": scan_active, "just_found": False,
                })
                time.sleep(0.03)
                continue

            just_found = self.was_scanning
            self.was_scanning = False
            self.last_seen_t = now
            self._found = True

            cx, cy, r = det
            h, w = f.shape[:2]
            self.cx_e = cx if self.cx_e is None else self.alpha * cx + (1 - self.alpha) * self.cx_e
            self.cy_e = cy if self.cy_e is None else self.alpha * cy + (1 - self.alpha) * self.cy_e
            self.r_e = r if self.r_e is None else self.alpha * r + (1 - self.alpha) * self.r_e
            self._cx, self._cy, self._r = int(self.cx_e), int(self.cy_e), int(self.r_e)

            ex = (self.cx_e - w / 2) / (w / 2)
            ey = (self.cy_e - h / 2) / (h / 2)
            if abs(ex) < self.dead_x_base:
                ex = 0.0

            if now - self.last_track_cmd_time >= self.track_cmd_interval:
                self.last_track_cmd_time = now

                t_blend = max(0.0, min(1.0, (self.r_e - self.r_far) / max(1.0, self.r_near - self.r_far)))
                dead_y_lo = self._lerp(self.dead_y_lo_far, self.dead_y_lo_near, t_blend)
                dead_y_hi = self._lerp(self.dead_y_hi_far, self.dead_y_hi_near, t_blend)
                kp_pit = self._lerp(self.kp_pit_far, self.kp_pit_near, t_blend)
                kd_pit = self._lerp(self.kd_pit_far, self.kd_pit_near, t_blend)
                max_step = self._lerp(self.max_step_far, self.max_step_near, t_blend)

                allow_yaw = (not self.vehicle_mode) or (abs(gimbal.yaw - self.yaw_center_deg) > self.yaw_center_band)
                if allow_yaw and abs(ex) > 0.01:
                    dyaw = float(np.clip(self.kp_yaw_deg * ex, -self.max_step_yaw, self.max_step_yaw))
                    if abs(dyaw) < self.min_move_deg:
                        dyaw = 0.0
                else:
                    dyaw = 0.0

                dpit = 0.0
                if self.use_pitch:
                    self.ey_f = ey if self.ey_f is None else (self.alpha_ey * ey + (1 - self.alpha_ey) * self.ey_f)
                    in_lock = now < self._lock_until
                    if abs(self.ey_f) <= dead_y_lo:
                        self._lock_until = now + self.center_lock_ms / 1000.0
                        e = 0.0
                    elif in_lock and abs(self.ey_f) < dead_y_hi:
                        e = 0.0
                    elif abs(self.ey_f) >= dead_y_hi:
                        self._lock_until = 0.0
                        e = self.ey_f
                    else:
                        e = 0.0

                    if e != 0.0:
                        dey = e - getattr(self, "_ey_prev", 0.0)
                        dpit = float(np.clip(kp_pit * e + kd_pit * dey, -max_step, max_step))
                        self._ey_prev = e
                    else:
                        dpit = 0.0
                        self._ey_prev = 0.0

                    if abs(dpit) < self.min_move_deg:
                        dpit = 0.0
                    if dpit > 0 and gimbal.pitch >= (gimbal.pitch_max - 3):
                        dpit = 0.0
                    if dpit < 0 and gimbal.pitch <= (gimbal.pitch_min + 3):
                        dpit = 0.0

                if abs(dyaw) > 0.01 or abs(dpit) > 0.01:
                    gimbal.step_deg(dyaw, dpit, ms=80)

            self.shared.update({
                "t": now, "found": True, "ex": ex, "ey": ey, "r": self._r,
                "yaw": gimbal.yaw, "pitch": gimbal.pitch, "scan": False, "just_found": just_found,
            })
            time.sleep(0.03)


# ---------------------------------------------------------------------------
# Vehicle follower thread
# ---------------------------------------------------------------------------

class VehicleFollower(threading.Thread):
    """
    Consumes Tracker.shared state and drives the mecanum chassis.

    Modes:
    - 'strafe': lateral correction via x velocity; no yaw.
    - 'turn': yaw correction via angular velocity; no lateral x.

    Forward/backward velocity is governed by a PD controller on apparent radius.
    Includes an alignment phase to centre the gimbal yaw before normal driving.
    """

    def __init__(
        self,
        shared: dict,
        lateral: str = "strafe",
        target_r: float = 100,
        v_max: float = 80,
        v_dead_x: float = 4.0,
        v_dead_y: float = 6.0,
        kx_img: float = 260.0,
        align_timeout: float = 3.0,
        band_stop: float = 8,
        invert_yawpid: bool = False,
    ) -> None:
        super().__init__(daemon=True)
        self.shared = shared
        self.running = True
        self.mode = lateral if lateral in ("turn", "strafe") else "strafe"
        self.target_r = float(target_r)
        self.v_max = float(v_max)
        self.v_dead_x = float(v_dead_x)
        self.v_dead_y = float(v_dead_y)
        self.kx_img = float(kx_img)
        self.align_timeout = float(align_timeout)
        self.band_stop = float(band_stop)
        self.invert_yawpid = bool(invert_yawpid)

        self.need_align = True
        self.align_start = None
        self.align_thresh_deg = 2.0
        self.align_wz = 0.10

        self.r_f = None
        self.r_prev = None
        self.t_prev = None
        self.last_dy = 0.0
        self.dy_rate = 3.5
        self.kp_y = 0.9
        self.kd_y = 0.12
        self.min_speed = 12.0

        self.last_cmd_time = 0.0
        self.cmd_interval = 0.05

    def stop(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            s = dict(self.shared) if self.shared else None
            now = time.time()

            if now - self.last_cmd_time < self.cmd_interval:
                time.sleep(0.01)
                continue

            if (not s) or (now - s.get("t", 0) > 1.0):
                self.need_align = True
                self.align_start = None
                try:
                    chassis.set_velocity(0, 90, 0)
                except Exception:
                    pass
                self.last_cmd_time = now
                time.sleep(0.03)
                continue

            scan_active = bool(s.get("scan", False))
            found = bool(s.get("found", False))
            just_found = bool(s.get("just_found", False))

            if scan_active or not found:
                if scan_active:
                    self.need_align = True
                try:
                    chassis.set_velocity(0, 90, 0)
                except Exception:
                    pass
                self.last_cmd_time = now
                time.sleep(0.03)
                continue

            if just_found:
                self.need_align = True
                self.align_start = None
                time.sleep(0.5)

            ex = (-s["ex"] if self.invert_yawpid else s["ex"])
            r_meas = float(s["r"])

            if self.need_align:
                if self.align_start is None:
                    self.align_start = now
                    time.sleep(0.3)

                err_deg = gimbal.yaw - 90.0
                if abs(err_deg) <= self.align_thresh_deg or (now - self.align_start) >= self.align_timeout:
                    self.need_align = False
                    try:
                        chassis.set_velocity(0, 90, 0)
                    except Exception:
                        pass
                    time.sleep(0.2)
                else:
                    wz = -self.align_wz if err_deg > 0 else self.align_wz
                    chassis.set_velocity(0, 90, wz)
                self.last_cmd_time = now
                time.sleep(0.03)
                continue

            # Lateral
            if self.mode == "strafe":
                dx_img = self.kx_img * ex
                dx = 0.0 if abs(dx_img) < self.v_dead_x else float(np.clip(dx_img, -self.v_max, self.v_max))
                wz = 0.0
            else:
                wz = float(np.clip(0.35 * ex, -0.4, 0.4))
                dx = 0.0

            # Forward/backward
            if self.r_f is None:
                self.r_f = r_meas
            else:
                self.r_f = 0.7 * r_meas + 0.3 * self.r_f

            err_y = self.target_r - self.r_f
            dr_dt = 0.0
            if self.r_prev is not None and self.t_prev is not None:
                dt = max(1e-3, now - self.t_prev)
                dr_dt = (self.r_f - self.r_prev) / dt
            self.r_prev = self.r_f
            self.t_prev = now

            dy_cmd = float(np.clip(self.kp_y * err_y - self.kd_y * dr_dt, -self.v_max, self.v_max))
            dy = float(np.clip(dy_cmd, self.last_dy - self.dy_rate, self.last_dy + self.dy_rate))
            self.last_dy = dy

            if abs(err_y) <= self.band_stop:
                dy = 0.0
            elif 0 < abs(dy) < self.min_speed:
                dy = self.min_speed if dy > 0 else -self.min_speed

            speed = float(min(100.0, math.hypot(dx, dy)))
            if speed < 1e-3 and abs(wz) > 0:
                chassis.set_velocity(0, 90, wz)
            elif speed >= 1e-3:
                ang = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
                chassis.set_velocity(speed, ang, wz)
            else:
                chassis.set_velocity(0, 90, 0)

            self.last_cmd_time = now
            time.sleep(0.03)


# ---------------------------------------------------------------------------
# Routes: tracker
# ---------------------------------------------------------------------------

_tracker: Optional[Tracker] = None
_follower: Optional[VehicleFollower] = None


def tracker_stop() -> None:
    """Stop and join tracker/follower threads; stop chassis and center gimbal."""
    global _tracker, _follower
    th1, th2 = _tracker, _follower
    _tracker = None
    _follower = None
    if th2:
        try:
            th2.stop()
            th2.join(timeout=1.0)
        except Exception:
            pass
    if th1:
        try:
            th1.stop()
            th1.join(timeout=1.0)
        except Exception:
            pass
    try:
        chassis.set_velocity(0, 90, 0)
    except Exception:
        pass
    try:
        gimbal.center()
    except Exception:
        pass


@app.route("/track/start")
def track_start():
    """
    Start the tracker thread (and optionally the vehicle follower).
    See module docstring for full list of query parameters.
    """
    global _tracker, _follower
    tracker_stop()

    color = request.args.get("color", "red").lower()
    overlay = request.args.get("overlay", "1") in ("1", "true", "True")
    use_pitch = request.args.get("use_pitch", "1")
    lost_timeout = float(request.args.get("lost_timeout", "1.0"))
    scan_cy = float(request.args.get("scan_center_yaw", "90"))
    scan_cp = float(request.args.get("scan_center_pitch", "90"))
    scan_Ry = float(request.args.get("scan_radius_yaw", "25"))
    scan_Rp = float(request.args.get("scan_radius_pitch", "12"))
    scan_omega_dps = float(request.args.get("scan_omega_dps", "36"))
    scan_step = float(request.args.get("scan_step_deg", "5"))
    vehicle_pid = request.args.get("vehicle_pid", "0") in ("1", "true", "True")
    lateral = request.args.get("lateral", "strafe")
    target_r = float(request.args.get("target_r", "100"))
    v_max = float(request.args.get("v_max", "80"))
    v_dead_x = float(request.args.get("v_dead_x", "4"))
    v_dead_y = float(request.args.get("v_dead_y", "6"))
    kx_img = float(request.args.get("kx_img", "260"))
    invert_yawpid = request.args.get("invert_yawpid", "0") in ("1", "true", "True")

    _tracker = Tracker(
        color=color, use_pitch=use_pitch, overlay=overlay,
        vehicle_mode=vehicle_pid, lost_timeout=lost_timeout,
        scan_center_yaw=scan_cy, scan_center_pitch=scan_cp,
        scan_radius_yaw=scan_Ry, scan_radius_pitch=scan_Rp,
        scan_omega_dps=scan_omega_dps, scan_step_deg=scan_step,
    )
    _tracker.start()

    if vehicle_pid:
        _follower = VehicleFollower(
            _tracker.shared, lateral=lateral, target_r=target_r, v_max=v_max,
            v_dead_x=v_dead_x, v_dead_y=v_dead_y, kx_img=kx_img,
            invert_yawpid=invert_yawpid, align_timeout=3.0,
        )
        _follower.start()

    return jsonify(
        ok=True, color=color, overlay=int(overlay),
        vehicle_pid=int(vehicle_pid), lateral=lateral, lost_timeout=lost_timeout,
    )


@app.route("/track/stop")
def track_stop_route():
    """Stop tracker and follower threads."""
    tracker_stop()
    return jsonify(ok=True)


@app.route("/track/status")
def track_status():
    """Return a compact JSON snapshot suitable for frequent UI polling."""
    s = dict(_tracker.shared) if _tracker else {
        "t": 0, "found": False, "ex": 0, "ey": 0, "r": 0,
        "yaw": 90, "pitch": 90, "scan": False,
    }
    return jsonify(
        ok=True,
        running=(_tracker is not None),
        veh=(_follower is not None),
        aligning=bool(getattr(_follower, "need_align", False)) if _follower else False,
        found=s["found"], ex=s["ex"], ey=s["ey"], r=s["r"],
        yaw=s["yaw"], pitch=s["pitch"], scan_active=s["scan"],
    )


# ---------------------------------------------------------------------------
# Exit cleanup
# ---------------------------------------------------------------------------

@atexit.register
def _cleanup() -> None:
    """Best-effort stop and reset when the server process exits."""
    try:
        tracker_stop()
    except Exception:
        pass
    try:
        chassis.set_velocity(0, 90, 0)
    except Exception:
        pass


if __name__ == "__main__":
    # Threaded mode so long-polling and image fetches don't block control endpoints.
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
