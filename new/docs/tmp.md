# PlutoV2 Driver — Technical Overview & Comparison

---

## 1. RC Control — Dynamic `set_rc()`

PlutoV2 exposes a single `set_rc()` call that accepts any value for any channel.
Every frame the gesture engine computes a new value and passes it directly:

```python
def set_rc(self, roll=None, pitch=None, yaw=None, throttle=None,
           aux1=None, aux2=None, aux3=None, aux4=None):
    with self.lock:
        if roll is not None:     self.target_rc[0] = self._clamp(roll)
        if pitch is not None:    self.target_rc[1] = self._clamp(pitch)
        if throttle is not None: self.target_rc[2] = self._clamp(throttle)
        if yaw is not None:      self.target_rc[3] = self._clamp(yaw)
        # ...
        self.last_input_time = time.time()
```

Called from the gesture engine every frame with computed values:

```python
# From main_gcs.py
target_r = self.filters['roll'].apply(clamp_rc(1500 + (dr * C.SENS_ROLL)))
target_p = self.filters['pitch'].apply(clamp_rc(1500 + (dp * C.SENS_PITCH)))
target_t = self.filters['throttle'].apply(clamp_rc(self.last_throttle + (dt * C.SENS_THROTTLE)))
target_y = self.filters['yaw'].apply(clamp_rc(1500 + (dy * C.SENS_YAW)))

self.drone_worker.set_rc(roll=target_r, pitch=target_p, throttle=target_t, yaw=target_y)
```

> **vs original_pluto.py:** RC control is a set of hardcoded methods —
> `forward()` sets pitch to exactly 1600, `left()` sets roll to exactly 1200.
> No in-between values, no proportional control.
> ```python
> def forward(self):
>     self.rcPitch = 1600
> def left(self):
>     self.rcRoll = 1200
> ```

---

## 2. Non-Blocking I/O — Background Thread

All socket communication runs in a background thread. Nagle's algorithm is
disabled with `TCP_NODELAY` for minimum latency. The socket is set to non-blocking
so the I/O loop never stalls waiting for data:

```python
def connect(self):
    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.client.settimeout(2.0)
    self.client.connect((self.ip, self.port))
    # Disable Nagle's algorithm for low latency
    self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    self.client.setblocking(False)

    self.io_thread = threading.Thread(target=self._io_loop, daemon=True)
    self.io_thread.start()
```

The I/O loop runs at ~45Hz, draining the socket buffer non-blockingly each cycle:

```python
for _ in range(5):
    try:
        data = self.client.recv(2048)
        if data:
            buffer += data
        else:
            break
    except (BlockingIOError, socket.timeout):
        break   # nothing to read right now, move on
```

The gesture engine and UI **never touch the socket**. They only call `get_state()`:

```python
def get_state(self):
    """Returns a copy of the current shadow state."""
    with self.lock:
        return self.state.copy()
```

> **vs original_pluto.py:** Every telemetry call is a synchronous blocking recv
> with a 1 second timeout. Calling `get_roll()`, `get_pitch()`, `get_battery()`
> sequentially could block the gesture loop for multiple seconds on any WiFi hiccup.
> ```python
> def get_roll(self):
>     self.send_request_msp(self.create_packet_msp(MSP_ATTITUDE, []))
>     for _ in range(RETRY_COUNT):      # 3 retries
>         data = self.receive_packet()  # blocks up to 1 second per call
>         ...
> ```

---

## 3. Shadow State Dictionary

A single dictionary is kept continuously updated by the background thread.
All telemetry fields are available instantly — roll, pitch, yaw, altitude,
battery, IMU data — with one non-blocking read. No per-field network calls needed:

```python
# Initialised at startup
self.state = {
    'roll': 0.0,
    'pitch': 0.0,
    'yaw': 0.0,
    'height': 0,
    'battery': 0.0,
    'battery_percentage': 0,
    'rssi': 0,
    'amperage': 0,
    'rc': [1500] * 8,
    'acc': [0, 0, 0],
    'gyro': [0, 0, 0],
    'mag': [0, 0, 0],
    'last_update': 0,
    'watchdog_active': False
}
```

Updated by `_handle_payload()` as MSP responses arrive in the background:

```python
def _handle_payload(self, cmd, payload):
    with self.lock:
        if cmd == MSP_ATTITUDE and len(payload) >= 6:
            r, p, y = struct.unpack('<hhh', payload[:6])
            self.state['roll']  = r / 10.0
            self.state['pitch'] = p / 10.0
            self.state['yaw']   = y / 10.0
        elif cmd == MSP_ALTITUDE and len(payload) >= 6:
            h, v = struct.unpack('<ih', payload[:6])
            self.state['height'] = h
        elif cmd == MSP_RAW_IMU and len(payload) >= 18:
            imu_data = struct.unpack('<9h', payload[:18])
            self.state['acc']  = list(imu_data[0:3])
            self.state['gyro'] = list(imu_data[3:6])
            self.state['mag']  = list(imu_data[6:9])
        self.state['last_update'] = time.time()
```

