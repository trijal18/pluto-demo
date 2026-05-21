from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class ControlDeck(QWidget):
    # Signals for mission commands
    connect_clicked = pyqtSignal()
    arm_clicked = pyqtSignal()
    disarm_clicked = pyqtSignal()
    takeoff_clicked = pyqtSignal()
    land_clicked = pyqtSignal()
    manual_rc_changed = pyqtSignal(int, int, int, int) # R, P, T, Y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(180)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(5, 10, 5, 5)
        
        # 1. Mission Section
        self.lbl_mission = QLabel("--- MISSION ---")
        self.lbl_mission.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_mission.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px;")
        
        self.btn_connect = self._create_button("CONNECT", "#004400")
        self.btn_arm = self._create_button("ARM", "#660000")
        self.btn_takeoff = self._create_button("TAKEOFF", "#004466")
        self.btn_land = self._create_button("LAND", "#664400")
        self.btn_disarm = self._create_button("DISARM", "#440000")
        
        self.btn_connect.clicked.connect(self.connect_clicked.emit)
        self.btn_arm.clicked.connect(self.arm_clicked.emit)
        self.btn_takeoff.clicked.connect(self.takeoff_clicked.emit)
        self.btn_land.clicked.connect(self.land_clicked.emit)
        self.btn_disarm.clicked.connect(self.disarm_clicked.emit)

        self.layout.addWidget(self.lbl_mission)
        self.layout.addWidget(self.btn_connect)
        self.layout.addWidget(self.btn_arm)
        self.layout.addWidget(self.btn_takeoff)
        self.layout.addWidget(self.btn_land)
        
        self.layout.addSpacing(20)

        # 2. Manual Section
        self.lbl_manual = QLabel("--- MANUAL ---")
        self.lbl_manual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_manual.setStyleSheet("color: #0ff; font-weight: bold; font-size: 10px;")
        self.layout.addWidget(self.lbl_manual)
        
        self.jog_grid = QGridLayout()
        self.jog_grid.setSpacing(5)
        
        # Jog Buttons
        self.btn_p_up = self._create_jog_btn("P+")
        self.btn_p_dn = self._create_jog_btn("P-")
        self.btn_r_lf = self._create_jog_btn("R-")
        self.btn_r_rt = self._create_jog_btn("R+")
        self.btn_t_up = self._create_jog_btn("T+")
        self.btn_t_dn = self._create_jog_btn("T-")
        self.btn_y_lf = self._create_jog_btn("Y-")
        self.btn_y_rt = self._create_jog_btn("Y+")
        self.btn_ctr = self._create_jog_btn("CTR")
        
        self.jog_grid.addWidget(self.btn_p_up, 0, 1)
        self.jog_grid.addWidget(self.btn_r_lf, 1, 0)
        self.jog_grid.addWidget(self.btn_ctr, 1, 1)
        self.jog_grid.addWidget(self.btn_r_rt, 1, 2)
        self.jog_grid.addWidget(self.btn_p_dn, 2, 1)
        
        self.jog_grid.addWidget(self.btn_t_up, 0, 3)
        self.jog_grid.addWidget(self.btn_y_lf, 1, 3)
        self.jog_grid.addWidget(self.btn_y_rt, 1, 4)
        self.jog_grid.addWidget(self.btn_t_dn, 2, 3)
        
        self.layout.addLayout(self.jog_grid)
        
        # Logic
        self.vals = {'roll': 1500, 'pitch': 1500, 'throttle': 1000, 'yaw': 1500}
        self.btn_p_up.clicked.connect(lambda: self._upd('pitch', 25))
        self.btn_p_dn.clicked.connect(lambda: self._upd('pitch', -25))
        self.btn_r_lf.clicked.connect(lambda: self._upd('roll', -25))
        self.btn_r_rt.clicked.connect(lambda: self._upd('roll', 25))
        self.btn_t_up.clicked.connect(lambda: self._upd('throttle', 50))
        self.btn_t_dn.clicked.connect(lambda: self._upd('throttle', -50))
        self.btn_y_lf.clicked.connect(lambda: self._upd('yaw', -50))
        self.btn_y_rt.clicked.connect(lambda: self._upd('yaw', 50))
        self.btn_ctr.clicked.connect(self._reset)

        self.layout.addStretch()
        self.layout.addWidget(self.btn_disarm)

    def _create_button(self, text, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {color}; color: white; border: 1px solid #555; border-radius: 3px; padding: 10px; font-weight: bold; }}
            QPushButton:pressed {{ background: white; color: black; }}
        """)
        return btn

    def _create_jog_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(35, 35)
        btn.setStyleSheet("""
            QPushButton { background: #222; color: #0ff; border: 1px solid #444; border-radius: 2px; font-size: 9px; }
            QPushButton:pressed { background: #0ff; color: black; }
        """)
        return btn

    def _upd(self, axis, delta):
        self.vals[axis] = max(1000, min(2000, self.vals[axis] + delta))
        self.manual_rc_changed.emit(self.vals['roll'], self.vals['pitch'], self.vals['throttle'], self.vals['yaw'])

    def _reset(self):
        self.vals = {'roll': 1500, 'pitch': 1500, 'throttle': self.vals['throttle'], 'yaw': 1500}
        self.manual_rc_changed.emit(1500, 1500, self.vals['throttle'], 1500)
