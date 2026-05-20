import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

class OscilloscopeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Create Plot Widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1a1a')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(1000, 2000)
        self.plot_widget.setXRange(0, 100)
        self.plot_widget.hideAxis('bottom')
        
        self.layout.addWidget(self.plot_widget)
        
        # Data Buffers
        self.buffer_size = 100
        self.data = {
            'roll': [1500] * self.buffer_size,
            'pitch': [1500] * self.buffer_size,
            'yaw': [1500] * self.buffer_size,
            'throttle': [1000] * self.buffer_size
        }
        
        # Curves
        self.curves = {
            'roll': self.plot_widget.plot(pen=pg.mkPen(color='#0ff', width=2), name="Roll"),
            'pitch': self.plot_widget.plot(pen=pg.mkPen(color='#f0f', width=2), name="Pitch"),
            'yaw': self.plot_widget.plot(pen=pg.mkPen(color='#ff0', width=2), name="Yaw"),
            'throttle': self.plot_widget.plot(pen=pg.mkPen(color='#0f0', width=2), name="Throttle")
        }

    def update_data(self, state):
        rc = state.get('rc', [1500, 1500, 1000, 1500])
        
        # Update buffers
        self.data['roll'].append(rc[0])
        self.data['pitch'].append(rc[1])
        self.data['throttle'].append(rc[2])
        self.data['yaw'].append(rc[3])
        
        for key in self.data:
            self.data[key] = self.data[key][-self.buffer_size:]
            self.curves[key].setData(self.data[key])
