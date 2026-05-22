# 🎛️ Raven GCS: Tactical Ground Control Station (GUI Deep-Dive)

This directory houses the **Raven Ground Control Station (GCS)**, a tactical graphical user interface (GUI) built with **PyQt6** and **pyqtgraph**. It provides pilots with live video feedback, a high-fidelity primary flight display (PFD) HUD, real-time sensor oscilloscopes, and hand-gesture telemetry mapping.

---

## 🏗️ Threading & Concurrency Model (Qt Signals & Slots)

To maintain a consistent, stutter-free **60 FPS** repaint rate on the user interface, all high-frequency blocking operations—such as webcam acquisition, MediaPipe tracking, and drone network communication—are delegated to independent worker threads (`QThread`). 

Data is bridged across thread boundaries using **Qt Signals and Slots**, preventing race conditions and UI freezing.

```
                  [ WEBCAM STREAM ]
                          │
                   (VisionWorker)  <-- QThread (60Hz)
                    │           │
   change_pixmap_signal       landmarks_signal
 (np.ndarray video frame)    (serialized hand landmarks)
          │                             │
          ▼                             ▼
   [ ViewportWidget ]           [ RavenGCS (Main Window) ]
          │                             │
          │                   Gesture Processing Engine
          │                     ├─ Decouple Left/Right
          │                     ├─ HandChassisStandard
          │                     └─ OneEuroFilter Smoothing
          │                             │
          │                       (DroneWorker)  <-- QThread (20Hz)
          │                        │         │
          │            telemetry_signal    set_rc / commands
          │           (state dict snapshot)  (TCP Socket Out)
          ▼                        │         │
[ HORIZON / HUD REPAINT ] <────────┴─────────┼─────────► [ Physical Drone ]
                                             ▼
                                    [ EngineeringConsole ]
                                      (pyqtgraph Scopes)
```

### 🛰️ The Signal Routing Interface
In `new/gcs/main_gcs.py`, threads are instantiated and their signal interfaces are linked during startup:
*   `vision_worker.change_pixmap_signal.connect(viewport.update_frame)`: Directly feeds the raw OpenCV video matrices to the canvas.
*   `vision_worker.landmarks_signal.connect(_on_landmarks_received)`: Passes serialized joint coordinates to the main gesture-mapping block.
*   `drone_worker.telemetry_signal.connect(viewport.update_hud)`: Passes current pitch, roll, yaw, height, and battery voltage to the aero HUD.
*   `drone_worker.telemetry_signal.connect(engineering.update_data)`: Passes accelerometer, gyroscope, magnetometer, and 8-channel RC arrays to the oscilloscope graphs.
*   `controls.manual_rc_changed.connect(_on_manual_rc)`: Forwards manual slider and button jog deck adjustments to the drone worker thread.

---

## 🎨 Custom Viewport Painting Math (`widgets/viewport.py`)

The `ViewportWidget` overrides `paintEvent` and uses `QPainter` to draw aviation-grade overlays directly on top of the live video stream. 

### 1. The Aero Horizon (Primary Flight Display)
The horizon gauge simulates a gyroscope indicator, dividing the sky (blue) and ground (brown) with a white level line.
*   **Rotation Math**: The horizon canvas is rotated around the gauge center $(C_x, C_y)$ by the negative roll value:
    $$\theta_{rotation} = -\theta_{roll}$$
*   **Pitch Pitch Offset**: The vertical divide line is shifted up or down along the pitch axis. The pixel translation offset is computed as:
    $$Y_{offset} = \theta_{pitch} \times 1.5 \text{ pixels}$$
*   **Clipping Path**: To prevent the colored sky/ground polygons from spilling across the viewport, a circular `QPainterPath` mask is applied:
    ```python
    path = QPainterPath()
    path.addEllipse(QRectF(x + 5, y + 5, size - 10, size - 10))
    painter.setClipPath(path)
    ```

### 2. The Compass Ribbon
Paints a horizontal magnetic heading scale at the top of the viewport.
*   **Yaw Translation**: Given the compass center coordinate $C_{x}$ and a yaw angle $\psi_{yaw}$:
    *   Iterates through angles from $\psi_{yaw} - 45^\circ$ to $\psi_{yaw} + 45^\circ$.
    *   Translates degrees to horizontal pixel coordinates:
        $$X_{tick} = C_{x} + (\theta_{deg} - \psi_{yaw}) \times 4 \text{ pixels}$$
    *   Annotates cardinal angles ($0^\circ \rightarrow \text{N}$, $90^\circ \rightarrow \text{E}$, $180^\circ \rightarrow \text{S}$, $270^\circ \rightarrow \text{W}$).
*   **Pointer Indicator**: A fixed red line is painted at $C_{x}$ to point to the current heading.

### 3. The Altitude Tape
Paints a sliding ruler on the left side of the screen displaying real-time height.
*   **Height Scale Translation**: Scales numeric altitudes (cm) to vertical coordinates:
    *   Iterates tick marks within $\pm 120\text{ cm}$ of the current height.
    *   Aligns ticks vertically relative to the screen center $C_{y}$:
        $$Y_{tick} = C_{y} + (H_{current} - H_{tick}) \times 2 \text{ pixels}$$
