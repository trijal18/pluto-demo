 # Pluto Drone Ground Control Station (GCS)

A modern, web-based ground control station for controlling Pluto drones with gesture recognition capabilities. This project provides a FastAPI backend with a real-time telemetry dashboard and optional gesture-based control using YOLO-based computer vision models.

## Features

###  Flight Control
- **Connection Management**: Connect/disconnect to Pluto drone
- **Arming System**: Arm and disarm the drone safely
- **Flight Operations**: Take off and land commands
- **Movement Control**: Forward, backward, left, and right directional commands

###  Real-Time Telemetry
- **Live Data Stream**: Real-time telemetry via WebSocket
- **Comprehensive Metrics**: Roll, pitch, yaw, altitude, battery voltage
- **RC Channel Monitoring**: 8-channel RC value visualization with progress bars
- **Interactive Charts**: Live updating charts for all telemetry parameters using Chart.js

###  Gesture Control
- **ASL Gesture Recognition**: Control drone using American Sign Language gestures (V, W, U, ThumbDown, Left, Right, Fist, Palm)
- **Numeric Gesture Control**: Simple numeric gestures (1-4) for basic commands
- **YOLO-based Detection**: Powered by Ultralytics YOLO models
- **Command Cooldown**: Prevents accidental repeated commands

###  Modern Web Interface
- **Responsive Design**: Works on desktop and tablet devices
- **Dark Theme**: Eye-friendly dark gradient interface
- **Visual Feedback**: Status indicators, notifications, and animated value updates
- **Live Charts**: Real-time data visualization with smooth animations

## Prerequisites

- **Python 3.8+**
- **Pluto Drone** (with `plutocontrol` library compatibility)
- **Web Camera** (for gesture control)
- **Operating System**: Windows, Linux, or macOS

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/trijal18/pluto-demo
cd pluto-demo
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Model Files

Ensure you have the gesture recognition model files:
- `models/asl.pt` - ASL gesture recognition model
- `models/numeric.pt` - Numeric gesture recognition model

These models should be YOLO-compatible PyTorch models trained on gesture recognition datasets.

## Usage

### Starting the Ground Control Station

Run the main GCS server:

```bash
python gcs.py
```

The server will start on `http://localhost:8000` by default. Open this URL in your web browser to access the control interface.

### Using the Web Interface

1. **Connect to Drone**: Click the "Connect" button to establish connection with your Pluto drone
2. **Arm the Drone**: Click "Arm" to activate the drone's flight systems
3. **Take Off**: Click "Take Off" to initiate flight
4. **Control Movement**: Use Forward, Backward, Left, and Right buttons to maneuver
5. **Monitor Telemetry**: Watch real-time data and charts in the dashboard
6. **Land and Disarm**: Use "Land" and "Disarm" buttons to safely conclude flight

### Gesture Control
<!-- 
#### ASL Gesture Control

Run the ASL gesture recognition script:

```bash
python gestures/gesture_asl.py
```

**Gesture Mappings:**
- `V` → Arm
- `W` → Disarm
- `U` → Take Off
- `ThumbDown` → Land
- `Left` → Move Left
- `Right` → Move Right
- `Fist` → Move Forward
- `Palm` → Move Backward -->

#### Numeric Gesture Control

Run the numeric gesture recognition script:

```bash
python gestures/gesture_numeric.py
```

**Gesture Mappings:**
- `1` → Arm
- `2` → Take Off
- `3` → Land
- `4` → Disarm

**Note**: Make sure the GCS server (`gcs.py`) is running before starting gesture control scripts. The gesture scripts connect to the GCS API to send commands.

## Project Structure

```
pluto-demo/
├── gcs.py                 # Main FastAPI GCS server
├── requirements.txt       # Python dependencies
├── gesture.log           # Gesture control logs
│
├── gestures/             # Gesture recognition scripts
│   ├── gesture_asl.py    # ASL gesture control
│   ├── gesture_numeric.py # Numeric gesture control
│   └── models/           # Gesture model files (alternate location)
│       ├── asl.pt
│       └── numeric.pt
│
├── models/               # Model files directory
│   ├── asl.pt           # ASL gesture recognition model
│   └── numeric.pt       # Numeric gesture recognition model
│
├── templates/           # HTML templates
│   └── index.html       # Main dashboard page
│
└── static/              # Static assets
    ├── script.js        # Frontend JavaScript (WebSocket, charts)
    └── styles.css       # Dashboard styling
```

## API Endpoints

### Connection
- `POST /connect` - Connect to drone
- `POST /disconnect` - Disconnect from drone

### Flight Control
- `POST /arm` - Arm the drone
- `POST /disarm` - Disarm the drone
- `POST /takeoff` - Command take off
- `POST /land` - Command landing

### Movement
- `POST /forward` - Move forward
- `POST /backward` - Move backward
- `POST /left` - Move left
- `POST /right` - Move right

### Telemetry
- `GET /` - Serve web dashboard
- `WebSocket /ws/telemetry` - Real-time telemetry stream

## Configuration

### GCS Server

The GCS server runs on `0.0.0.0:8000` by default. To change this, modify the `uvicorn.run()` call at the bottom of `gcs.py`.

### Gesture Control

Both gesture scripts can be configured by editing their respective files:

**ASL Gesture (`gesture_asl.py`):**
- `GCS_BASE`: Base URL of GCS server (default: `http://127.0.0.1:8000`)
- `COOLDOWN_SECONDS`: Time between repeated gesture commands (default: 3)
- `MODEL_PATH`: Path to ASL model file

**Numeric Gesture (`gesture_numeric.py`):**
- `GCS_BASE_URL`: Base URL of GCS server (default: `http://127.0.0.1:8000`)
- `COOLDOWN_SECONDS`: Time between repeated gesture commands (default: 3)
- `MODEL_PATH`: Path to numeric model file
- `LOG_FILE`: Path to log file (default: `gesture.log`)

## Safety Features

- **Safe Shutdown**: Automatically lands and disarms drone on server shutdown (Ctrl+C)
- **Signal Handling**: Graceful shutdown on SIGINT and SIGTERM
- **Error Handling**: Comprehensive error handling in all components
- **Command Cooldown**: Prevents accidental repeated commands in gesture mode

## Troubleshooting

### Connection Issues
- Ensure your Pluto drone is powered on and in range
- Check that the `plutocontrol` library is properly installed
- Verify network connectivity between your computer and the drone

### Gesture Recognition Not Working
- Ensure your webcam is connected and accessible
- Check that model files are in the correct location
- Verify the model file paths in the gesture scripts
- Make sure the GCS server is running before starting gesture control

### Web Interface Not Loading
- Check that the server is running on the expected port
- Verify all static files are in the correct directories
- Check browser console for JavaScript errors

### Telemetry Not Updating
- Ensure WebSocket connection is established (check browser console)
- Verify drone is connected via the Connect button
- Check that the drone is sending telemetry data

## Dependencies

Key dependencies include:
- **FastAPI**: Web framework for API and WebSocket support
- **plutocontrol**: Pluto drone control library
- **ultralytics**: YOLO model inference
- **opencv-python**: Camera access for gesture recognition
- **torch**: PyTorch for model inference
- **uvicorn**: ASGI server for FastAPI

See `requirements.txt` for the complete list of dependencies.



## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Gesture recognition powered by [Ultralytics YOLO](https://ultralytics.com/)
- Charts powered by [Chart.js](https://www.chartjs.org/)
- Drone control via [plutocontrol](https://github.com/DronaAviation/plutocontrol)



