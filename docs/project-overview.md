# Project Overview

LUNA is a Raspberry Pi-based intelligent robot built on the Hiwonder TurboPi platform. The project combines hardware assembly, Python programming, wireless control, computer vision, voice interaction, and movement tuning into one integrated robotics system.

The robot supports multiple control and automation behaviours: manual app-based movement, WonderEcho voice-control commands, camera-based line-following, ball-following, and safer movement using sensor-based crash-guard logic.

## Purpose

The goal of this project was to explore how software, hardware, sensors, and communication protocols work together in an embedded robotics system. LUNA demonstrates how a Raspberry Pi can act as the central computing platform while coordinating camera input, motor control, voice commands, and robot movement behaviour.

## Key Capabilities

- Manual robot control through a Flask-based control system
- Raspberry Pi communication with robot hardware components
- WonderEcho voice-control integration using I²C command reading
- Camera-based line-following (voice-triggered subprocess controller)
- Ball-following and tracking using computer vision and PID control
- PID-style tuning for smoother autonomous movement
- Hardware assembly, troubleshooting, and physical system integration

## Technologies Used

- Raspberry Pi 4B
- Hiwonder TurboPi robot platform
- Python
- Flask
- OpenCV
- Tkinter
- WonderEcho voice-recognition module
- I²C communication
- Mecanum-wheel movement system
- Camera and ultrasonic sensing components
