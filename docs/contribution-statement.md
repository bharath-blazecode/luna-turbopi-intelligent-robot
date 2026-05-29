# Contribution Statement

LUNA was completed as a two-person robotics project. This repository presents a sanitized portfolio version of the work, focusing on the technical design, implementation process, system integration, validation, and engineering lessons learned.

## Overview

This project was completed collaboratively by Bharath "Barry" Sampath and Zhirui Lu. Both team members contributed significantly to the final system, with responsibilities divided across hardware assembly, robot control, Raspberry Pi communication, computer vision, voice interaction, PID-style tuning, and final integration.

## Bharath "Barry" Sampath

- Sourced and maintained the TurboPi robot hardware throughout the project
- Raspberry Pi communication and hardware-control integration
- WonderEcho voice-control integration — I²C command reading, command ID mapping, movement triggering, debounce logic, and response validation
- Instruction-following / line-following behaviour: wrote the WonderEcho integration controller that starts and stops the line-following routine via voice command
- Hardware assembly, robot setup, component mounting, and practical hardware troubleshooting (including diagnosing and resolving a motor/wheel failure mid-project)
- Flask control app collaboration and command-routing workflow support
- PID-style fine-tuning after the initial PID implementation was completed by my teammate
- Project documentation, technical explanation, and final presentation support

## Zhirui Lu

- Flask control app and server-side control workflow development
- Ball-following / ball-tracking functionality using camera-based computer vision
- Initial PID implementation for autonomous tracking behaviour
- Hardware assembly support, robot setup, and component preparation
- Control logic development and integration support
- Testing support for autonomous tracking behaviour and robot response
- Project documentation, technical explanation, and final presentation support

## Collaboration Note

The final LUNA system was the result of shared teamwork. Some components — including the Flask control system, PID behaviour, and final integration — involved collaborative development and refinement across both team members. This document separates individual responsibilities where possible while reflecting that reality.

## A Note on This Repository

This repository is not a copy of the original university submission. It is a cleaned and restructured portfolio version intended to demonstrate technical learning and project experience. 
