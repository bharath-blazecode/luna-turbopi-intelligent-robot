# Contribution Statement

LUNA was completed as a two-person robotics project. This repository presents a sanitized portfolio version of the work, focusing on the technical design, implementation process, testing, and engineering lessons learned.

## Contributions

This project was completed as a two-person university robotics project. Both team members contributed significantly to the final system, with responsibilities divided across hardware assembly, robot control, computer vision, voice interaction, and tuning.

### Bharath “Barry” Sampath — Contributions

My main contributions included:

- Implemented the Raspberry Pi communication layer used to connect the robot’s software control logic with the hardware components.
- Designed and implemented the WonderEcho voice-control integration, including I²C command reading, command mapping, movement triggering, and voice-control testing.
- Developed the instruction-following / line-following behaviour, allowing the robot to follow a pathway using camera-based guidance.
- Led most of the physical hardware assembly, including component setup, mounting, wiring support, and robot preparation.
- Contributed practical hardware troubleshooting, including identifying a repair approach when the motor was not functioning correctly and a wheel component broke.
- Contributed to the Flask-based control app and command-routing workflow.
- Fine-tuned the PID-style control behaviour after the initial PID implementation was started by my teammate.
- Contributed to project documentation, technical explanation, and final presentation material.

### Zhirui Lu — Contributions

Zhirui Lu contributed significantly to the project, including:

- Contributing to the Flask-based control app and server-side control workflow.
- Supporting hardware assembly and robot setup.
- Starting the initial PID implementation used for autonomous tracking behaviour.
- Contributing significantly to the ball-following / ball-tracking functionality.
- Supporting control logic development and project documentation.

### Collaboration Note

The final LUNA system was the result of shared teamwork. This repository separates individual responsibilities where possible, while recognising that some components, such as the Flask control system, PID behaviour, and final integration, involved collaborative development and refinement.

## Academic Integrity Note

This repository is not a copy of the original university submission. It is a cleaned and restructured portfolio version intended to demonstrate technical learning and project experience.
