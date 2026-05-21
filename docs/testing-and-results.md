# Testing and Results

## Overview

Testing was an important part of the LUNA project because the robot combined software, hardware, sensors, camera input, voice control, and physical movement. Each subsystem needed to be checked individually before being integrated into the complete robot.

The testing process focused on confirming that the robot could respond to commands, move correctly, process camera input, follow visual targets or pathways, and operate reliably during demonstrations.

## Testing Goals

The main goals of testing were to confirm that:

- The Raspberry Pi could communicate correctly with the robot hardware.
- The Flask control system could send movement commands successfully.
- The WonderEcho voice-control module could trigger the correct robot actions.
- The camera-based behaviours could support line-following and ball-tracking.
- PID-style tuning improved movement stability.
- The robot could operate safely and consistently during real-world use.

## Tested Subsystems

| Subsystem | What Was Tested | Result |
|---|---|---|
| Hardware assembly | Robot setup, motor connections, camera mounting, wiring, and component placement | Robot was physically assembled and prepared for software integration |
| Raspberry Pi communication | Communication between Raspberry Pi, robot hardware, and control modules | Raspberry Pi successfully acted as the main control platform |
| Flask control system | Manual movement commands and command routing | Commands were routed through the control system successfully |
| WonderEcho voice control | I²C command reading, command mapping, and movement triggering | Voice commands were successfully connected to robot movement |
| Line-following / instruction-following | Camera-based pathway-following behaviour | Robot was able to follow a pathway using visual guidance |
| Ball-tracking | Camera-based object detection and tracking behaviour | Robot was able to support coloured ball-following behaviour |
| PID-style tuning | Movement smoothness, correction behaviour, and response stability | Fine-tuning improved the robot’s autonomous movement behaviour |
| Safety / troubleshooting | Hardware issues, motor response, and movement reliability | Practical troubleshooting improved the robot’s physical reliability |

## Hardware Testing

The hardware testing process involved checking that the robot components were correctly assembled and physically stable. This included checking the Raspberry Pi, TurboPi platform, wheels, camera, motors, wiring, and attached modules.

During development, hardware issues were encountered, including a motor-related issue and a broken wheel component. A practical repair approach was identified by reworking available motor parts so the robot could continue operating. This highlighted the importance of hardware troubleshooting in robotics projects.

## Movement Testing

Movement testing focused on confirming that the robot could respond to basic movement commands, including:

- Forward movement
- Backward movement
- Left and right turning
- Strafing movement
- Stop commands

These tests helped confirm that command inputs were being translated into physical robot movement correctly.

## Flask Control Testing

The Flask-based control system was tested by sending movement commands through the control workflow and observing the robot’s physical response.

Testing focused on:

- Command routing
- Response timing
- Movement consistency
- Connection between software commands and hardware output

This helped confirm that the software control layer could successfully communicate with the robot’s movement system.

## WonderEcho Voice-Control Testing

The WonderEcho voice-control integration was tested by using spoken commands and observing whether the robot performed the correct action.

Testing focused on:

- Reading command values through I²C
- Mapping voice command IDs to robot movement actions
- Triggering movement from voice input
- Confirming command-response behaviour
- Reducing unintended or repeated command behaviour

The final result showed that the WonderEcho module could be integrated into the Raspberry Pi control system and used as a hands-free input method for robot movement.

## Line-Following Testing

The line-following system was tested by placing the robot on a visible pathway and observing whether it could respond to the path using camera-based guidance.

Testing focused on:

- Detecting the pathway through camera input
- Connecting visual input to movement decisions
- Keeping the robot aligned with the path
- Adjusting movement as the pathway changed

This confirmed that LUNA could use visual information from its environment to support instruction-following / line-following behaviour.

## Ball-Tracking Testing

The ball-tracking system was tested by using a coloured object as the visual target. The robot used camera input and computer vision processing to detect and respond to the target.

Testing focused on:

- Coloured object detection
- Target position tracking
- Movement adjustment based on visual feedback
- Stability during autonomous following behaviour

This confirmed that the robot could support camera-based ball-following behaviour.

## PID-Style Tuning Results

PID-style tuning was used to improve the smoothness and stability of autonomous movement. The robot’s response was adjusted based on how it behaved during real-world testing.

The tuning process helped reduce:

- Jittery movement
- Overcorrection
- Sudden response changes
- Unstable tracking behaviour

The final tuned behaviour was more controlled and suitable for demonstration.

## Key Challenges Found During Testing

Several issues appeared during physical testing and integration:

- Hardware reliability issues, including motor and wheel problems.
- Movement behaviour not always matching expected direction or response.
- Voice-control commands needing stable mapping and response handling.
- Autonomous tracking requiring tuning to reduce jitter and overcorrection.
- Real-world robot behaviour differing from ideal software behaviour.

These issues were resolved or improved through hardware troubleshooting, software refinement, and repeated physical validation.

## Final Result

The final LUNA system demonstrated a working robotics platform that combined:

- Raspberry Pi-based control
- Flask command routing
- Manual movement control
- WonderEcho voice-control integration
- Camera-based line-following
- Camera-based ball-tracking
- PID-style movement tuning
- Hardware assembly and troubleshooting

Overall, the project successfully demonstrated how software, hardware, sensors, and control logic can be integrated into a practical embedded robotics system.

## Lessons Learned

This project showed that robotics development requires more than writing code. The final system depended on hardware setup, physical testing, communication reliability, software integration, and practical troubleshooting.

Key lessons included:

- Embedded systems require strong hardware/software coordination.
- Physical testing is essential because robot behaviour can differ from expected code behaviour.
- Communication protocols such as I²C are important for connecting external modules.
- Computer vision features require careful tuning in real environments.
- Clear modular design makes the system easier to test, explain, and improve.
