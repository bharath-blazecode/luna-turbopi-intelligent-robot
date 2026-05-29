# Setup and Usage

## Prerequisites

- Raspberry Pi 4B with the Hiwonder TurboPi SDK installed
- Pi and your laptop connected to the same Wi-Fi network
- Python dependencies installed (`pip install -r requirements.txt`)
- SSH access to the Pi
- The Flask server has no authentication. Run it only on a trusted local network

---

## Mode 1 — Full Control System (Flask server + Tkinter app)

This is the main operating mode. The Flask server runs on the Pi and handles all hardware control. The Tkinter app runs on your laptop and sends commands over HTTP.

**Step 1 — Find the Pi's IP address**

On the Pi, run:
```bash
hostname -I
```
Note the IP (e.g. `192.168.1.45`). You'll need this for the control app.

**Step 2 — Start the Flask server on the Pi**

SSH into the Pi, then run:
```bash
python3 src/flask_server/flask_robot_server.py
```

The server starts on port 5000. Leave this terminal open.

**Step 3 — Launch the Tkinter control app on your laptop**

```bash
LUNA_ROBOT_URL=http://192.168.1.45:5000 python3 src/control_app/tkinter_control_app.py
```

Or launch the app without the environment variable and type the IP directly into the **Base URL** field at the top of the window.

**Step 4 — Verify the connection**

Click **Ping**. The status bar should show `health: 200`. If it shows an error, check that the Flask server is still running and the IP address is correct.

**Step 5 — Control the robot**

| Input | Action |
|---|---|
| Arrow keys | Forward / Backward / Turn Left / Turn Right |
| Z / C | Strafe Left / Strafe Right |
| Space | Stop |
| t / T | Start / Stop ball tracking |
| j / l / i / k | Gimbal step (hold Shift for larger step) |
| o | Centre gimbal |

Enable **Vehicle PID** and click **Start Tracking** to start autonomous ball-following. Click **Start Preview** for a live camera feed.

---

## Mode 2 — Standalone Voice Control (Pi only)

These scripts run directly on the Pi. No laptop or Flask server needed. SSH into the Pi and run the script for the behaviour you want.

**Voice control + line-following**
```bash
python3 src/line_following/wonderecho_line_following_controller.py
```
Manual movement commands (go, back, left, right, stop) work immediately. Say the configured wake phrase to start line-following. Any manual movement command stops line-following automatically.

**Voice control + snapshot capture**
```bash
python3 src/voice_control/wonderecho_snapshot_control.py
```
Standard movement commands plus a snapshot command (ID 131 by default) that saves a timestamped JPEG to `./snapshots/`.

**Voice control + crash guard**
```bash
python3 src/safety_guard/voice_crash_guard.py
```
Same as standard voice control, but the forward command polls the ultrasonic sensor during movement and stops early if an obstacle is within the threshold. Falls back to normal forward movement if no sonar hardware is detected.

**Voice control + ball tracking**
```bash
python3 src/vision_tracking/voice_ball_tracking.py
```
Say the configured phrase to start tracking a red, green, or blue ball. The robot uses the camera and PID control to find and follow the target. Say "stop" to end tracking.

---

## Stopping any script

Press `Ctrl+C`. All scripts handle `KeyboardInterrupt` and stop the chassis cleanly before exiting.

---

## Configuration

**SDK path** — if your TurboPi SDK is installed somewhere other than `/home/pi/TurboPi`:
```bash
export LUNA_TURBOPI_SDK=/path/to/sdk
```

**Robot IP (Mode 1)** — set before launching the control app:
```bash
export LUNA_ROBOT_URL=http://192.168.1.45:5000
```

**WonderEcho command IDs** — if your voice profile uses different IDs than the defaults, create `~/voice_id_overrides.json` on the Pi:
```json
{
    "1": "go",
    "2": "back",
    "3": "left",
    "4": "right",
    "9": "stop",
    "102": "line_on"
}
```
Scripts load this file at startup if it exists. This lets you adjust the ID mapping without touching the source code.

**Snapshot output directory:**
```bash
export LUNA_SNAPSHOT_DIR=/path/to/save/photos
```
