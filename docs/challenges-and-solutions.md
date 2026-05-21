# Challenges and Solutions

## Overview

LUNA was not only a software project. It required hardware assembly, Raspberry Pi communication, camera-based behaviour, voice-control integration, movement tuning, and real-world troubleshooting. Because the robot interacted with physical components, several challenges appeared during development and testing.

This document summarises the main challenges encountered and how they were approached or resolved.

---

## 1. Hardware Assembly and Physical Reliability

### Challenge

One of the early challenges was ensuring that the robot hardware was physically stable and ready for software integration. The robot included multiple hardware components, including the Raspberry Pi, TurboPi platform, motors, wheels, camera module, WonderEcho module, and wiring connections.

During development, a motor-related issue occurred, and a wheel component was damaged. This affected the robot’s ability to move reliably.

### Solution

A practical troubleshooting approach was used to continue development. The hardware was inspected, and an alternative repair approach was identified by reworking available motor parts so the robot could continue operating.

This experience showed that robotics work often requires practical hardware problem-solving, not just software development.

### Lesson Learned

Physical reliability is essential in robotics. Even if the code is correct, the robot will not behave properly if motors, wheels, wiring, or mounted components are unstable.

---

## 2. Raspberry Pi Communication and Hardware Control

### Challenge

The Raspberry Pi needed to act as the central control platform for multiple hardware and software components. This required communication between the Raspberry Pi, robot control hardware, movement logic, sensors, and external modules.

The challenge was ensuring that commands from software could reliably trigger real physical movement.

### Solution

A Raspberry Pi communication layer was implemented to connect the robot’s control logic with its hardware components. This allowed software commands to be translated into robot actions through the hardware-control system.

### Lesson Learned

Embedded systems require a clear communication pathway between software and hardware. Without reliable communication, individual features may work separately but fail during integration.

---

## 3. WonderEcho Voice-Control Integration

### Challenge

Integrating WonderEcho voice control required the robot to respond to spoken commands through local embedded processing. The challenge was reading command values from the WonderEcho module, mapping them to correct robot actions, and preventing incorrect or repeated command triggering.

Voice control also had to work alongside the existing movement-control system.

### Solution

The WonderEcho module was integrated using I²C communication. A Python-based command handler was used to read command IDs, map them to robot actions, and trigger movement behaviours such as forward, backward, left, right, and stop.

The integration was validated through repeated voice-command testing to confirm that spoken commands resulted in the expected robot response.

### Lesson Learned

Voice-control integration requires more than recognising commands. The system must also handle command mapping, timing, repeated input, and safe movement response.

---

## 4. Line-Following / Instruction-Following Behaviour

### Challenge

The robot needed to follow a pathway using camera-based guidance. This required the system to interpret visual input and convert it into movement decisions.

The challenge was connecting what the camera detected with how the robot should physically move.

### Solution

A line-following / instruction-following behaviour was developed so the robot could respond to a pathway using visual input. This allowed LUNA to move based on environmental guidance rather than only direct manual or voice commands.

### Lesson Learned

Camera-based behaviour requires strong integration between vision input and movement control. The robot must continuously interpret the environment and adjust its movement in real time.

---

## 5. Ball-Following and Computer Vision Tracking

### Challenge

The ball-following system required the robot to detect a coloured object and respond to its position. This involved processing camera frames and converting target position information into movement behaviour.

Challenges included maintaining detection stability and ensuring the robot responded smoothly while the target moved.

### Solution

The ball-tracking system used camera-based computer vision to identify and follow a coloured target. Movement logic was connected to the detected position of the object so the robot could adjust its movement during tracking.

### Lesson Learned

Computer vision features are sensitive to real-world conditions such as lighting, object movement, camera position, and processing delay. Reliable behaviour requires both software logic and physical testing.

---

## 6. PID-Style Tuning and Movement Stability

### Challenge

Autonomous tracking behaviour can become unstable if the robot reacts too strongly or too slowly to visual input. Without tuning, the robot may jitter, overcorrect, or move less smoothly.

### Solution

PID-style tuning was used to refine the robot’s movement response. The initial PID implementation was started by Zhirui Lu, and further fine-tuning was completed by Bharath “Barry” Sampath to improve real-world movement behaviour.

The tuning process helped make the robot’s movement more controlled during autonomous behaviours.

### Lesson Learned

Control tuning is highly practical. The best values cannot always be chosen from theory alone because real motors, wheels, sensors, and camera input introduce delay and physical variation.

---

## 7. Integrating Multiple Control Methods

### Challenge

LUNA supported multiple control methods, including manual control, voice control, line-following, and ball-tracking. The challenge was making these features work as part of one system rather than separate disconnected experiments.

### Solution

The system was structured around shared control logic and command-routing concepts. This helped connect different inputs to the robot’s movement system in a more organised way.

### Lesson Learned

Multi-feature robotics projects need modular design. Each feature should be understandable on its own, but also able to connect with the larger system safely and clearly.

---

## Final Reflection

The main challenge of LUNA was not just building one feature. The real challenge was integrating hardware, software, communication, computer vision, voice control, and movement tuning into one working robot platform.

This project showed the importance of:

- Practical hardware troubleshooting
- Clear software-to-hardware communication
- Modular control-system design
- Real-world testing and validation
- Team collaboration
- Honest contribution tracking
- Iterative improvement

Overall, these challenges made the project more valuable because they required real engineering decision-making rather than only following a fixed tutorial.
