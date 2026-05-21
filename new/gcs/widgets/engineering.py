import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal

class RCBar(QWidget):
    def __init__(self, label="CH", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)
        
        self.lbl = QLabel(label)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("font-size: 9px; color: #888;")
        
        self.bar = QProgressBar()
        self.bar.setOrientation(Qt.Orientation.Vertical)
        self.bar.setRange(1000, 2000)
        self.bar.setValue(1500)
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(15)
        self.bar.setStyleSheet("""
            QProgressBar { background: #222; border: 1px solid #333; }
            QProgressBar::chunk { background: #0f0; }
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
        
        # Color coding
        if val > 1800 or val < 1200: color = "#f00"
        elif val > 1600 or val < 1400: color = "#ff0"
        else: color = "#0f0"
        self.bar.setStyleSheet(f"QProgressBar {{ background: #222; border: 1px solid #333; }} QProgressBar::chunk {{ background: {color}; }}")

class EngineeringConsole(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. RC Monitor (8 Channels)
        self.rc_group = QWidget()
        self.rc_layout = QHBoxLayout(self.rc_group)
        self.rc_layout.setSpacing(5)
        
        self.rc_channels = []
        labels = ["ROL", "PIT", "THR", "YAW", "AX1", "AX2", "AX3", "AX4"]
        for lbl in labels:
            bar = RCBar(lbl)
            self.rc_channels.append(bar)
            self.rc_layout.addWidget(bar)
            
        self.layout.addWidget(self.rc_group)
        
        # 2. IMU Plots
        self.plot_container = QWidget()
        self.plot_layout = QHBoxLayout(self.plot_container)
        
        self.acc_plot = self._create_plot("ACC (G)")
        self.gyro_plot = self._create_plot("GYRO (deg/s)")
        self.mag_plot = self._create_plot("MAG (uT)")
        
        self.plot_layout.addWidget(self.acc_plot)
        self.plot_layout.addWidget(self.gyro_plot)
        self.plot_layout.addWidget(self.mag_plot)
        
        self.layout.addWidget(self.plot_container, 1)
        
        # Data Buffers
        self.buf_size = 100
        self.data = {
            'acc': {'x': [0]*self.buf_size, 'y': [0]*self.buf_size, 'z': [0]*self.buf_size},
            'gyro': {'x': [0]*self.buf_size, 'y': [0]*self.buf_size, 'z': [0]*self.buf_size},
            'mag': {'x': [0]*self.buf_size, 'y': [0]*self.buf_size, 'z': [0]*self.buf_size}
        }
        
        # Curves
        self.curves = {
            'acc': self._add_curves(self.acc_plot),
            'gyro': self._add_curves(self.gyro_plot),
            'mag': self._add_curves(self.mag_plot)
        }

    def _create_plot(self, title):
        pw = pg.PlotWidget()
        pw.setBackground('#0d0d0d')
        pw.setTitle(title, color='#888', size='9pt')
        pw.showGrid(x=True, y=True, alpha=0.2)
        pw.hideAxis('bottom')
        return pw

    def _add_curves(self, plot):
        return {
            'x': plot.plot(pen=pg.mkPen('#f00', width=1)),
            'y': plot.plot(pen=pg.mkPen('#0f0', width=1)),
            'z': plot.plot(pen=pg.mkPen('#00f', width=1))
        }

    def update_data(self, state):
        # Update RC
        rc = state.get('rc', [1500]*8)
        for i, val in enumerate(rc):
            if i < len(self.rc_channels):
                self.rc_channels[i].set_value(val)
                
        # Update IMU
        for key in ['acc', 'gyro', 'mag']:
            vals = state.get(key, [0, 0, 0])
            for i, axis in enumerate(['x', 'y', 'z']):
                self.data[key][axis].append(vals[i])
                self.data[key][axis] = self.data[key][axis][-self.buf_size:]
                self.curves[key][axis].setData(self.data[key][axis])
