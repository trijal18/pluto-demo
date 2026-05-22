from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class ControlDeck(QWidget):
    # Signals for mission commands
    connect_clicked = pyqtSignal()
    arm_clicked = pyqtSignal()
    disarm_clicked = pyqtSignal()
    takeoff_clicked = pyqtSignal()
    land_clicked = pyqtSignal()
    cal_acc_clicked = pyqtSignal()
    cal_mag_clicked = pyqtSignal()
    manual_rc_changed = pyqtSignal(int, int, int, int) # R, P, T, Y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200) # Slightly wider for slider
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 5)
        
        # 1. Mission Section
        self.lbl_mission = QLabel("--- MISSION ---")
        self._set_lbl_style(self.lbl_mission)
        
        self.btn_connect = self._create_button("CONNECT", "#004400")
        self.btn_arm = self._create_button("ARM", "#660000")
        self.btn_takeoff = self._create_button("TAKEOFF", "#004466")
        self.btn_land = self._create_button("LAND", "#664400")
        self.btn_disarm = self._create_button("DISARM", "#440000")
        
        for b in [self.btn_connect, self.btn_arm, self.btn_takeoff, self.btn_land]:
            self.layout.addWidget(b)
        
        # 2. Calibration Section (Moved from HUD)
        self.lbl_cal = QLabel("--- CALIBRATION ---")
        self._set_lbl_style(self.lbl_cal)
        self.cal_layout = QHBoxLayout()
        self.btn_cal_acc = self._create_button("ACC", "#333")
        self.btn_cal_mag = self._create_button("MAG", "#333")
        self.cal_layout.addWidget(self.btn_cal_acc)
        self.cal_layout.addWidget(self.btn_cal_mag)
        
        self.layout.addWidget(self.lbl_cal)
        self.layout.addLayout(self.cal_layout)

        # 3. Manual Section
        self.lbl_manual = QLabel("--- MANUAL ---")
        self._set_lbl_style(self.lbl_manual)
        self.layout.addWidget(self.lbl_manual)
        
        self.man_layout = QHBoxLayout()
        
        # Jog Grid (P, R, Y, CTR)
        self.jog_grid = QGridLayout()
        self.jog_grid.setSpacing(5)
        
        self.btn_p_up = self._create_jog_btn("P+")
        self.btn_p_dn = self._create_jog_btn("P-")
        self.btn_r_lf = self._create_jog_btn("R-")
        self.btn_r_rt = self._create_jog_btn("R+")
        self.btn_y_lf = self._create_jog_btn("Y-")
        self.btn_y_rt = self._create_jog_btn("Y+")
        self.btn_ctr = self._create_jog_btn("CTR")
        
        self.jog_grid.addWidget(self.btn_p_up, 0, 1)
        self.jog_grid.addWidget(self.btn_r_lf, 1, 0)
        self.jog_grid.addWidget(self.btn_ctr, 1, 1)
        self.jog_grid.addWidget(self.btn_r_rt, 1, 2)
        self.jog_grid.addWidget(self.btn_p_dn, 2, 1)
        
        # Yaw Buttons below P/R/CTR cross
        self.jog_grid.addWidget(self.btn_y_lf, 3, 0)
        self.jog_grid.addWidget(self.btn_y_rt, 3, 2)
        
        self.man_layout.addLayout(self.jog_grid)
        
        # Vertical Throttle Slider
        self.sld_thr = QSlider(Qt.Orientation.Vertical)
        self.sld_thr.setRange(1000, 2000)
        self.sld_thr.setValue(1000)
        self.sld_thr.setMinimumHeight(150)
        self.sld_thr.setStyleSheet("""
            QSlider::groove:vertical { background: #222; width: 8px; border-radius: 4px; }
            QSlider::handle:vertical { background: #0ff; height: 20px; margin: 0 -6px; border-radius: 2px; }
        """)
        self.man_layout.addWidget(self.sld_thr)
        self.layout.addLayout(self.man_layout)
        
        # Connect Signals
        self.btn_connect.clicked.connect(self.connect_clicked.emit)
        self.btn_arm.clicked.connect(self.arm_clicked.emit)
        self.btn_takeoff.clicked.connect(self.takeoff_clicked.emit)
        self.btn_land.clicked.connect(self.land_clicked.emit)
        self.btn_disarm.clicked.connect(self.disarm_clicked.emit)
        self.btn_cal_acc.clicked.connect(self.cal_acc_clicked.emit)
        self.btn_cal_mag.clicked.connect(self.cal_mag_clicked.emit)
        
        # Jog Logic
        self.vals = {'roll': 1500, 'pitch': 1500, 'yaw': 1500}
        self.btn_p_up.clicked.connect(lambda: self._upd('pitch', 25))
        self.btn_p_dn.clicked.connect(lambda: self._upd('pitch', -25))
        self.btn_r_lf.clicked.connect(lambda: self._upd('roll', -25))
        self.btn_r_rt.clicked.connect(lambda: self._upd('roll', 25))
        self.btn_y_lf.clicked.connect(lambda: self._upd('yaw', -50))
        self.btn_y_rt.clicked.connect(lambda: self._upd('yaw', 50))
        self.btn_ctr.clicked.connect(self._reset)
        self.sld_thr.valueChanged.connect(self._on_thr_change)

        self.layout.addStretch()
        self.layout.addWidget(self.btn_disarm)

    def _set_lbl_style(self, lbl):
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px; margin-top: 5px;")

    def _create_button(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: white; border: 1px solid #555; border-radius: 3px; padding: 8px; font-weight: bold; }}
            QPushButton:pressed {{ background: white; color: black; }}
        """)
        return btn

    def _create_jog_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(40, 40)
        btn.setStyleSheet("""
            QPushButton { background: #111; color: #0ff; border: 1px solid #444; border-radius: 3px; font-size: 10px; font-weight: bold; }
            QPushButton:pressed { background: #0ff; color: black; }
        """)
        return btn

    def _on_thr_change(self):
        self.manual_rc_changed.emit(self.vals['roll'], self.vals['pitch'], self.sld_thr.value(), self.vals['yaw'])

    def _upd(self, axis, delta):
        self.vals[axis] = max(1000, min(2000, self.vals[axis] + delta))
        self.manual_rc_changed.emit(self.vals['roll'], self.vals['pitch'], self.sld_thr.value(), self.vals['yaw'])

    def _reset(self):
        self.vals = {'roll': 1500, 'pitch': 1500, 'yaw': 1500}
        self.manual_rc_changed.emit(1500, 1500, self.sld_thr.value(), 1500)
