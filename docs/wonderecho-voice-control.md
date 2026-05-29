# WonderEcho Voice-Control Integration

LUNA supports offline voice control using the WonderEcho voice-recognition module — allowing the robot to respond to spoken commands with no cloud processing or internet connection required.

The WonderEcho connects to the Raspberry Pi over I²C. Python scripts poll the module continuously, read incoming command IDs, and map them to robot actions such as forward, backward, left, right, and stop.

## System Workflow

```text
Spoken Command
       ↓
WonderEcho (on-board recognition)
       ↓
I²C Register (addr 0x34, reg 0x64)
       ↓
Python polling loop (20 ms interval)
       ↓
Command ID read → action lookup
       ↓
Motor control execution
```

## Implementation

The WonderEcho module stores the most recently recognised command as a numeric ID in an I²C register. Python scripts open bus 1 with `SMBus(1)`, poll register `0x64` at address `0x34` every 20 ms, and look up the ID in a mapping table to find the corresponding action.

The default command map:

| Voice Command | ID | Robot Action |
|---|---|---|
| Go / Move forward | 1 | Forward movement |
| Move backward | 2 | Backward movement |
| Turn left | 3 | Left turn |
| Turn right | 4 | Right turn |
| Stop | 9 | Stop all movement |
| Start line-following | 102 | Launch VisualPatrol subprocess |
| Track red ball | 128 | Start tracking — red |
| Track green ball | 129 | Start tracking — green |
| Track blue ball | 130 | Start tracking — blue |
| Take photo | 131 | Capture and save snapshot |

Command IDs can be overridden without editing source code by placing a JSON file at `~/voice_id_overrides.json` on the Pi. This was added specifically because IDs sometimes needed adjusting after physical testing, and editing code for each test became impractical.

## Technical Challenges

### 1. Finding the correct I²C bus, address, and register

The WonderEcho module isn't well-documented for use outside Hiwonder's own examples. Getting the I²C parameters right — bus 1, address `0x34`, result register `0x64` — required testing and cross-referencing the SDK source. Using the wrong bus (bus 0) or the wrong register returns garbage data without raising an obvious error. The `read_wonderecho_id` function catches `OSError` silently so a communication failure doesn't crash the whole control loop, but getting the parameters right up front was essential.

### 2. Debouncing repeated command reads

The WonderEcho holds the last recognised command ID in its result register until a new command arrives. Polling at 20 ms means a single spoken word could trigger the same action 40 or 50 times before the register clears. Without debounce logic, one "go" command would drive the robot forward in a tight loop until something interrupted it.

The fix is tracking the previous command ID and skipping re-execution when the value hasn't changed:

```python
if command_id == last_id:
    time.sleep(POLL_DELAY_SECONDS)
    continue

last_id = command_id
```

This was one of the first problems that appeared during initial testing and had to be resolved before any further development could happen reliably.

### 3. Validating command IDs through physical testing

The WonderEcho doesn't expose a human-readable log of what it recognized. The only feedback is the numeric ID written to the register. This meant that for every phrase in the vocabulary, the process was: say the word, read back the ID, confirm it matched the expected mapping, update the code if not.

Some IDs didn't match their documentation or came out differently on the specific firmware version installed. The `voice_id_overrides.json` system was added after several cycles of this — it allows the mapping to be corrected at runtime without touching the source files.

### 4. Preventing conflicts between voice commands and autonomous behaviour

When the line-following routine was running as a subprocess, a voice movement command arriving at the same time would cause both the voice controller and `VisualPatrol.py` to issue chassis commands simultaneously — the result was erratic, unpredictable movement.

The solution was to always stop the line-following subprocess before executing any manual movement action. The comment in the code captures the intent directly:

```python
if action in {"go", "back", "left", "right"}:
    # Manual movement takes priority so it does not fight line-following.
    line_follower.stop()
```

The same principle applies when integrating voice control with ball tracking — the tracking thread has to be halted before manual commands take effect.

### 5. Tuning movement duration

The timed movement approach — drive for a fixed duration then stop — required physical tuning. At 0.4 seconds, forward movements felt too short to be meaningful. At 1.5 seconds, the robot had traveled too far to correct easily. The final values (0.8 s forward, 0.5 s turn) were reached through repeated testing on the floor, watching how far and how accurately the robot moved in response to each command.

These values are set as named constants in each script so they can be adjusted without searching through the code:

```python
forward_time_seconds: float = 0.8
turn_time_seconds: float = 0.5
```

### 6. Forward direction mismatch

During early integration with the Flask server, the robot's physical forward direction didn't match the SDK's angle reference. A command sent as "move forward" would cause the robot to move in a different direction than expected.

This was resolved by applying a configurable angle offset to all linear movement commands. The Flask server exposes `/config/angle?forward=<degrees>` as a runtime calibration endpoint — so the physical chassis orientation can be corrected without code changes. For the LUNA setup, a 180° offset was needed to align the SDK reference with the physical robot.

## Validation and Testing

Testing focused on:

- Confirming each command ID matched the correct spoken phrase
- Verifying the debounce logic prevented repeated triggers
- Checking that manual commands reliably interrupted autonomous behaviour
- Testing in different ambient noise conditions to confirm recognition stability
- Ensuring the robot stopped cleanly at the end of each timed movement
