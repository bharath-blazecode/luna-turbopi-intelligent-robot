# Line-Following / Instruction-Following System

## Overview

LUNA included a camera-based line-following behaviour that allowed the robot to follow a pathway using visual input. This subsystem was designed to let the robot respond to a physical path rather than relying only on manual or voice commands.

## Purpose

The purpose of this feature was to explore how computer vision can guide robot movement in a real-world environment. Instead of only receiving direct commands, the robot could use camera input to interpret a pathway and adjust its movement accordingly.

## System Workflow

```text
Camera Input
      ↓
Frame Processing
      ↓
Line / Path Detection
      ↓
Movement Decision
      ↓
Motor Control
      ↓
Robot Follows Pathway
```
## Implementation Approach

The line-following system used camera-based guidance to detect a pathway and adjust the robot’s movement. The behaviour allowed LUNA to follow instructions from the environment, making the robot more autonomous than simple manual control.

This feature required the system to connect visual input with movement logic so the robot could respond continuously as the pathway changed.

## Technical Focus

This subsystem involved:

- Camera-based input processing
- Pathway detection logic
- Movement adjustment based on visual feedback
- Integration with the robot’s motor-control system
- Real-world physical testing using the TurboPi platform

## Challenges

Line-following required the robot to respond smoothly to visual changes while maintaining stable movement. The main challenge was connecting the camera-based interpretation of the path with the robot’s physical movement response.

## Engineering Lessons

This feature demonstrated how visual perception can be connected to movement control in an embedded robotics system. It also showed the importance of careful integration between camera input, control logic, and physical robot behaviour.
