# PlutoV2 vs. Original Pluto Library: Technical Comparison

This document provides a technical comparison between the original `plutocontrol` library and the newly architected `PlutoV2` library.

## 1. Overview
The `PlutoV2` library is a complete re-architecting of the original `Pluto` control library. While the original was designed for simple script-based interaction, `PlutoV2` is optimized for integration into modern, asynchronous GUI applications (like the Raven GCS) where real-time, low-latency telemetry and thread-safe control are mandatory.

## 2. Key Architectural Differences

| Feature | Original Pluto Library | PlutoV2 Library |
| :--- | :--- | :--- |
| **Telemetry Access** | Synchronous (Poll & Wait). | Asynchronous Shadow State (non-blocking). |
| **Data Integrity** | Prone to `0.0` values on timeout. | Persistent (retains last known good data). |
| **Parsing** | Basic/Unsafe (no length checks). | Robust (checksums + strict length validation). |
| **Headers** | Rigid (expects only `$M>`). | Adaptive (supports `$M>` and `$M!`). |
| **Concurrency** | Shared locks for *everything*. | Lock-protected shared state; async I/O. |
| **Logging** | Global side-effects (`logging.basicConfig`). | Scoped, library-specific logging. |

## 3. How PlutoV2 Works

### The Asynchronous I/O Loop
Unlike the original library that used a blocking `write_function`, `PlutoV2` uses a unified `_io_loop` running at ~45Hz. This loop handles:
1.  **Safety Watchdog**: Automatically resets RC values to neutral if no commands are received (failsafe).
2.  **Telemetry Requesting**: Iteratively requests specific MSP telemetry slices (IMU, RC, Analog) to keep the data stream balanced.
3.  **Buffer Draining**: Drains the socket buffer into a byte stream, ensuring no packets are missed due to OS-level buffering.

### The Shadow State
`PlutoV2` stores the drone's status in a thread-safe `self.state` dictionary. 
- **Benefit**: The UI thread can call `get_state()` at any time without blocking the I/O thread. The UI always has the most recent telemetry, even if a specific packet is dropped.

## 4. Key Design Principles

1.  **Robustness over Simplicity**: Where the original library would return an incomplete/erroneous value, `PlutoV2` uses strict length checks (`len(payload) >= X`) and checksum validation to ensure that only 100% valid MSP packets update the internal state.
2.  **Safety-First**: The internal watchdog triggers a failsafe (throttle/RC reset) if the main application stops sending commands.
3.  **Firmware Agnosticism**: The inclusion of `MSP_RESPONSE_HEADERS` allows it to communicate with firmware versions that might use non-standard response headers (e.g., `0x21` vs `0x3e`), preventing the sync failures common in older libraries.

## 5. Usage Guidelines

### Initialization
```python
from plutov2 import PlutoV2
drone = PlutoV2(ip='192.168.4.1', port=23)
drone.connect()
```

### Telemetry Access
Access data via the `get_state()` method.
```python
state = drone.get_state()
print(f"Roll: {state['roll']}, Battery: {state['battery']}V")
```

### Command Control
All commands are thread-safe and non-blocking:
```python
drone.arm()
time.sleep(1)
drone.takeoff()
drone.set_rc(throttle=1500) # Centered
drone.flip(CMD_FRONT_FLIP)
```

## 6. Migration Notes
- **Method Names**: Method signatures for `arm()`, `disarm()`, and `set_rc()` have been improved to ensure the drone is in a safe state before applying changes.
- **State Structure**: Instead of individual variables like `self.rcRoll`, use `state['rc'][0]`. All sensors are now accessible under the `state` dictionary, providing a unified interface for all data points.