*   **Yellow Indicator Arrow**: A static polygon arrow points to the tape center, displaying the numerical value in high-contrast text.

---

## 🖖 Decoupled Gesture Dynamics (`utils/gestures.py`)

`HandChassisStandard` implements a sophisticated two-handed model to control flight:

```
    [ MIRRORED WEBCAM VIEW ]

    Left Side of Screen:                  Right Side of Screen:
    Webcam category: "Right"              Webcam category: "Left"
    Physical Hand: LEFT                   Physical Hand: RIGHT
    
         (Index Tip) 8                        (Middle Base) 9
              \                                     │
         Pinch \                                    │ Slope
                \                                   │
     (Thumb Tip) 4 ─── 0 (Wrist)                   0 (Wrist)
     
     * Clutch Toggle                      * Pitch Control
     * Takeoff (Thumbs Up)                * Roll Control
     * Land (Thumbs Down)                 * Yaw Control
     * Emergency Kill (Fist)
```

### 1. Left Hand: Clutch, Elevation, and Mission Triggers
*   **Pinch Clutch System**: The system checks the distance between Left Thumb Tip (4) and Index Tip (8):
    $$D_{pinch} = \sqrt{(X_4 - X_8)^2 + (Y_4 - Y_8)^2}$$
    If $D_{pinch} < 0.05$, the **Clutch is Engaged**, locking in neutral references and starting RC streams. Releasing the pinch immediately drops the clutch, disabling active outputs and forcing hover states.
*   **Decoupled Throttle**: Relative height delta of the Left Wrist (0) drives climbing/sinking:
    $$\Delta T = Y_{wrist\_neutral} - Y_{wrist\_current}$$
*   **Fist Kill Switch**: Measures the average distance of finger tips (8, 12, 16, 20) to Wrist (0). If $<0.12$, it triggers a tight-fist condition, immediately disarming the drone motors.
*   **Thumbs Up/Down**: Detects relative finger heights to trigger discrete Takeoff (`CMD_TAKE_OFF`) and Landing (`CMD_LAND`) routines.

### 2. Right Hand: The Flight Joystick
When the Clutch is engaged, the Right hand functions as a virtual joystick:
*   **Pitch Delta**: Measures the vertical slope from Wrist (0) to Middle Finger Base (9):
    $$Slope_{pitch} = Y_{wrist} - Y_{middle\_base}$$
    $$\Delta P = Slope_{pitch} - Slope_{pitch\_neutral}$$
*   **Roll Delta**: Measures the tilt difference between Pinky Tip (20) and Thumb Tip (4):
    $$Tilt_{roll} = Y_{pinky} - Y_{thumb}$$
    $$\Delta R = Tilt_{roll} - Tilt_{roll\_neutral}$$
*   **Yaw Delta**: Measures depth rotation using z-axis coordinates of Thumb (4) and Pinky (20):
    $$Rotation_{yaw} = Z_{thumb} - Z_{pinky}$$
    $$\Delta Y = Rotation_{yaw} - Rotation_{yaw\_neutral}$$

---

## 📈 Signal Filtering & Smoothing Tuning (`utils/filters.py`)

Direct skeletal joint inputs from MediaPipe contain pixel noise and tracking jitter. To solve this, inputs are routed through an adaptive **OneEuroFilter** before being packed into RC signals.

### OneEuroFilter Parameters
*   **Min Cutoff (`MC = 1.0`)**: The minimum frequency cutoff. Higher values reduce lag but allow slight jitter when the hand is still. $1.0$ is optimized for responsive hover holds.
*   **Beta (`BETA = 0.02`)**: Speed coefficient. During fast movements, the cutoff frequency increases proportionally to velocity, eliminating input lag.
*   **Deadzone (`DEADZONE = 0.05`)**: Prevents micro-movements of the pilot's hands from causing drone drift. Any delta value within $\pm 5\%$ of the neutral coordinate is clamped to $0.0$.

---

## ⌨️ Manual Control & Safety Key Bindings

Manual pilot controls can be accessed via keyboard overrides or the graphical jog panel. Pressing any movement key immediately switches the flight state into **`MANUAL` mode**.

| Key Action | Assigned Keyboard Key | Mapped Channel Delta |
| :--- | :--- | :--- |
| **Pitch Up / Down** | `W` / `S` | $\pm 30$ PWM Pitch units |
| **Roll Left / Right** | `A` / `D` | $\pm 30$ PWM Roll units |
| **Yaw CCW / CW** | `Left Arrow` / `Right Arrow` | $\pm 50$ PWM Yaw units |
| **Throttle Up / Down** | `Up Arrow` / `Down Arrow` | $\pm 50$ PWM Throttle units |
| **Emergency Disarm** | `Spacebar` | Immediate Disarm Pulse |
