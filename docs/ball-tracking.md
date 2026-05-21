# Ball-Tracking System

## Overview

LUNA included a camera-based ball-following system that allowed the robot to detect and follow a coloured object using computer vision techniques. This subsystem combined camera input, image processing, movement logic, and PID-style behaviour to create autonomous object-following functionality.

## Purpose

The purpose of this subsystem was to explore how computer vision can be used to guide robot movement in real time. Instead of relying only on manual or voice commands, the robot could analyse visual input and react dynamically to a moving target.

## System Workflow

```text
Camera Input
      ↓
Frame Processing
      ↓
Colour / Object Detection
      ↓
Target Position Calculation
      ↓
Movement Decision
      ↓
Motor Control
      ↓
Robot Follows Target
```

## Implementation Approach

The ball-tracking system used OpenCV-based image processing to detect a coloured target from the camera feed. The system analysed each frame, identified the target position, and adjusted robot movement accordingly.

Movement behaviour was connected to the detected position of the target so the robot could continuously adjust its direction and maintain tracking.

## Technical Focus

This subsystem involved:

- Camera-based visual input
- OpenCV image processing
- Colour-based target detection
- Real-time movement adjustment
- Integration with robot motor-control systems
- Autonomous tracking behaviour

## PID-Style Behaviour

To improve tracking smoothness, PID-style tuning was used to help stabilise robot movement during autonomous following behaviour.

This helped reduce:

- Sudden movement changes
- Overshooting behaviour
- Unstable turning response
- Jitter during target tracking

## Challenges

Ball-following behaviour required the robot to process visual information while simultaneously adjusting physical movement in real time.

Challenges included:

- Maintaining stable target detection
- Handling movement delay
- Reducing unstable turning behaviour
- Synchronising camera processing with motor response

## Engineering Lessons

This subsystem demonstrated how computer vision and robotics can be integrated into an embedded system using Python, OpenCV, and movement-control logic.

It also highlighted the importance of balancing software processing, movement response, and real-world robot behaviour during autonomous operation.
