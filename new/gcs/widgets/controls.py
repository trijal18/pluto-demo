from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QGridLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class ControlDeck(QWidget):
    # Signals to be connected to DroneWorker
    connect_clicked = pyqtSignal()
    arm_clicked = pyqtSignal()
    disarm_clicked = pyqtSignal()
    takeoff_clicked = pyqtSignal()
    land_clicked = pyqtSignal()
    calibrate_clicked = pyqtSignal()
    calibrate_mag_clicked = pyqtSignal()
    save_config_clicked = pyqtSignal()
    flip_clicked = pyqtSignal(int) # direction
    
    manual_rc_changed = pyqtSignal(int, int, int, int) # R, P, T, Y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        
        # 1. Safety & System Section
        self.safety_group = QVBoxLayout()
        self.lbl_safety = QLabel("--- SAFETY & SYSTEM ---")
        self.lbl_safety.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_safety.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px;")
        
        self.btn_connect = self._create_button("CONNECT", "#005500")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_arm = self._create_button("ARM", "#880000")
        self.btn_arm.setObjectName("btn_arm")
        self.btn_disarm = self._create_button("DISARM", "#440000")
        self.btn_disarm.setObjectName("btn_disarm")
        
        # Calibration Row
        self.cal_row = QHBoxLayout()
        self.btn_cal_acc = self._create_button("ACC CAL", "#333300")
        self.btn_cal_mag = self._create_button("MAG CAL", "#330033")
        self.cal_row.addWidget(self.btn_cal_acc)
        self.cal_row.addWidget(self.btn_cal_mag)
        
        self.btn_save = self._create_button("SAVE CONFIG (EEPROM)", "#444")
        
        self.btn_connect.clicked.connect(self.connect_clicked.emit)
        self.btn_arm.clicked.connect(self.arm_clicked.emit)
        self.btn_disarm.clicked.connect(self.disarm_clicked.emit)
        self.btn_cal_acc.clicked.connect(self.calibrate_clicked.emit)
        self.btn_cal_mag.clicked.connect(self.calibrate_mag_clicked.emit)
        self.btn_save.clicked.connect(self.save_config_clicked.emit)
        
        self.safety_group.addWidget(self.lbl_safety)
        self.safety_group.addWidget(self.btn_connect)
        self.safety_group.addWidget(self.btn_arm)
        self.safety_group.addWidget(self.btn_disarm)
        self.safety_group.addLayout(self.cal_row)
        self.safety_group.addWidget(self.btn_save)
        self.main_layout.addLayout(self.safety_group)

        # 2. Flight & Acrobatics Section
        self.flight_group = QVBoxLayout()
        self.lbl_flight = QLabel("--- FLIGHT & ACRO ---")
        self.lbl_flight.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_flight.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px;")
        
        # Takeoff/Land Row
        self.to_row = QHBoxLayout()
        self.btn_takeoff = self._create_button("TAKEOFF", "#004488")
        self.btn_land = self._create_button("LAND", "#884400")
        self.to_row.addWidget(self.btn_takeoff)
        self.to_row.addWidget(self.btn_land)
        
        # Flip Grid
        self.flip_grid = QGridLayout()
        self.btn_f_fwd = self._create_button("FWD FLIP", "#555")
        self.btn_f_back = self._create_button("BCK FLIP", "#555")
        self.btn_f_left = self._create_button("LFT FLIP", "#555")
        self.btn_f_right = self._create_button("RGT FLIP", "#555")
        
        # Directions from PlutoV2: 3=Back, 4=Front, 5=Right, 6=Left
        self.btn_f_fwd.clicked.connect(lambda: self.flip_clicked.emit(4))
        self.btn_f_back.clicked.connect(lambda: self.flip_clicked.emit(3))
        self.btn_f_left.clicked.connect(lambda: self.flip_clicked.emit(6))
        self.btn_f_right.clicked.connect(lambda: self.flip_clicked.emit(5))
        
        self.flip_grid.addWidget(self.btn_f_fwd, 0, 1)
        self.flip_grid.addWidget(self.btn_f_left, 1, 0)
        self.flip_grid.addWidget(self.btn_f_right, 1, 2)
        self.flip_grid.addWidget(self.btn_f_back, 2, 1)

        self.flight_group.addWidget(self.lbl_flight)
        self.flight_group.addLayout(self.to_row)
        self.flight_group.addLayout(self.flip_grid)
        self.main_layout.addLayout(self.flight_group)

        # 3. Manual Override Section
        self.manual_group = QVBoxLayout()
        self.lbl_manual = QLabel("--- MANUAL OVERRIDE ---")
        self.lbl_manual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_manual.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px;")
        self.manual_group.addWidget(self.lbl_manual)
        
        # Jog + Throttle Horizontal
        self.man_controls = QHBoxLayout()
        
        # Grid for all 4 axes
        self.jog_grid = QGridLayout()
        self.btn_p_up = self._create_button("P+", "#333")
        self.btn_p_dn = self._create_button("P-", "#333")
        self.btn_r_lf = self._create_button("R-", "#333")
        self.btn_r_rt = self._create_button("R+", "#333")
        self.btn_y_lf = self._create_button("Y-", "#333")
        self.btn_y_rt = self._create_button("Y+", "#333")
        self.btn_t_up = self._create_button("T+", "#333")
        self.btn_t_dn = self._create_button("T-", "#333")
        self.btn_reset = self._create_button("CTR", "#555")
        
        # Fixed size for grid buttons
        for b in [self.btn_p_up, self.btn_p_dn, self.btn_r_lf, self.btn_r_rt, 
                  self.btn_y_lf, self.btn_y_rt, self.btn_t_up, self.btn_t_dn, self.btn_reset]:
            b.setFixedSize(40, 40)
            b.setStyleSheet(b.styleSheet() + "font-size: 9px; padding: 0;")

        # Layout: P, R, Y in a logical pattern, T separately
        self.jog_grid.addWidget(self.btn_p_up, 0, 1)
        self.jog_grid.addWidget(self.btn_r_lf, 1, 0)
        self.jog_grid.addWidget(self.btn_reset, 1, 1)
        self.jog_grid.addWidget(self.btn_r_rt, 1, 2)
        self.jog_grid.addWidget(self.btn_p_dn, 2, 1)
        
        # Yaw and Throttle steps
        self.jog_grid.addWidget(self.btn_t_up, 0, 3)
        self.jog_grid.addWidget(self.btn_y_lf, 1, 3)
        self.jog_grid.addWidget(self.btn_y_rt, 1, 4)
        self.jog_grid.addWidget(self.btn_t_dn, 2, 3)
        
        self.man_controls.addLayout(self.jog_grid)
        
        # Throttle Slider
        self.sld_throttle = QSlider(Qt.Orientation.Vertical)
        self.sld_throttle.setRange(1000, 2000)
        self.sld_throttle.setValue(1000)
        self.sld_throttle.setMinimumHeight(120)
        self.sld_throttle.setStyleSheet("""
            QSlider::groove:vertical { background: #333; width: 6px; }
            QSlider::handle:vertical { background: #0ff; height: 15px; margin: 0 -5px; }
        """)
        self.sld_throttle.valueChanged.connect(self._on_manual_change)
        self.man_controls.addWidget(self.sld_throttle)
        
        self.manual_group.addLayout(self.man_controls)
        self.main_layout.addLayout(self.manual_group)
        
        # Jog Logic
        self.manual_vals = {'roll': 1500, 'pitch': 1500, 'yaw': 1500}
        self.btn_p_up.clicked.connect(lambda: self._update_jog('pitch', 20))
        self.btn_p_dn.clicked.connect(lambda: self._update_jog('pitch', -20))
        self.btn_r_lf.clicked.connect(lambda: self._update_jog('roll', -20))
        self.btn_r_rt.clicked.connect(lambda: self._update_jog('roll', 20))
        self.btn_y_lf.clicked.connect(lambda: self._update_jog('yaw', -50))
        self.btn_y_rt.clicked.connect(lambda: self._update_jog('yaw', 50))
        self.btn_t_up.clicked.connect(lambda: self._update_throttle(50))
        self.btn_t_dn.clicked.connect(lambda: self._update_throttle(-50))
        self.btn_reset.clicked.connect(self._reset_jog)

        self.main_layout.addStretch()

    def _create_button(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background-color: #fff;
                color: black;
            }}
        """)
        return btn

    def _update_jog(self, axis, delta):
        self.manual_vals[axis] = max(1000, min(2000, self.manual_vals[axis] + delta))
        self._on_manual_change()

    def _update_throttle(self, delta):
        new_val = max(1000, min(2000, self.sld_throttle.value() + delta))
        self.sld_throttle.setValue(new_val)
        # sld_throttle.valueChanged already calls _on_manual_change

    def _reset_jog(self):
        self.manual_vals = {'roll': 1500, 'pitch': 1500, 'yaw': 1500}
        self._on_manual_change()

    def _on_manual_change(self):
        self.manual_rc_changed.emit(
            self.manual_vals['roll'],
            self.manual_vals['pitch'],
            self.sld_throttle.value(),
            self.manual_vals['yaw']
        )
