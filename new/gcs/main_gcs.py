import sys
import os
import time
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel
from PyQt6.QtCore import Qt, QTimer

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.filters import LowPassFilter, OneEuroFilter
from utils.gestures import HandChassis, HandChassisAdvanced, HandChassisStandard
import utils.constants as C

from workers.vision_worker import VisionWorker
from workers.drone_worker import DroneWorker
from widgets.viewport import ViewportWidget
from widgets.target_display import TargetDisplay
from widgets.telemetry import TelemetryRack
from widgets.oscilloscope import OscilloscopeWidget
from widgets.controls import ControlDeck
from widgets.engineering import EngineeringConsole
from widgets.pfd import HorizonWidget, CompassWidget

def clamp_rc(val):
    return max(1000, min(2000, int(val)))

class RavenGCS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAVEN GCS - PLUTO DRONE COMMAND")
        self.resize(1350, 900)
        
        # Load Stylesheet
        style_path = os.path.join(os.path.dirname(__file__), "assets", "styles", "industrial.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        else:
            self.setStyleSheet("background-color: #0a0a0a; color: #0ff;")

        # 1. Core Logic Components
        self.chassis = HandChassisStandard(clutch_threshold=C.CLUTCH_THRESHOLD, deadzone=C.DEADZONE)
        self.filters = {
            'roll': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'pitch': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'yaw': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'throttle': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA, initial_value=1000)
        }
        self.last_throttle = 1000
        self.mode = "STANDBY" # STANDBY, GESTURE, MANUAL
        self.manual_lock_timer = QTimer()
        self.manual_lock_timer.setSingleShot(True)
        self.manual_lock_timer.timeout.connect(self._release_manual_lock)

        # 2. UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Main Splitter (Left: Monitor Stack | Right: Control Stack)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Stack (Monitor)
        self.monitor_stack = QWidget()
        self.monitor_layout = QVBoxLayout(self.monitor_stack)
        
        # Monitor Top (Viewport + PFD)
        self.mon_top = QWidget()
        self.mon_top_layout = QHBoxLayout(self.mon_top)
        self.mon_top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.pfd_stack = QWidget()
        self.pfd_stack.setFixedWidth(220)
        self.pfd_layout = QVBoxLayout(self.pfd_stack)
        self.horizon = HorizonWidget()
        self.compass = CompassWidget()
        self.lbl_alt = QLabel("ALT: 0 cm")
        self.lbl_alt.setStyleSheet("color: #0ff; font-family: Consolas; font-size: 16px; font-weight: bold; padding: 10px;")
        self.lbl_alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pfd_layout.addWidget(self.horizon)
        self.pfd_layout.addWidget(self.compass)
        self.pfd_layout.addWidget(self.lbl_alt)
        self.pfd_layout.addStretch()
        
        self.viewport = ViewportWidget()
        self.mon_top_layout.addWidget(self.pfd_stack)
        self.mon_top_layout.addWidget(self.viewport, 1)
        
        self.target_display = TargetDisplay()
        self.oscilloscope = OscilloscopeWidget()
        self.engineering = EngineeringConsole()
        
        self.monitor_layout.addWidget(self.mon_top, 8) 
        self.monitor_layout.addWidget(self.target_display, 0)
        self.monitor_layout.addWidget(self.oscilloscope, 2)
        self.monitor_layout.addWidget(self.engineering, 2)
        
        # Right Stack (Control)
        self.control_stack = QWidget()
        self.control_stack.setMaximumWidth(300)
        self.control_layout = QVBoxLayout(self.control_stack)
        self.telemetry = TelemetryRack()
        self.controls = ControlDeck()
        self.control_layout.addWidget(self.telemetry, 1)
        self.control_layout.addWidget(self.controls, 2)

        self.h_splitter.addWidget(self.monitor_stack)
        self.h_splitter.addWidget(self.control_stack)
        
        self.h_splitter.setStretchFactor(0, 3)
        self.h_splitter.setStretchFactor(1, 1)
        
        self.main_layout.addWidget(self.h_splitter)

        # 3. Workers Setup
        self.vision_worker = VisionWorker()
        self.drone_worker = DroneWorker()

        # 4. Signal Connections
        # Vision -> UI
        self.vision_worker.change_pixmap_signal.connect(self.viewport.update_frame)
        self.vision_worker.landmarks_signal.connect(self._on_landmarks_received)
        
        # Drone -> UI
        self.drone_worker.telemetry_signal.connect(self.telemetry.update_telemetry)
        self.drone_worker.telemetry_signal.connect(self.oscilloscope.update_data)
        self.drone_worker.telemetry_signal.connect(self.engineering.update_data)
        self.drone_worker.telemetry_signal.connect(self._on_telemetry_received)
        self.drone_worker.connection_signal.connect(self._on_connection_update)

        # UI -> Drone Commands
        self.controls.connect_clicked.connect(self.drone_worker.connect_drone)
        self.controls.arm_clicked.connect(self.drone_worker.arm)
        self.controls.disarm_clicked.connect(self.drone_worker.disarm)
        self.controls.takeoff_clicked.connect(self.drone_worker.takeoff)
        self.controls.land_clicked.connect(self.drone_worker.land)
        self.controls.calibrate_clicked.connect(self.drone_worker.calibrate)
        self.controls.calibrate_mag_clicked.connect(self.drone_worker.calibrate_mag)
        self.controls.save_config_clicked.connect(self.drone_worker.save_config)
        self.controls.flip_clicked.connect(self.drone_worker.flip)
        self.controls.manual_rc_changed.connect(self._on_manual_rc_input)

        # Start Workers
        self.vision_worker.start()
        self.drone_worker.start()

    def _on_telemetry_received(self, state):
        # Update PFD
        self.horizon.set_orientation(state.get('roll', 0.0), state.get('pitch', 0.0))
        self.compass.set_yaw(state.get('yaw', 0.0))
        self.lbl_alt.setText(f"ALT: {state.get('height', 0)} cm")

    def _on_landmarks_received(self, landmarks, handedness):
        self.viewport.update_landmarks(landmarks, handedness)
        
        if self.mode == "MANUAL":
            return 

        if landmarks and handedness:
            # 1. Identify Hands (Mirrored View: Physical Right = Left, Physical Left = Right)
            flight_idx = -1 # Physical Right Hand
            clutch_idx = -1 # Physical Left Hand
            
            for i, h in enumerate(handedness):
                if h[0].category_name == "Left": flight_idx = i
                elif h[0].category_name == "Right": clutch_idx = i

            # 2. Check for Discrete Gestures (Fist for Emergency Stop)
            if flight_idx != -1:
                if self.chassis.detect_stop(landmarks[flight_idx]):
                    self.drone_worker.disarm()
                    self.viewport.set_mode("EMERGENCY STOP")
                    return

            # 3. Handle Clutch & Decoupled Control
            clutch_active = False
            if clutch_idx != -1:
                clutch_active = self.chassis.get_clutch_state([landmarks[clutch_idx]], [[handedness[clutch_idx][0]]])
                
                # Takeoff / Land from Clutch Hand
                if self.chassis.detect_takeoff(landmarks[clutch_idx]):
                    self.drone_worker.takeoff()
                elif self.chassis.detect_land(landmarks[clutch_idx]):
                    self.drone_worker.land()

            self.viewport.set_clutch(clutch_active)
            
            if flight_idx != -1 and clutch_active and clutch_idx != -1:
                self.mode = "GESTURE"
                self.viewport.set_mode(self.mode)
                
                flight_lm = landmarks[flight_idx]
                clutch_lm = landmarks[clutch_idx]

                if not self.chassis.is_engaged:
                    self.chassis.set_neutral(flight_lm, clutch_lm)
                
                dr, dp, dt, dy = self.chassis.get_decoupled_controls(flight_lm, clutch_lm)
                
                # Scale to RC
                target_r = clamp_rc(1500 + (dr * C.SENS_ROLL))
                target_p = clamp_rc(1500 + (dp * C.SENS_PITCH))
                target_t = clamp_rc(self.last_throttle + (dt * C.SENS_THROTTLE))
                target_y = clamp_rc(1500 + (dy * C.SENS_YAW))
                
                # Apply Smoothing
                target_r = self.filters['roll'].apply(target_r)
                target_p = self.filters['pitch'].apply(target_p)
                target_t = self.filters['throttle'].apply(target_t)
                target_y = self.filters['yaw'].apply(target_y)
                
                self.drone_worker.set_rc(roll=target_r, pitch=target_p, throttle=target_t, yaw=target_y)
                self.last_throttle = target_t
                self.target_display.update_targets(target_r, target_p, target_t, target_y)
            else:
                self.chassis.is_engaged = False
                if self.mode == "GESTURE":
                    self.mode = "STANDBY"
                    self.viewport.set_mode(self.mode)
                    self.drone_worker.set_rc(roll=1500, pitch=1500, yaw=1500, throttle=self.last_throttle)
                    self.target_display.update_targets(1500, 1500, self.last_throttle, 1500)
        else:
            self.viewport.set_clutch(False)
            if self.mode == "GESTURE":
                self.mode = "STANDBY"
                self.viewport.set_mode(self.mode)
                self.target_display.update_targets(1500, 1500, self.last_throttle, 1500)

    def _on_manual_rc_input(self, r, p, t, y):
        self.mode = "MANUAL"
        self.viewport.set_mode(self.mode)
        self.viewport.set_clutch(False)
        
        # Lock out gestures for 2 seconds after manual input
        self.manual_lock_timer.start(2000)
        
        self.drone_worker.set_rc(roll=r, pitch=p, throttle=t, yaw=y)
        self.last_throttle = t
        self.target_display.update_targets(r, p, t, y)
        
        # Reset filters to manual value to prevent jumps
        self.filters['throttle'].reset(t)
        self.filters['roll'].reset(r)
        self.filters['pitch'].reset(p)
        self.filters['yaw'].reset(y)

    def _release_manual_lock(self):
        if self.mode == "MANUAL":
            self.mode = "STANDBY"
            self.viewport.set_mode(self.mode)

    def _on_connection_update(self, connected):
        status = "CONNECTED" if connected else "DISCONNECTED"
        self.viewport.set_mode(f"{self.mode} | {status}")

    def keyPressEvent(self, event):
        # Keyboard RC Mapping
        # WASD: Pitch/Roll
        # Arrows: Throttle/Yaw
        
        # Step sizes
        step_rp = 30
        step_ty = 50
        
        r, p, t, y = self.filters['roll'].value, self.filters['pitch'].value, self.filters['throttle'].value, self.filters['yaw'].value
        
        key = event.key()
        if key == Qt.Key.Key_W: p = clamp_rc(p + step_rp)
        elif key == Qt.Key.Key_S: p = clamp_rc(p - step_rp)
        elif key == Qt.Key.Key_A: r = clamp_rc(r - step_rp)
        elif key == Qt.Key.Key_D: r = clamp_rc(r + step_rp)
        elif key == Qt.Key.Key_Up: t = clamp_rc(t + step_ty)
        elif key == Qt.Key.Key_Down: t = clamp_rc(t - step_ty)
        elif key == Qt.Key.Key_Left: y = clamp_rc(y - step_ty)
        elif key == Qt.Key.Key_Right: y = clamp_rc(y + step_ty)
        elif key == Qt.Key.Key_Space: # Reset / Emergency Stop
            r, p, y = 1500, 1500, 1500
            self.drone_worker.set_rc(roll=1500, pitch=1500, yaw=1500)
        elif key == Qt.Key.Key_Shift: self.drone_worker.arm()
        elif key == Qt.Key.Key_Control: self.drone_worker.disarm()
        elif key == Qt.Key.Key_T: self.drone_worker.takeoff()
        elif key == Qt.Key.Key_L: self.drone_worker.land()
        elif key == Qt.Key.Key_C: self.drone_worker.connect_drone()
        
        if key in [Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D, Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            self._on_manual_rc_input(r, p, t, y)

    def closeEvent(self, event):
        self.vision_worker.stop()
        self.drone_worker.stop()
        event.accept()

if __name__ == "__main__":
    try:
        print("\n" + "="*40)
        print(" INITIALIZING RAVEN GCS ")
        print("="*40)
        
        app = QApplication(sys.argv)
        print("[1/3] Qt Application Initialized.")
        
        window = RavenGCS()
        print("[2/3] UI Components Loaded.")
        
        window.show()
        print("[3/3] Displaying Interface. System Ready.")
        print("="*40 + "\n")
        
        # Ensure focus for keyboard controls
        window.central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        window.central_widget.setFocus()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"\n[FATAL ERROR] GCS Failed to start: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
