# PID-Style Tuning

## Overview

LUNA used PID-style tuning to improve the stability and smoothness of autonomous movement behaviours, especially during ball-following and tracking. This helped the robot respond more smoothly instead of making sudden or unstable movements.

The initial PID implementation was started by Zhirui Lu, and further fine-tuning was completed by Bharath “Barry” Sampath to improve real-world robot behaviour.

## Purpose

The purpose of PID-style tuning was to make LUNA’s movement more controlled when responding to visual input. Without tuning, the robot could react too sharply, overshoot the target, or move in a jittery way.

PID-style control helped the robot adjust its response based on how far it was from the target and how quickly the target position was changing.

## What PID Helps With

PID-style tuning was used to improve:

- Smooth target following
- More stable turning behaviour
- Reduced jitter during tracking
- Better response to target movement
- Less overshooting when correcting position
- More controlled autonomous movement

## Simplified Control Concept

```text
Target Position
      ↓
Compare with Current Position
      ↓
Calculate Error
      ↓
Apply PID-Style Adjustment
      ↓
Update Motor / Movement Response
      ↓
Robot Moves More Smoothly
```

## Implementation Focus

The tuning process focused on adjusting how strongly the robot responded to changes in the target’s position.

If the response was too strong, the robot could overcorrect or shake.  
If the response was too weak, the robot could react too slowly or fail to follow the target properly.

The tuning process aimed to find a practical balance between:

- Responsiveness
- Stability
- Smoothness
- Safety
- Real-world movement behaviour

## Practical Challenges

PID-style tuning was challenging because the robot’s behaviour depended on both software and physical hardware conditions.

Challenges included:

- Movement delay between command and physical response
- Camera processing delay
- Servo and motor response limitations
- Jitter during target tracking
- Overshooting when the robot corrected too aggressively
- Differences between ideal code behaviour and real-world robot movement

## Fine-Tuning Process

The PID-style behaviour was refined through repeated observation and adjustment. The robot’s movement was tested in real conditions, then tuning values were adjusted to improve stability.

The fine-tuning process helped make the robot’s autonomous behaviour more controlled and practical during demonstrations.

## Engineering Lessons

This part of the project showed that robotics programming is not only about writing code. It also requires observing how the physical robot behaves and adjusting the control logic to match real-world movement.

PID-style tuning demonstrated the importance of:

- Control-system thinking
- Iterative improvement
- Real-world testing
- Hardware/software interaction
- Balancing stability and responsiveness
