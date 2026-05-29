# LUNA — TurboPi Intelligent Robot

![LUNA TurboPi robot](media/photos/luna-robot-front-view.jpg)
> Raspberry Pi robotics platform integrating Flask control, OpenCV vision, WonderEcho voice commands, line-following, ball-tracking, and PID-style tuning.

**Demo video:** https://youtu.be/RrAcwlQjl2Y

## Overview

LUNA is a Raspberry Pi-based intelligent robot built on the Hiwonder TurboPi platform. The project combines hardware assembly, Python programming, wireless control, computer vision, voice interaction, and movement tuning into one integrated robotics system.

This repository is structured as a technical case study covering design decisions, implementation details, and engineering challenges.

## Key Features

- Raspberry Pi-based robot control system
- Flask server for wireless command routing
- Tkinter-based desktop control interface
- WonderEcho offline voice-control integration using I²C
- Camera-based line-following (voice-triggered subprocess controller for Hiwonder VisualPatrol.py)
- OpenCV-based coloured ball-following using LAB colour detection and PID tracking
- PID-style fine-tuning for smoother autonomous movement
- Mecanum-wheel movement: forward, backward, turning, and strafing
- Hardware troubleshooting and physical robot integration
- Ultrasonic crash guard for forward movement safety

## Technology Stack

| Area | Technologies |
|---|---|
| Hardware | Raspberry Pi 4B, Hiwonder TurboPi, mecanum wheels, camera module, WonderEcho module, ultrasonic sensor |
| Programming | Python |
| Web / control layer | Flask |
| Computer vision | OpenCV, NumPy |
| Interface | Tkinter |
| Communication | I²C, GPIO, HTTP endpoints |
| Robotics / control | PID-style tuning, motor control, servo/gimbal control |

## My Contributions

This project was completed collaboratively by **Bharath "Barry" Sampath** and **Zhirui Lu**.

My main contributions:

- Sourced and maintained the TurboPi robot hardware throughout the project
- Raspberry Pi communication and hardware-control integration
- WonderEcho voice-control integration — I²C command reading, ID mapping, debounce logic, and movement triggering
- Line-following integration controller: voice-triggered subprocess management for Hiwonder's VisualPatrol.py
- Hardware assembly, robot setup, component mounting, and hands-on troubleshooting (including diagnosing and resolving a motor/wheel failure)
- Flask control app collaboration and command-routing workflow support
- PID-style fine-tuning after the initial PID implementation by Zhirui Lu
- Project documentation, technical explanation, and final presentation support

→ Full breakdown: [docs/contribution-statement.md](docs/contribution-statement.md)

## Documentation

| Document | Description |
|---|---|
| [Setup and Usage](docs/setup-and-usage.md) | How to run the full system and standalone voice scripts |
| [Project Overview](docs/project-overview.md) | High-level explanation of LUNA, purpose, and key capabilities |
| [System Architecture](docs/system-architecture.md) | How the Raspberry Pi, software, sensors, camera, and hardware connect |
| [Contribution Statement](docs/contribution-statement.md) | Individual and collaborative contribution breakdown |
| [WonderEcho Voice Control](docs/wonderecho-voice-control.md) | Offline voice-control integration using I²C |
| [Line-Following System](docs/line-following.md) | WonderEcho integration controller for pathway-following behaviour |
| [Ball-Tracking System](docs/ball-tracking.md) | LAB colour detection, PID gimbal control, and chassis following |
| [PID-Style Tuning](docs/pid-tuning.md) | Tuning process and control parameters for smoother autonomous movement |
| [Testing and Results](docs/testing-and-results.md) | Subsystem testing and final project results |
| [Challenges and Solutions](docs/challenges-and-solutions.md) | Hardware, software, and integration problems encountered and resolved |
| [Future Improvements](docs/future-improvements.md) | Possible next steps and project extensions |

## Repository Structure

```text
docs/           Technical documentation and project write-ups
media/          Project photos, diagrams, screenshots, and demo visuals
src/            Selected and sanitized source code modules
LICENSE         MIT License
DISCLAIMER.md   Usage, academic integrity, and liability notice
```

## Source Code

Code is organised into focused modules, one per subsystem.

```text
src/
├── control_app/        Tkinter desktop control interface        ✓
├── flask_server/       Flask server and robot command routing   ✓
├── voice_control/      WonderEcho snapshot controller           ✓
├── vision_tracking/    Stand-alone voice + ball-tracking        ✓
├── line_following/     WonderEcho line-following controller      ✓
└── safety_guard/       Ultrasonic crash guard                   ✓
```

## Running the Project

LUNA runs in two modes — the full control system (Flask server on the Pi, Tkinter app on your laptop) or standalone voice scripts (Pi only). Install dependencies first:

```bash
pip install -r requirements.txt
```

→ Full setup steps, configuration options, and troubleshooting: [docs/setup-and-usage.md](docs/setup-and-usage.md)

## Third-Party Components

The TurboPi platform and associated SDK components (HiwonderSDK, VisualPatrol.py, Camera, yaml_handle) are products of [Hiwonder](https://www.hiwonder.com). These are not included in this repository — SDK paths and function calls are referenced only to document integration work.
