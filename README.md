# LUNA — TurboPi Intelligent Robot

![LUNA TurboPi robot](media/photos/luna-robot-front-view.jpg)
> Raspberry Pi robotics platform integrating Flask control, OpenCV vision, WonderEcho voice commands, line-following, ball-tracking, and PID-style tuning.

## Overview

LUNA is a Raspberry Pi-based intelligent robot built on the Hiwonder TurboPi platform. The project combines hardware assembly, Python programming, wireless control, computer vision, voice interaction, and movement tuning into one integrated robotics system.

This repository is a sanitized portfolio version of a two-person university robotics project. It is structured to demonstrate the technical design, implementation process, testing, and engineering decisions without publishing the original academic submission.

## Key Features

- Raspberry Pi-based robot control system
- Flask server for wireless command routing
- Tkinter-based desktop control interface
- WonderEcho offline voice-control integration using I²C
- Camera-based instruction-following / line-following behaviour
- OpenCV-based coloured ball-following / ball-tracking
- PID-style fine-tuning for smoother autonomous movement
- Mecanum-wheel movement: forward, backward, turning, and strafing
- Hardware troubleshooting and physical robot integration
- Camera streaming and robot demonstration support

## Technology Stack

| Area | Technologies |
|---|---|
| Hardware | Raspberry Pi 4B, Hiwonder TurboPi, mecanum wheels, camera module, WonderEcho module, ultrasonic sensor |
| Programming | Python |
| Web/control layer | Flask |
| Computer vision | OpenCV, NumPy |
| Interface | Tkinter |
| Communication | I²C, GPIO, HTTP endpoints |
| Robotics/control | PID-style tuning, motor control, servo/gimbal control |

## My Contributions

This project was completed collaboratively by **Bharath “Barry” Sampath** and **Zhirui Lu**.

My main contributions included:

- Raspberry Pi communication and hardware-control integration
- WonderEcho voice-control integration using I²C command reading and movement mapping
- Instruction-following / line-following behaviour for pathway navigation
- Major hardware assembly, robot setup, component mounting, and practical hardware troubleshooting
- Flask control app collaboration and command-routing workflow support
- PID-style fine-tuning after the initial PID implementation was started by my teammate
- Project documentation, technical explanation, and final presentation support

For a detailed contribution breakdown, see:

[Contribution Statement](docs/contribution-statement.md)

## Documentation

| Document | Description |
|---|---|
| [Project Overview](docs/project-overview.md) | High-level explanation of LUNA, project purpose, and key capabilities |
| [System Architecture](docs/system-architecture.md) | Explains how the Raspberry Pi, software, sensors, camera, and robot hardware connect |
| [Contribution Statement](docs/contribution-statement.md) | Clear breakdown of individual and collaborative contributions |
| [WonderEcho Voice Control](docs/wonderecho-voice-control.md) | Details the offline voice-control integration using I²C |
| [Line-Following System](docs/line-following.md) | Explains the instruction-following / pathway-following behaviour |
| [Ball-Tracking System](docs/ball-tracking.md) | Covers camera-based object detection and ball-following behaviour |
| [PID-Style Tuning](docs/pid-tuning.md) | Explains tuning for smoother autonomous movement |
| [Testing and Results](docs/testing-and-results.md) | Summarises subsystem testing and final project results |
| [Challenges and Solutions](docs/challenges-and-solutions.md) | Documents key hardware, software, and integration challenges |
| [Future Improvements](docs/future-improvements.md) | Outlines possible next steps and project extensions |

## Repository Structure

```text
docs/          Technical documentation and project write-ups
media/         Project photos, diagrams, screenshots, and demo visuals
src/           Selected and cleaned source code modules
README-assets/ Supporting images for the README
```

## Current Status

The repository currently includes the professional documentation structure and project media. Selected cleaned code modules will be added after the documentation and project explanation are complete.

The original university submission, student details, tutor details, and full raw assessment document are not included.

## Planned Code Sections

The source code will be organised into focused modules:

```text
src/
├── control_app/
├── flask_server/
├── voice_control/
├── vision_tracking/
├── line_following/
└── safety_guard/
```

## Portfolio Note

This project is presented as a technical case study showing embedded systems, Python development, robotics, computer vision, voice-control integration, hardware troubleshooting, and control-system thinking.
