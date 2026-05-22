import sys
import os
import time
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer

# Add paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.filters import OneEuroFilter
from utils.gestures import HandChassisStandard
from utils.gestures_simple import SimpleOneHandController
import utils.constants as C

from workers.vision_worker import VisionWorker
from workers.drone_worker import DroneWorker
from widgets.viewport import ViewportWidget
from widgets.controls import ControlDeck
from widgets.engineering import EngineeringConsole

def clamp_rc(val):
    return max(1000, min(2000, int(val)))

class RavenGCS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLUTO GCS - COMMAND HUB")
        self.resize(1400, 950)
        self.setStyleSheet("background-color: #050505; color: #0ff; font-family: Consolas;")

        # 1. Logic
        self.chassis = HandChassisStandard(clutch_threshold=C.CLUTCH_THRESHOLD, deadzone=C.DEADZONE)
        self.simple_chassis = SimpleOneHandController()
        self.gesture_mode = "CONTINUOUS"
        self.filters = {
            'roll': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'pitch': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'yaw': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
            'throttle': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA, initial_value=1000)
        }
        self.last_throttle = 1000
        self.mode = "STANDBY"
        self.prev_discrete_gesture = ""
        
        # 2. UI - Tactical Header
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.header = QFrame()
        self.header.setFixedHeight(40)
        self.header.setStyleSheet("background: #0a0a0a; border-bottom: 1px solid #333;")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.lbl_logo = QLabel("PLUTO GCS v2.4")
        self.lbl_logo.setStyleSheet("font-weight: bold; color: #0ff; font-size: 15px;")
        
        self.lbl_hands = QLabel("HANDS: L-NONE R-NONE")
        self.lbl_clutch = QLabel("CLUTCH: DISENGAGED")
        self.lbl_latency = QLabel("LATENCY: -- ms")
        self.lbl_mode = QLabel("MODE: STANDBY")
        
        for lbl in [self.lbl_hands, self.lbl_clutch, self.lbl_latency, self.lbl_mode]:
            lbl.setStyleSheet("color: #00ffcc; font-size: 11px; font-weight: bold;")

        self.header_layout.addWidget(self.lbl_logo)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.lbl_hands)
        self.header_layout.addSpacing(40)
        self.header_layout.addWidget(self.lbl_clutch)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.lbl_latency)
        self.header_layout.addSpacing(40)
        self.header_layout.addWidget(self.lbl_mode)
        
        self.main_layout.addWidget(self.header)

        # 3. UI - Body (Viewport + Sidebar)
        self.body_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.top_container = QWidget()
        self.top_h_layout = QHBoxLayout(self.top_container)
        self.top_h_layout.setContentsMargins(0, 0, 0, 0)
        self.top_h_layout.setSpacing(0)
        
        self.viewport = ViewportWidget()
        self.controls = ControlDeck()
        
        # Add viewport first with stretch=1 to fill the left side
        self.top_h_layout.addWidget(self.viewport, 1)
        # Add controls with stretch=0 to keep it pinned to the right of the video
        self.top_h_layout.addWidget(self.controls, 0)
        
        # 4. UI - Engineering Pit
        self.engineering = EngineeringConsole()
        
        self.body_splitter.addWidget(self.top_container)
        self.body_splitter.addWidget(self.engineering)
        self.body_splitter.setStretchFactor(0, 3) # 75%
        self.body_splitter.setStretchFactor(1, 1) # 25%
        
        self.main_layout.addWidget(self.body_splitter)

        # 5. Workers
        self.vision_worker = VisionWorker()
        self.drone_worker = DroneWorker()

        # 6. Connections
        self.vision_worker.change_pixmap_signal.connect(self.viewport.update_frame)
        self.vision_worker.landmarks_signal.connect(self._on_landmarks_received)
        
        self.drone_worker.telemetry_signal.connect(self.viewport.update_hud)
        self.drone_worker.telemetry_signal.connect(self.engineering.update_data)
        self.drone_worker.telemetry_signal.connect(self._update_header)
        self.drone_worker.connection_signal.connect(self._on_conn)

        self.controls.connect_clicked.connect(self.drone_worker.connect_drone)
        self.controls.arm_clicked.connect(self.drone_worker.arm)
        self.controls.disarm_clicked.connect(self.drone_worker.disarm)
        self.controls.takeoff_clicked.connect(self.drone_worker.takeoff)
        self.controls.land_clicked.connect(self.drone_worker.land)
        self.controls.cal_acc_clicked.connect(self.drone_worker.calibrate)
        self.controls.cal_mag_clicked.connect(self.drone_worker.calibrate_mag)
        self.controls.manual_rc_changed.connect(self._on_manual_rc)
        self.controls.gesture_mode_changed.connect(self._on_gesture_mode_changed)

        self.vision_worker.start()
        self.drone_worker.start()

    def _on_landmarks_received(self, landmarks, handedness):
        self.viewport.update_landmarks(landmarks, handedness)
        
        l_status = "NONE"
        r_status = "NONE"
        flight_idx = -1
        clutch_idx = -1
        
        if landmarks and handedness:
            for i, h in enumerate(handedness):
                if h[0].category_name == "Left": 
                    flight_idx = i
                    r_status = "OK"
                elif h[0].category_name == "Right": 
                    clutch_idx = i
                    l_status = "OK"
        
        self.lbl_hands.setText(f"HANDS: L-{l_status} R-{r_status}")
        self.lbl_hands.setStyleSheet(f"color: {'#0f0' if (l_status=='OK' or r_status=='OK') else '#777'}; font-size: 11px; font-weight: bold;")
        
        if self.mode == "MANUAL": return

        if self.gesture_mode == "DISCRETE":
            self.viewport.set_clutch(False)
            self.lbl_clutch.setText("CLUTCH: N/A")
            self.lbl_clutch.setStyleSheet("color: #555; font-size: 11px; font-weight: bold;")
            
            if landmarks and handedness:
                # Use the first detected hand
                hand_lm = landmarks[0]
                hand_label = handedness[0][0].category_name  # "Left" or "Right"
                
                # Update status for hands
                if hand_label == "Left":
                    r_status = "OK"
                else:
                    l_status = "OK"
                self.lbl_hands.setText(f"HANDS: L-{l_status} R-{r_status}")
                self.lbl_hands.setStyleSheet(f"color: #0f0; font-size: 11px; font-weight: bold;")
                
                command, rc_vals = self.simple_chassis.get_controls(hand_lm, hand_label)
                self.viewport.set_detected_gesture(command)
                
                # Extract target RC values
                target_r, target_p, target_t, target_y = rc_vals
                
                # Check for rising edge transitions
                if command == "ARM_TAKEOFF" and self.prev_discrete_gesture != "ARM_TAKEOFF":
                    self.drone_worker.takeoff()
                elif command == "DISARM" and self.prev_discrete_gesture != "DISARM":
                    self.drone_worker.disarm()
                else:
                    # Apply 1 Euro filter for smooth transmission
                    filtered_r = self.filters['roll'].apply(clamp_rc(target_r))
                    filtered_p = self.filters['pitch'].apply(clamp_rc(target_p))
                    filtered_t = self.filters['throttle'].apply(clamp_rc(target_t))
                    filtered_y = self.filters['yaw'].apply(clamp_rc(target_y))
                    
                    self.drone_worker.set_rc(roll=filtered_r, pitch=filtered_p, throttle=filtered_t, yaw=filtered_y)
                    self.last_throttle = filtered_t
                    self.viewport.update_targets(filtered_r, filtered_p, filtered_t, filtered_y)
                
                self.prev_discrete_gesture = command
                self.mode = "GESTURE"
            else:
                self.viewport.set_detected_gesture("")
                self.prev_discrete_gesture = ""
                # Default to neutral hover
                filtered_r = self.filters['roll'].apply(1500)
                filtered_p = self.filters['pitch'].apply(1500)
                filtered_t = self.filters['throttle'].apply(self.last_throttle)
                filtered_y = self.filters['yaw'].apply(1500)
                
                self.drone_worker.set_rc(roll=filtered_r, pitch=filtered_p, throttle=filtered_t, yaw=filtered_y)
                self.viewport.update_targets(filtered_r, filtered_p, filtered_t, filtered_y)
                
                self.lbl_hands.setText("HANDS: L-NONE R-NONE")
                self.lbl_hands.setStyleSheet("color: #777; font-size: 11px; font-weight: bold;")
                if self.mode == "GESTURE":
                    self.mode = "STANDBY"
            
            self.lbl_mode.setText(f"MODE: {self.mode}")
            return

        clutch_active = False
        if clutch_idx != -1:
            clutch_active = self.chassis.get_clutch_state([landmarks[clutch_idx]], [[handedness[clutch_idx][0]]])
            if self.chassis.detect_takeoff(landmarks[clutch_idx]): self.drone_worker.takeoff()
            elif self.chassis.detect_land(landmarks[clutch_idx]): self.drone_worker.land()

        self.viewport.set_clutch(clutch_active)
        self.lbl_clutch.setText(f"CLUTCH: {'ENGAGED' if clutch_active else 'DISENGAGED'}")
        self.lbl_clutch.setStyleSheet(f"color: {'#0f0' if clutch_active else '#555'}; font-size: 11px; font-weight: bold;")

        if flight_idx != -1 and clutch_active and clutch_idx != -1:
            self.mode = "GESTURE"
            flight_lm = landmarks[flight_idx]
            clutch_lm = landmarks[clutch_idx]

            if not self.chassis.is_engaged: self.chassis.set_neutral(flight_lm, clutch_lm)
            
            dr, dp, dt, dy = self.chassis.get_decoupled_controls(flight_lm, clutch_lm)
            target_r = self.filters['roll'].apply(clamp_rc(1500 + (dr * C.SENS_ROLL)))
            target_p = self.filters['pitch'].apply(clamp_rc(1500 + (dp * C.SENS_PITCH)))
            target_t = self.filters['throttle'].apply(clamp_rc(self.last_throttle + (dt * C.SENS_THROTTLE)))
            target_y = self.filters['yaw'].apply(clamp_rc(1500 + (dy * C.SENS_YAW)))
            
            self.drone_worker.set_rc(roll=target_r, pitch=target_p, throttle=target_t, yaw=target_y)
            self.last_throttle = target_t
            self.viewport.update_targets(target_r, target_p, target_t, target_y)
        else:
            self.chassis.is_engaged = False
            if self.mode == "GESTURE":
                self.mode = "STANDBY"
                self.drone_worker.set_rc(roll=1500, pitch=1500, yaw=1500, throttle=self.last_throttle)
                self.viewport.update_targets(1500, 1500, self.last_throttle, 1500)
        
        self.lbl_mode.setText(f"MODE: {self.mode}")

    def _on_gesture_mode_changed(self, mode_str):
        if "Discrete" in mode_str:
            self.gesture_mode = "DISCRETE"
        else:
            self.gesture_mode = "CONTINUOUS"
        self.viewport.set_gesture_mode(self.gesture_mode)
        self.viewport.set_detected_gesture("")
        self.prev_discrete_gesture = ""
        # Reset RC targets to hover/neutral values for safety
        self.drone_worker.set_rc(roll=1500, pitch=1500, throttle=self.last_throttle, yaw=1500)
        self.viewport.update_targets(1500, 1500, self.last_throttle, 1500)

    def _update_header(self, state):
        last_upd = state.get('last_update', 0)
        if last_upd > 0:
            lat = int((time.time() - last_upd) * 1000)
            self.lbl_latency.setText(f"LATENCY: {lat} ms")
            if lat > 200: self.lbl_latency.setStyleSheet("color: #f00; font-size: 11px; font-weight: bold;")
            else: self.lbl_latency.setStyleSheet("color: #0f0; font-size: 11px; font-weight: bold;")

    def _on_manual_rc(self, r, p, t, y):
        self.mode = "MANUAL"
        self.lbl_mode.setText(f"MODE: {self.mode}")
        self.drone_worker.set_rc(roll=r, pitch=p, throttle=t, yaw=y)
        self.last_throttle = t
        self.viewport.update_targets(r, p, t, y)
        self.viewport.set_clutch(False)

    def _on_conn(self, connected):
        self.viewport.set_mode("CONNECTED" if connected else "DISCONNECTED")

    def keyPressEvent(self, event):
        key = event.key()
        r, p, t, y = self.filters['roll'].value, self.filters['pitch'].value, self.filters['throttle'].value, self.filters['yaw'].value
        
        if key == Qt.Key.Key_W: p = clamp_rc(p + 30)
        elif key == Qt.Key.Key_S: p = clamp_rc(p - 30)
        elif key == Qt.Key.Key_A: r = clamp_rc(r - 30)
        elif key == Qt.Key.Key_D: r = clamp_rc(r + 30)
        elif key == Qt.Key.Key_Up: t = clamp_rc(t + 50)
        elif key == Qt.Key.Key_Down: t = clamp_rc(t - 50)
        elif key == Qt.Key.Key_Left: y = clamp_rc(y - 50)
        elif key == Qt.Key.Key_Right: y = clamp_rc(y + 50)
        elif key == Qt.Key.Key_Space: 
            self.drone_worker.disarm()
            return
        
        if key in [Qt.Key.Key_W, Qt.Key.Key_S, Qt.Key.Key_A, Qt.Key.Key_D, Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            self._on_manual_rc(r, p, t, y)

    def closeEvent(self, event):
        self.vision_worker.stop()
        self.drone_worker.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RavenGCS()
    window.show()
    sys.exit(app.exec())
