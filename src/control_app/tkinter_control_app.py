#!/usr/bin/env python3
"""
LUNA — Tkinter Desktop Control App

Desktop control interface for the LUNA robot Flask server.
Connects to the robot over Wi-Fi and provides:

  - Manual chassis movement (arrow keys, strafe with Z/C)
  - Live camera preview (JPEG stream from /frame.jpg)
  - Ball-tracking start/stop with configurable colour and parameters
  - Gimbal control (keyboard steps and sliders)
  - Live status polling from /track/status

Set the robot's IP address in the "Base URL" field at the top of the app.
The default value can be changed by setting the LUNA_ROBOT_URL environment
variable before launching.

Hotkeys:
  Arrow Up / Down / Left / Right  →  Forward / Backward / Turn Left / Turn Right
  Z / C                           →  Strafe Left / Strafe Right
  Space                           →  STOP
  t / T                           →  Start / Stop tracking
  j / l / i / k                  →  Gimbal step (hold Shift for larger step)
  o                               →  Gimbal centre

Dependencies (pip): requests, Pillow
"""

import io
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests
from PIL import Image, ImageTk


# ---------------------------------------------------------------------------
# Endpoint names (must match flask_robot_server.py routes)
# ---------------------------------------------------------------------------

ENDPOINTS = {
    "forward":      "move_forward",
    "backward":     "move_backward",
    "left":         "turn_left",
    "right":        "turn_right",
    "strafe_l":     "strafe_left",
    "strafe_r":     "strafe_right",
    "stop":         "stop",
    "health":       "health",
    "frame":        "frame.jpg",
    "track_start":  "track/start",
    "track_stop":   "track/stop",
    "track_status": "track/status",
    "cfg_angle":    "config/angle",
    "gimbal_angle": "gimbal/angle",
    "gimbal_step":  "gimbal/step",
    "gimbal_center":"gimbal/center",
    "cam_open":     "camera/open",
}

