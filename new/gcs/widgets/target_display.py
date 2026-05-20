from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt

class TargetIndicator(QWidget):
    def __init__(self, label="CH", parent=None):
        super().__init__(parent)
        self.label_text = label
        self.value = 1500
        self.setMinimumHeight(40)
        self.setMinimumWidth(60)

    def set_value(self, val):
        self.value = max(1000, min(2000, int(val)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(25, 25, 25))
        painter.setPen(QColor(50, 50, 50))
        painter.drawRect(0, 0, self.width()-1, self.height()-1)
        
        # Label
        painter.setPen(QColor(0, 200, 255))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(5, 12, self.label_text)
        
        # Value
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(5, 30, str(int(self.value)))
        
        # Mini Bar
        bar_margin = 5
        bar_y = 34
        bar_h = 4
        painter.fillRect(bar_margin, bar_y, self.width() - 2*bar_margin, bar_h, QColor(40, 40, 40))
        
        normalized = (self.value - 1000) / 1000.0
        fill_w = int(normalized * (self.width() - 2*bar_margin))
        painter.fillRect(bar_margin, bar_y, fill_w, bar_h, QColor(0, 255, 255))

class TargetDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        
        self.indicators = {
            'roll': TargetIndicator("T_ROLL"),
            'pitch': TargetIndicator("T_PITCH"),
            'throttle': TargetIndicator("T_THR"),
            'yaw': TargetIndicator("T_YAW")
        }
        
        self.layout.addWidget(QLabel("TARGET:"))
        for ind in self.indicators.values():
            self.layout.addWidget(ind)
        self.layout.addStretch()

    def update_targets(self, r, p, t, y):
        self.indicators['roll'].set_value(r)
        self.indicators['pitch'].set_value(p)
        self.indicators['throttle'].set_value(t)
        self.indicators['yaw'].set_value(y)
