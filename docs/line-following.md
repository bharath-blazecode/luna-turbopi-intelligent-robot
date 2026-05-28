# Line-Following / Instruction-Following System

## Overview

LUNA's line-following behaviour is built on Hiwonder's `VisualPatrol.py` — the TurboPi platform's camera-based path-detection routine. My contribution was the WonderEcho integration layer: a controller that starts and stops `VisualPatrol.py` as a managed subprocess in response to spoken voice commands, and handles the interaction between manual movement and autonomous following.

## What VisualPatrol.py Does

`VisualPatrol.py` uses the robot's camera to detect a black line on a contrasting surface. It processes each frame to find the line's position and steers the mecanum chassis to keep the robot aligned with the path. The vision and movement logic are part of the Hiwonder SDK and not reproduced in this repository.

## My Contribution: The WonderEcho Integration Controller

The file `wonderecho_line_following_controller.py` handles:

- Reading WonderEcho voice command IDs over I²C at 20 ms polling intervals
- Starting `VisualPatrol.py` as a subprocess when voice command ID 102 is received
- Stopping the subprocess cleanly (SIGINT → terminate → kill escalation) when any manual movement command is received
- Preventing manual commands and the line-following routine from running at the same time
- Logging all recognised command IDs for troubleshooting

```text
Voice Command (ID 102)
        ↓
Read over I²C (bus 1, addr 0x34, reg 0x64)
        ↓
Map ID → "line_on" action
        ↓
Launch VisualPatrol.py as subprocess
        ↓
Robot follows line autonomously
        ↓
Manual movement command received
        ↓
Stop subprocess → execute manual movement
```

## Why Subprocess Rather Than Import

Running `VisualPatrol.py` as a subprocess rather than importing it directly keeps the two control systems independent. If the line-following routine crashes or hangs, it doesn't take down the voice-control loop. It also means the voice controller can stop line-following cleanly without relying on internal state from the SDK module.

## Configuration

Voice command IDs can be overridden at runtime without editing the source by placing a JSON file at `~/voice_id_overrides.json`:

```json
{
    "102": "line_on",
    "9": "stop"
}
```

The default command map is `{1: go, 2: back, 3: left, 4: right, 9: stop, 102: line_on}`.

## Challenges

The main problem was ensuring that starting and stopping line-following felt safe and predictable rather than glitchy.

A manual movement command arriving while `VisualPatrol.py` was running would cause both the manual movement code and the line-following code to issue chassis commands at the same time. The fix was to always stop the subprocess before executing any manual movement action — so the two paths cannot run concurrently.

The subprocess stop sequence also needed to be robust. A simple `terminate()` call would sometimes leave the process in a zombie state if the SDK held open file descriptors. The SIGINT → 2 s wait → terminate → kill escalation was the reliable solution.

## Engineering Notes

This feature is a useful example of process management in Python — using `subprocess.Popen`, signal handling, and timeout-based escalation to control an external program safely. The same pattern would apply to any situation where you need to run and stop a third-party script from a parent control loop.
