# Ball-Tracking System

## Overview

LUNA's ball-tracking system uses camera-based computer vision to detect and follow a coloured target in real time. It combines LAB colour-space detection, contour analysis, PID-based gimbal control, and chassis following behaviour into an autonomous tracking loop. This was primarily Zhirui Lu's implementation, with PID fine-tuning contributions from both team members.

## How It Works

The system runs two concurrent threads — one for head/gimbal control, one for chassis movement — both fed by a shared vision pipeline.

```text
Camera Input
      ↓
Frame Processing
      ↓
Colour / Object Detection [Threshold against stored LAB ranges (red / green / blue)]
      ↓
Target Position Calculation
      ↓
Movement Decision
      ↓
Motor Control
      ↓
┌─────────────────────────────────────────┐
│  Gimbal thread: move camera to centre   │
│  Chassis thread: drive toward target    │
└─────────────────────────────────────────┘
```

## Vision Pipeline

Colour detection uses the LAB colour space rather than RGB or HSV. LAB thresholds are stored in a YAML config file and loaded at startup, which means colour ranges can be tuned without editing the source code.

For each frame the pipeline converts to LAB, applies a 3×3 Gaussian blur, then runs `cv2.inRange` against the stored thresholds. The result goes through morphological open and close operations to remove noise and fill gaps. The largest contour above 300 px² is selected as the target.

## Gimbal (Head) Control

The gimbal uses a proportional + integral controller to keep the detected target centred in the camera frame:

- Runs at ~55 Hz (18 ms loop)
- Gain values: Kp = 0.40 (yaw), 0.44 (pitch); Ki = 0.020 (yaw), 0.025 (pitch) per second
- Anti-windup clamp of ±180 pulse units on the integral term
- A lock/unlock system requiring 4 consecutive detections to confirm tracking and 0.5 s without detection to release — this prevents single-frame noise from triggering movement

When the target is lost and the unlock timeout expires, the gimbal enters a raster scan pattern to search for the target.

## Chassis (Vehicle) Following

Once the gimbal has a stable lock, the chassis thread drives the robot toward the target:

- Distance is estimated from the detected ball radius
- Target radius for safe following distance: ~100 px
- PID gains: P = 0.15 (lateral / x), P = 1.00 (forward-back / y), with small I and D terms
- Deadband thresholds prevent movement for minor detection noise: ±15 px lateral, ±15 px forward-back
- Maximum chassis speed capped at 80% to keep movement safe indoors
- Command rate limited to 50–80 ms to reduce bus/servo chatter

## PID Tuning

The initial PID parameters were set by Zhirui Lu. I contributed further fine-tuning after observing real-world robot behaviour. The main issues corrected through tuning were gimbal oscillation, chassis overshooting the target distance, and jitter during slow target movement.

## Challenges

The main practical problems encountered:

- **Gimbal oscillation** — the head would overshoot and oscillate when gains were too high. Solved by reducing Kp and introducing a small integral term with anti-windup.
- **Chassis instability while tracking** — limiting the chassis command rate to 50–80 ms significantly reduced erratic movement.
- **False detections** — ambient lighting sometimes matched the LAB thresholds. The lock/unlock system (4 frames to lock, 0.5 s to unlock) filtered most single-frame noise.
- **Camera frame direction correction** — a global angle offset had to be applied (`/config/angle?forward=180`) because the SDK's angle reference didn't match the physical chassis orientation.
