import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt

class PrecisionBar(QWidget):
    def __init__(self, label="CH", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl = QLabel(label)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("font-size: 9px; color: #888;")
        
        self.bar = QProgressBar()
        self.bar.setOrientation(Qt.Orientation.Vertical)
        self.bar.setRange(1000, 2000)
        self.bar.setValue(1500)
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(20)
        self.bar.setStyleSheet("""
            QProgressBar { background: #111; border: 1px solid #333; }
            QProgressBar::chunk { background: #00ffcc; }
        """)
        
        self.val_lbl = QLabel("1500")
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_lbl.setStyleSheet("font-size: 9px; font-family: Consolas; color: #0ff;")
        
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.bar, 1, Qt.AlignmentFlag.AlignHCenter)
        self.layout.addWidget(self.val_lbl)

    def set_value(self, val):
        self.bar.setValue(int(val))
        self.val_lbl.setText(str(int(val)))

class EngineeringConsole(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        
        # 1. 8-CH Monitor
        self.rc_group = QWidget()
        self.rc_layout = QHBoxLayout(self.rc_group)
        self.rc_layout.setSpacing(4)
        self.rc_bars = []
        labels = ["ROL", "PIT", "THR", "YAW", "AX1", "AX2", "AX3", "AX4"]
        for lbl in labels:
            bar = PrecisionBar(lbl)
            self.rc_bars.append(bar)
            self.rc_layout.addWidget(bar)
        self.layout.addWidget(self.rc_group)
        
        # Divider
        line = QWidget()
        line.setFixedWidth(1)
        line.setStyleSheet("background: #333;")
        self.layout.addWidget(line)
        
        # 2. IMU Cluster (Horizontal Graphs)
        self.graphs_layout = QHBoxLayout()
        self.graphs_layout.setSpacing(5)
        
        self.acc_pw = self._setup_graph("ACC (G)")
        self.gyro_pw = self._setup_graph("GYRO (deg/s)")
        self.mag_pw = self._setup_graph("MAG (uT)")
        
        self.graphs_layout.addWidget(self.acc_pw)
        self.graphs_layout.addWidget(self.gyro_pw)
        self.graphs_layout.addWidget(self.mag_pw)
        self.layout.addLayout(self.graphs_layout, 1)
        
        # Buffers
        self.size = 150
        self.data = {
            'acc': {'x': [0]*self.size, 'y': [0]*self.size, 'z': [0]*self.size},
            'gyro': {'x': [0]*self.size, 'y': [0]*self.size, 'z': [0]*self.size},
            'mag': {'x': [0]*self.size, 'y': [0]*self.size, 'z': [0]*self.size}
        }
        self.curves = {
            'acc': self._add_curves(self.acc_pw),
            'gyro': self._add_curves(self.gyro_pw),
            'mag': self._add_curves(self.mag_pw)
        }

    def _setup_graph(self, title):
        pw = pg.PlotWidget()
        pw.setBackground('#0a0a0a')
        pw.setTitle(title, color='#555', size='8pt')
        pw.showGrid(x=True, y=True, alpha=0.1)
        pw.setMenuEnabled(False)
        pw.setMouseEnabled(x=False, y=False)
        pw.hideAxis('bottom')
        
        # Set ranges based on typical sensor values
        if "ACC" in title:
            pw.setYRange(-500, 500)
        elif "GYRO" in title:
            pw.setYRange(-2000, 2000)
        elif "MAG" in title:
            pw.setYRange(-1000, 1000)
            
        return pw

    def _add_curves(self, pw):
        return {
            'x': pw.plot(pen=pg.mkPen('#f00', width=1)),
            'y': pw.plot(pen=pg.mkPen('#0f0', width=1)),
            'z': pw.plot(pen=pg.mkPen('#00f', width=1))
        }

    def update_data(self, state):
        # RC
        rc = state.get('rc', [1500]*8)
        for i, val in enumerate(rc):
            if i < len(self.rc_bars): self.rc_bars[i].set_value(val)
            
        # IMU
        for key in ['acc', 'gyro', 'mag']:
            vals = state.get(key, [0,0,0])
            for i, axis in enumerate(['x','y','z']):
                self.data[key][axis].append(vals[i])
                self.data[key][axis] = self.data[key][axis][-self.size:]
                self.curves[key][axis].setData(self.data[key][axis])
