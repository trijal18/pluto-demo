# PlutoV2 Library Documentation

The `PlutoV2` library is a robust, thread-safe Python interface for controlling Pluto drones using the MultiWii Serial Protocol (MSP). It is designed to handle communication asynchronously, ensuring low-latency drone control and high-frequency telemetry updates.

## Architecture

- **Communication**: Operates on a dedicated background I/O thread, ensuring that control packets and telemetry requests are sent at a steady ~45Hz rate.
- **Thread Safety**: Uses `threading.Lock()` to manage shared RC channel states and command buffers, preventing race conditions.
- **Shadow State**: Maintains an internal dictionary (`self.state`) representing the current drone state, populated by the asynchronous I/O thread.
- **Protocol Flexibility**: Supports both standard MSP responses (`0x3e`) and firmware-specific variants (e.g., `0x21`).

## Key Features

### 1. Telemetry Handling
The library automatically polls the drone for the following data and keeps `self.state` updated:
- **Orientation**: Roll, Pitch, Yaw (Degrees)
- **Position**: Altitude (Height)
- **Power**: Battery (Voltage/Percentage), Amperage (mA), RSSI
- **IMU**: Accelerometer (XYZ), Gyroscope (XYZ), Magnetometer (XYZ)
- **RC Channels**: Real-time feedback of current channel values (1000-2000 PWM)

### 2. Flight Commands
- **Arming/Disarming**: Safe sequences for motor management.
- **Takeoff/Land**: Automated flight modes utilizing MSP `CMD` packets.
- **Advanced Moves**: Built-in support for Flips (Front, Back, Left, Right).
- **Calibration**: Dedicated methods for Accelerometer and Magnetometer calibration.

## API Reference

### Connection & Control
- `connect()`: Starts the communication thread and establishes TCP link.
- `disconnect()`: Safely closes resources.
- `set_rc(roll, pitch, yaw, throttle, ...)`: Updates target RC channels (clamped 1000-2000).
- `arm()`/`disarm()`: Flight state controls.
- `takeoff()`/`land()`: Automated takeoff and landing sequence.

### Telemetry Access
- `get_state()`: Returns a snapshot (dictionary) of the latest drone telemetry.

### Diagnostics & Safety
- **Watchdog**: Automatically resets RC channels to hover if no input is received within the `watchdog_timeout` window (500ms).
- **Robust Parsing**: Includes strict length checks and checksum validation for every MSP packet, ensuring data integrity.
- **Multiple Header Support**: Automatically detects and handles non-standard MSP response headers from varying firmware versions.

---

## Usage Example

```python
from plutov2 import PlutoV2

drone = PlutoV2()
drone.connect()

# Arm and takeoff
drone.arm()
time.sleep(1)
drone.takeoff()

# Monitor state
while drone.connected:
    state = drone.get_state()
    print(f"Altitude: {state['height']}cm | Battery: {state['battery']}V")
    time.sleep(0.5)

drone.disconnect()
```