The GCS reads all of this at 20Hz with a single non-blocking call:

```python
# From drone_worker.py
state = self.drone.get_state()
self.telemetry_signal.emit(state)
```

> **vs original_pluto.py:** No unified state. Every field requires its own
> separate blocking network call. To get a full snapshot:
> ```python
> roll    = drone.get_roll()      # blocking
> pitch   = drone.get_pitch()     # blocking
> yaw     = drone.get_yaw()       # blocking
> height  = drone.get_height()    # blocking
> battery = drone.get_battery()   # blocking
> ```

---

## 4. Safety Watchdog — 500ms Timeout

If no `set_rc()` call arrives for more than 500ms — camera dropped, gesture
pipeline crashed, webcam unplugged — the driver automatically resets all
movement channels to neutral hover. The drone holds position instead of
continuing on its last command:

```python
self.watchdog_timeout = 0.5  # 500ms

# Runs every I/O loop iteration
if now - self.last_input_time > self.watchdog_timeout:
    self.target_rc[0] = 1500  # roll   → neutral
    self.target_rc[1] = 1500  # pitch  → neutral
    self.target_rc[2] = 1500  # throttle → neutral
    self.target_rc[3] = 1500  # yaw    → neutral
    self.watchdog_active = True
    self.state['watchdog_active'] = True
```

`last_input_time` resets every time `set_rc()` is called, keeping the watchdog
from firing during normal operation:

```python
def set_rc(self, ...):
    with self.lock:
        # ... update values ...
        self.last_input_time = time.time()  # reset watchdog timer
```

When the watchdog fires, the GCS viewport shows a pulsing red warning border:

```python
# From widgets/viewport.py
if self.watchdog:
    glow = int(abs(math.sin(time.time() * 5)) * 180)
    painter.setPen(QPen(QColor(255, 0, 0, glow), 6))
    painter.drawRect(self.video_rect.adjusted(3, 3, -3, -3))
```

> **vs original_pluto.py:** No watchdog exists. If the control pipeline crashes
> mid-flight, the drone holds the last commanded RC values indefinitely.

---

## 5. Telemetry Health Check

Separate from the watchdog, PlutoV2 monitors the telemetry stream itself.
If no telemetry response arrives for more than 1 second, it flags the connection
as lost and logs a warning:

```python
self.telemetry_timeout = 1.0  # 1 second

if now - self.state['last_update'] > self.telemetry_timeout \
        and self.state['last_update'] > 0:
    if not self.telemetry_lost:
        self.logger.warning("Telemetry stream timed out.")
        self.telemetry_lost = True
else:
    self.telemetry_lost = False
```

> **vs original_pluto.py:** No telemetry loss detection.

---

## 6. MSP Packet Construction

PlutoV2 builds packets using `struct.pack` directly on bytes —
no intermediate hex string conversion:

```python
MSP_HEADER = b'$M<'   # bytes literal

def _create_packet(self, cmd, payload):
    size = len(payload)
    checksum = size ^ cmd
    for b in payload:
        checksum ^= b
    return MSP_HEADER + struct.pack('<BB', size, cmd) + payload + struct.pack('<B', checksum)

# RC packet example
rc_payload = struct.pack('<8H', *self.target_rc)
rc_packet  = self._create_packet(MSP_SET_RAW_RC, rc_payload)
self.client.sendall(rc_packet)
```

> **vs original_pluto.py:** Packets are built as hex strings then converted back
> to bytes with `bytes.fromhex()` — an unnecessary round-trip.
> ```python
> MSP_HEADER_IN = "244d3c"   # hex string
> bf += '{:02x}'.format(k & 0xFF)
> # ...
> self.client.send(bytes.fromhex(bf))
> ```

---

## Summary Table

| Feature | `plutov2.py` | `original_pluto.py` |
|---|---|---|
| RC control | Dynamic `set_rc()` — any value 1000–2000 | Static hardcoded values per method |
| I/O model | Async non-blocking (`setblocking(False)`) | Synchronous blocking (`settimeout(1.0)`) |
| Nagle's algorithm | Disabled (`TCP_NODELAY`) | Enabled (default) |
| Telemetry | Shadow state dict, updated by background thread | Separate blocking call per field |
| Telemetry rate | 45 Hz (all fields in one loop) | ~2 Hz (sequential per-field) |
| UI freeze risk | None — I/O fully isolated | High — any dropout blocks the thread |
| Safety watchdog | 500ms timeout → neutral hover | None |
| Telemetry loss detection | 1 second timeout → flag + log | None |
| Packet construction | `struct.pack` directly | Hex string concatenation + `bytes.fromhex()` |