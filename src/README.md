# Source Code

Selected and sanitized source code modules from the LUNA TurboPi Intelligent Robot project.

Each subfolder covers one subsystem so they can be understood independently.

## Folder Structure

| Folder | Contents |
|---|---|
| `control_app/` | Tkinter desktop control interface |
| `flask_server/` | Flask server and robot command routing |
| `voice_control/` | WonderEcho voice-control with snapshot capture |
| `vision_tracking/` | Stand-alone voice + ball-tracking |
| `line_following/` | WonderEcho integration controller for line-following |
| `safety_guard/` | Ultrasonic crash guard for forward movement |

## Notes

These modules require Raspberry Pi hardware, the Hiwonder TurboPi platform, and the HiwonderSDK to run. The SDK path defaults to `/home/pi/TurboPi` and can be overridden with the `LUNA_TURBOPI_SDK` environment variable.

See [`requirements.txt`](../requirements.txt) for pip-installable dependencies.
