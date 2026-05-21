# LUNA — TurboPi Intelligent Robot

![LUNA TurboPi robot](media/photos/luna-front-view.jpg)

LUNA is a Raspberry Pi-based robotics project built on the Hiwonder TurboPi platform. The project integrates wireless robot control, camera streaming, OpenCV-based ball tracking, WonderEcho voice commands, PID-style tuning, and ultrasonic safety logic into one working embedded robotics system.

> This repository is a sanitized portfolio version of a robotics project. It is structured to demonstrate the technical design, implementation process, testing, and engineering decisions without publishing the original assignment submission.

## Project Highlights

- Raspberry Pi-based robot control system
- Flask server for wireless command routing
- Tkinter-based desktop control interface
- WonderEcho offline voice-control integration using I²C
- OpenCV-based coloured ball detection and tracking
- PID-style fine-tuning for smoother robot behaviour
- Mecanum-wheel movement: forward, backward, turning, and strafing
- Ultrasonic forward crash guard for safer movement
- Camera streaming and snapshot capture

## Technology Stack

| Area | Technologies |
|---|---|
| Hardware | Raspberry Pi 4B, Hiwonder TurboPi, mecanum wheels, camera module, WonderEcho, ultrasonic sensor |
| Programming | Python |
| Web/control layer | Flask |
| Computer vision | OpenCV, NumPy |
| Interface | Tkinter |
| Communication | I²C, GPIO, HTTP endpoints |
| Robotics/control | PID-style tuning, motor control, servo/gimbal control |

## My Contributions

This project was completed as a two-person robotics project. My main contributions included:

- Implemented the Raspberry Pi communication layer used to connect robot control components.
- Contributed to the Flask-based control application and command-routing structure.
- Led most of the hardware assembly, including robot setup, component mounting, and physical testing.
- Integrated and tested the WonderEcho voice-control module.
- Fine-tuned the PID-style control behaviour after the initial implementation was started by my teammate.
- Helped test and debug movement behaviour, ball tracking, command timing, and safety responses.
- Contributed to documentation, testing notes, and final project presentation material.

## Repository Structure

```text
docs/          Technical documentation and project write-ups
media/         Project photos, diagrams, and demo visuals
src/           Cleaned and selected source code modules
README-assets/ Supporting images for the README