DEFAULT_ROBOT_URL = os.getenv("LUNA_ROBOT_URL", "http://192.168.1.100:5000")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def b2s(b: bool) -> str:
    """Convert a Python bool to the '1'/'0' string the server expects."""
    return "1" if b else "0"


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class App(ttk.Frame):
    """
    Main Tkinter control panel.

    Builds the UI, wires keyboard bindings, and sends HTTP requests to the
    robot server.
    """

    def __init__(self, master=None) -> None:
        super().__init__(master, padding=10)
        self.master.title("LUNA Controller")
        self.grid(sticky="nsew")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        self.sess = requests.Session()

        # Connection settings
        self.base = tk.StringVar(value=DEFAULT_ROBOT_URL)
        self.timeout = tk.DoubleVar(value=2.0)
        self.no_redirects = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready.")

        # Movement defaults
        self.append_params = tk.BooleanVar(value=True)
        self.def_speed = tk.IntVar(value=45)
        self.def_ms = tk.IntVar(value=600)

        # Tracking parameters
        self.color = tk.StringVar(value="red")
        self.overlay = tk.BooleanVar(value=True)
        self.use_pitch = tk.BooleanVar(value=True)
        self.vehicle_pid = tk.BooleanVar(value=False)
        self.lateral = tk.StringVar(value="strafe")
        self.invert_yawpid = tk.BooleanVar(value=False)

        # Vehicle PID / safe distance
        self.target_r = tk.IntVar(value=100)
        self.v_max = tk.IntVar(value=80)
        self.v_dead_x = tk.IntVar(value=4)
        self.v_dead_y = tk.IntVar(value=6)
        self.kx_img = tk.IntVar(value=260)

        # Scan and lost-timeout parameters
        self.lost_timeout = tk.DoubleVar(value=1.0)
        self.scan_center_yaw = tk.DoubleVar(value=90.0)
        self.scan_center_pitch = tk.DoubleVar(value=100.0)
        self.scan_radius_yaw = tk.DoubleVar(value=30.0)
        self.scan_radius_pitch = tk.DoubleVar(value=15.0)
        self.scan_omega_dps = tk.DoubleVar(value=30.0)

        # Preview state
        self.preview_on = False
        self.preview_job = None
        self.photo = None
        self.status_job = None

        # Gimbal display
        self.yaw = tk.IntVar(value=90)
        self.pitch = tk.IntVar(value=90)

        self.build()
        self.bind_keys()
        self.status_poll_start()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Construct all Tkinter widgets."""
        r = 0

        # ---- Connection row ----
        fr = ttk.Frame(self)
        fr.grid(row=r, column=0, sticky="ew")
        r += 1
        for c in range(8):
            fr.grid_columnconfigure(c, weight=1)
        ttk.Label(fr, text="Base URL").grid(row=0, column=0, sticky="e")
        ttk.Entry(fr, textvariable=self.base, width=30).grid(
            row=0, column=1, columnspan=3, sticky="ew", padx=6
        )
        ttk.Label(fr, text="Timeout").grid(row=0, column=4, sticky="e")
        ttk.Entry(fr, textvariable=self.timeout, width=6).grid(row=0, column=5, sticky="w")
        ttk.Checkbutton(fr, text="No redirects", variable=self.no_redirects).grid(
            row=0, column=6, sticky="w"
        )
        ttk.Button(
            fr, text="Ping",
            command=lambda: self._get(self._url(ENDPOINTS["health"]), "health")
        ).grid(row=0, column=7, sticky="ew")

        # ---- Movement defaults ----
        fr2 = ttk.Frame(self)
        fr2.grid(row=r, column=0, sticky="ew", pady=(6, 0))
        r += 1
        for c in range(7):
            fr2.grid_columnconfigure(c, weight=1)
        ttk.Checkbutton(fr2, text="Append speed/ms", variable=self.append_params).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(fr2, text="speed%").grid(row=0, column=1, sticky="e")
        ttk.Spinbox(fr2, from_=0, to=100, textvariable=self.def_speed, width=6).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Label(fr2, text="ms").grid(row=0, column=3, sticky="e")
        ttk.Spinbox(fr2, from_=0, to=5000, increment=50, textvariable=self.def_ms, width=8).grid(
            row=0, column=4, sticky="w"
        )
        ttk.Button(
            fr2, text="STOP  (Space)", style="Danger.TButton",
            command=lambda: self.send(ENDPOINTS["stop"], "Stop")
        ).grid(row=0, column=5, sticky="ew")

        # ---- Chassis direction pad ----
        fr3 = ttk.Frame(self)
        fr3.grid(row=r, column=0, sticky="ew", pady=(6, 0))
        r += 1
        for c in range(7):
            fr3.grid_columnconfigure(c, weight=1)
        ttk.Button(fr3, text="▲ Forward",
            command=lambda: self.send(ENDPOINTS["forward"], "Forward")
        ).grid(row=0, column=2, pady=4)
        ttk.Button(fr3, text="◀ Turn Left",
            command=lambda: self.send(ENDPOINTS["left"], "Turn Left")
        ).grid(row=1, column=0)
        ttk.Button(fr3, text="Strafe ◄",
            command=lambda: self.send(ENDPOINTS["strafe_l"], "Strafe L")
        ).grid(row=1, column=2)
        ttk.Button(fr3, text="Strafe ►",
            command=lambda: self.send(ENDPOINTS["strafe_r"], "Strafe R")
        ).grid(row=1, column=3)
        ttk.Button(fr3, text="Turn Right ▶",
            command=lambda: self.send(ENDPOINTS["right"], "Turn Right")
        ).grid(row=1, column=5)
        ttk.Button(fr3, text="▼ Backward",
            command=lambda: self.send(ENDPOINTS["backward"], "Backward")
        ).grid(row=2, column=2, pady=4)

        ttk.Separator(self, orient="horizontal").grid(
            row=r, column=0, sticky="ew", pady=(8, 6)
        )
        r += 1

        # ---- Tracking config ----
        fr4 = ttk.Frame(self)
        fr4.grid(row=r, column=0, sticky="ew")
        r += 1
        for c in range(10):
            fr4.grid_columnconfigure(c, weight=1)
        ttk.Label(fr4, text="Color").grid(row=0, column=0, sticky="e")
        ttk.Combobox(
            fr4, textvariable=self.color,
            values=["red", "green", "blue", "auto"], width=7, state="readonly"
        ).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(fr4, text="Overlay", variable=self.overlay).grid(
            row=0, column=2, sticky="w"
        )
        ttk.Checkbutton(fr4, text="Use Pitch", variable=self.use_pitch).grid(
            row=0, column=3, sticky="w"
        )
        ttk.Checkbutton(fr4, text="Vehicle PID", variable=self.vehicle_pid).grid(
            row=0, column=4, sticky="w"
        )
        ttk.Label(fr4, text="Lateral").grid(row=0, column=5, sticky="e")
        ttk.Combobox(
            fr4, textvariable=self.lateral,
            values=["turn", "strafe"], width=7, state="readonly"
        ).grid(row=0, column=6, sticky="w")
        ttk.Checkbutton(fr4, text="Invert L/R", variable=self.invert_yawpid).grid(
            row=0, column=7, sticky="w"
        )
        ttk.Button(fr4, text="Start Preview", command=self.preview_start).grid(
            row=0, column=8, sticky="ew"
        )
        ttk.Button(fr4, text="Stop Preview", command=self.preview_stop).grid(
            row=0, column=9, sticky="ew"
        )

        # ---- Circular scan / lost rescan ----
        fr5 = ttk.LabelFrame(self, text="Circular Scan / Lost Rescan")
        fr5.grid(row=r, column=0, sticky="ew", pady=(6, 0))
        r += 1
        for c in range(8):
            fr5.grid_columnconfigure(c, weight=1)
        ttk.Label(fr5, text="lost_timeout (s)").grid(row=0, column=0, sticky="e")
        ttk.Spinbox(fr5, from_=0.2, to=5.0, increment=0.1, textvariable=self.lost_timeout, width=6).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(fr5, text="Center Yaw").grid(row=0, column=2, sticky="e")
        ttk.Spinbox(fr5, from_=10, to=170, textvariable=self.scan_center_yaw, width=6).grid(
            row=0, column=3, sticky="w"
        )
        ttk.Label(fr5, text="Center Pitch").grid(row=0, column=4, sticky="e")
        ttk.Spinbox(fr5, from_=55, to=125, textvariable=self.scan_center_pitch, width=6).grid(
            row=0, column=5, sticky="w"
        )
        ttk.Label(fr5, text="Radius Yaw").grid(row=1, column=0, sticky="e")
        ttk.Spinbox(fr5, from_=5, to=80, textvariable=self.scan_radius_yaw, width=6).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Label(fr5, text="Radius Pitch").grid(row=1, column=2, sticky="e")
        ttk.Spinbox(fr5, from_=5, to=60, textvariable=self.scan_radius_pitch, width=6).grid(
            row=1, column=3, sticky="w"
        )
        ttk.Label(fr5, text="Scan Speed (°/s)").grid(row=1, column=4, sticky="e")
        ttk.Spinbox(fr5, from_=8, to=90, textvariable=self.scan_omega_dps, width=6).grid(
            row=1, column=5, sticky="w"
        )
        ttk.Label(fr5, text="Tip: lower speed + radius reduces jitter",
                  foreground="gray").grid(row=1, column=6, columnspan=2, sticky="w", padx=8)

        # ---- Vehicle PID / safe distance ----
        fr6 = ttk.LabelFrame(self, text="Vehicle PID / Safe Distance")
        fr6.grid(row=r, column=0, sticky="ew", pady=(6, 0))
        r += 1
        for c in range(10):
            fr6.grid_columnconfigure(c, weight=1)
        for label, var, col in [
            ("Target r",    self.target_r, 0),
            ("Max speed",   self.v_max,    2),
            ("Deadband L/R", self.v_dead_x, 4),
            ("Deadband F/B", self.v_dead_y, 6),
            ("Lateral gain", self.kx_img,  8),
        ]:
            ttk.Label(fr6, text=label).grid(row=0, column=col,   sticky="e")
            ttk.Spinbox(fr6, from_=0, to=800, increment=10, textvariable=var, width=6).grid(
                row=0, column=col + 1, sticky="w"
            )

        # ---- Tracking control buttons ----
        fr7 = ttk.Frame(self)
        fr7.grid(row=r, column=0, sticky="ew", pady=(6, 0))
        r += 1
        for c in range(6):
            fr7.grid_columnconfigure(c, weight=1)
        ttk.Button(fr7, text="Start Tracking (t)", style="Success.TButton",
                   command=self.track_start).grid(row=0, column=0, sticky="ew")
        ttk.Button(fr7, text="Stop Tracking (T)", style="Danger.TButton",
                   command=self.track_stop).grid(row=0, column=1, sticky="ew")
        ttk.Button(fr7, text="Gimbal Centre (o)",
                   command=self.gimbal_center).grid(row=0, column=2, sticky="ew")
        ttk.Button(fr7, text="Open Camera (corr=0)",
                   command=lambda: self._get(
                       self._url(f'{ENDPOINTS["cam_open"]}?correction=0'), "cam open"
                   )).grid(row=0, column=3, sticky="ew")
        ttk.Button(fr7, text="Open Camera (corr=1)",
                   command=lambda: self._get(
                       self._url(f'{ENDPOINTS["cam_open"]}?correction=1'), "cam open"
                   )).grid(row=0, column=4, sticky="ew")
        ttk.Button(fr7, text="Save Photo",
                   command=self.capture_photo).grid(row=0, column=5, sticky="ew")

        # ---- Live preview ----
        self.video = ttk.Label(self, text="(preview off)")
        self.video.grid(row=r, column=0, sticky="nsew", pady=6)
        r += 1

        # ---- Gimbal manual control ----
        fr8 = ttk.LabelFrame(self, text="Gimbal Manual Control")
        fr8.grid(row=r, column=0, sticky="ew")
        r += 1
        for c in range(8):
            fr8.grid_columnconfigure(c, weight=1)
        ttk.Label(fr8, text="Yaw").grid(row=0, column=0, sticky="e")
        ttk.Scale(fr8, from_=0, to=180, variable=self.yaw,
                  command=lambda v: self.gimbal_angle()).grid(
            row=0, column=1, columnspan=3, sticky="ew"
        )
        ttk.Label(fr8, textvariable=self.yaw, width=4).grid(row=0, column=4, sticky="w")
        ttk.Label(fr8, text="Pitch").grid(row=0, column=5, sticky="e")
        ttk.Scale(fr8, from_=0, to=180, variable=self.pitch,
                  command=lambda v: self.gimbal_angle()).grid(
            row=0, column=6, sticky="ew"
        )
        ttk.Label(fr8, textvariable=self.pitch, width=4).grid(row=0, column=7, sticky="w")

        # ---- Status bar ----
        ttk.Label(self, textvariable=self.status, anchor="w", foreground="gray").grid(
            row=r, column=0, sticky="ew", pady=(4, 0)
        )

    # ------------------------------------------------------------------
    # Keyboard bindings
    # ------------------------------------------------------------------

    def bind_keys(self) -> None:
        m = self.master
        m.bind("<Up>",    lambda e: self.send(ENDPOINTS["forward"],  "Forward"))
        m.bind("<Down>",  lambda e: self.send(ENDPOINTS["backward"], "Backward"))
        m.bind("<Left>",  lambda e: self.send(ENDPOINTS["left"],     "Turn Left"))
        m.bind("<Right>", lambda e: self.send(ENDPOINTS["right"],    "Turn Right"))
        m.bind("z",       lambda e: self.send(ENDPOINTS["strafe_l"], "Strafe L"))
        m.bind("Z",       lambda e: self.send(ENDPOINTS["strafe_l"], "Strafe L"))
        m.bind("c",       lambda e: self.send(ENDPOINTS["strafe_r"], "Strafe R"))
        m.bind("C",       lambda e: self.send(ENDPOINTS["strafe_r"], "Strafe R"))
        m.bind("<space>", lambda e: self.send(ENDPOINTS["stop"],     "Stop"))
        m.bind("t",       lambda e: self.track_start())
        m.bind("T",       lambda e: self.track_stop())
        m.bind("o",       lambda e: self.gimbal_center())
        # Gimbal steps
        m.bind("j",  lambda e: self.gimbal_step(dx=-1))
        m.bind("l",  lambda e: self.gimbal_step(dx=+1))
        m.bind("i",  lambda e: self.gimbal_step(dy=-1))
        m.bind("k",  lambda e: self.gimbal_step(dy=+1))
        m.bind("J",  lambda e: self.gimbal_step(dx=-1, big=True))
        m.bind("L",  lambda e: self.gimbal_step(dx=+1, big=True))
        m.bind("I",  lambda e: self.gimbal_step(dy=-1, big=True))
        m.bind("K",  lambda e: self.gimbal_step(dy=+1, big=True))

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _url(self, endpoint: str) -> str:
        base = self.base.get().rstrip("/")
        return f"{base}/{endpoint}"

    def _get(self, url: str, label: str) -> None:
        """Send a GET request in a background thread; update the status bar."""
        def _worker():
            try:
                r = self.sess.get(
                    url,
                    timeout=self.timeout.get(),
                    allow_redirects=not self.no_redirects.get(),
                )
                self.status.set(f"{label}: {r.status_code}")
            except requests.exceptions.RequestException as e:
                self.status.set(f"{label}: error — {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def send(self, endpoint: str, label: str) -> None:
        """Build the movement URL (optionally appending speed/ms) and send it."""
        url = self._url(endpoint)
        if self.append_params.get():
            url += f"?speed={self.def_speed.get()}&ms={self.def_ms.get()}"
        self._get(url, label)

    # ------------------------------------------------------------------
    # Camera preview
    # ------------------------------------------------------------------

    def preview_start(self) -> None:
        self.preview_on = True
        self._poll_frame()

    def preview_stop(self) -> None:
        self.preview_on = False
        if self.preview_job:
            self.after_cancel(self.preview_job)
            self.preview_job = None
        self.video.configure(image="", text="(preview off)")

    def _poll_frame(self) -> None:
        if not self.preview_on:
            return

        def _fetch():
            try:
                resp = self.sess.get(
                    self._url(ENDPOINTS["frame"]),
                    timeout=self.timeout.get(),
                    stream=True,
                )
                img = Image.open(io.BytesIO(resp.content))
                photo = ImageTk.PhotoImage(img)
                self.photo = photo
                self.video.configure(image=photo, text="")
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()
        self.preview_job = self.after(120, self._poll_frame)

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track_start(self) -> None:
        params = (
            f"color={self.color.get()}"
            f"&overlay={b2s(self.overlay.get())}"
            f"&use_pitch={b2s(self.use_pitch.get())}"
            f"&vehicle_pid={b2s(self.vehicle_pid.get())}"
            f"&lateral={self.lateral.get()}"
            f"&invert_yawpid={b2s(self.invert_yawpid.get())}"
            f"&target_r={self.target_r.get()}"
            f"&v_max={self.v_max.get()}"
            f"&v_dead_x={self.v_dead_x.get()}"
            f"&v_dead_y={self.v_dead_y.get()}"
            f"&kx_img={self.kx_img.get()}"
            f"&lost_timeout={self.lost_timeout.get()}"
            f"&scan_center_yaw={self.scan_center_yaw.get()}"
            f"&scan_center_pitch={self.scan_center_pitch.get()}"
            f"&scan_radius_yaw={self.scan_radius_yaw.get()}"
            f"&scan_radius_pitch={self.scan_radius_pitch.get()}"
            f"&scan_omega_dps={self.scan_omega_dps.get()}"
            f"&scan_step_deg=5"
        )
        url = f"{self._url(ENDPOINTS['track_start'])}?{params}"
        self._get(url, "track start")

    def track_stop(self) -> None:
        self._get(self._url(ENDPOINTS["track_stop"]), "track stop")

    # ------------------------------------------------------------------
    # Gimbal
    # ------------------------------------------------------------------

    def gimbal_center(self) -> None:
        self._get(self._url(ENDPOINTS["gimbal_center"]), "gimbal centre")

    def gimbal_angle(self) -> None:
        url = self._url(ENDPOINTS["gimbal_angle"])
        url += f"?yaw={self.yaw.get()}&pitch={self.pitch.get()}"
        self._get(url, "gimbal angle")

    def gimbal_step(self, dx: int = 0, dy: int = 0, big: bool = False) -> None:
        url = self._url(ENDPOINTS["gimbal_step"])
        url += f"?dx={dx}&dy={dy}&big={b2s(big)}"
        self._get(url, "gimbal step")

    # ------------------------------------------------------------------
    # Photo capture
    # ------------------------------------------------------------------

    def capture_photo(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("All files", "*.*")],
        )
        if not path:
            return

        def _fetch():
            try:
                resp = self.sess.get(
                    self._url(ENDPOINTS["frame"]),
                    timeout=self.timeout.get(),
                )
                with open(path, "wb") as f:
                    f.write(resp.content)
                self.status.set(f"Saved: {path}")
            except Exception as e:
                self.status.set(f"Photo error: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    def status_poll_start(self) -> None:
        self._poll_status()

    def _poll_status(self) -> None:
        def _fetch():
            try:
                resp = self.sess.get(
                    self._url(ENDPOINTS["track_status"]),
                    timeout=1.0,
                )
                data = resp.json()
                found = data.get("found", False)
                scan  = data.get("scan_active", False)
                r_val = data.get("r", 0)
                mode  = "SCAN" if scan else ("TRACK" if found else "idle")
                self.status.set(f"status: {mode} | r={r_val}")
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()
        self.status_job = self.after(500, self._poll_status)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    root.resizable(True, True)

    try:
        style = ttk.Style()
        style.configure("Success.TButton", foreground="green")
        style.configure("Danger.TButton", foreground="red")
    except Exception:
        pass

    app = App(master=root)
    root.mainloop()


if __name__ == "__main__":
    main()
