import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPolygonF, QPainterPath
from PyQt6.QtCore import Qt, QPointF, QRectF

class HorizonWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roll = 0.0 # Degrees
        self.pitch = 0.0 # Degrees
        self.setMinimumSize(200, 200)

    def set_orientation(self, roll, pitch):
        self.roll = roll
        self.pitch = pitch
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2
        cy = self.height() / 2
        radius = min(cx, cy) * 0.9
        
        # Clip to circle using QPainterPath
        path = QPainterPath()
        path.addEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
        painter.setClipPath(path)
        
        # 1. Draw Sky/Ground
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-self.roll)
        
        # Pitch offset (approx 2 pixels per degree)
        pitch_off = self.pitch * 2
        
        # Sky
        painter.fillRect(QRectF(-radius*2, -radius*2 - pitch_off, radius*4, radius*2 + pitch_off), QColor(0, 100, 200))
        # Ground
        painter.fillRect(QRectF(-radius*2, -pitch_off, radius*4, radius*2 + pitch_off), QColor(100, 50, 0))
        
        # Horizon Line
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(QPointF(-radius, -pitch_off), QPointF(radius, -pitch_off))
        
        # Pitch Ladder (Simple)
        painter.setFont(QFont("Consolas", 8))
        for p in range(-30, 31, 10):
            if p == 0: continue
            y = -p * 2 - pitch_off
            painter.drawLine(QPointF(-20, y), QPointF(20, y))
            painter.drawText(25, int(y + 4), str(p))
            
        painter.restore()
        
        # 2. Fixed Aircraft Reference
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        # Wings
        painter.drawLine(QPointF(cx - 50, cy), QPointF(cx - 10, cy))
        painter.drawLine(QPointF(cx + 10, cy), QPointF(cx + 50, cy))
        # Center pip
        painter.drawEllipse(QPointF(cx, cy), 3, 3)
        
        # 3. Outer Ring
        painter.setClipping(False)
        painter.setPen(QPen(QColor(0, 255, 255, 100), 2))
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.yaw = 0.0 # Degrees
        self.setMinimumSize(200, 50)

    def set_yaw(self, yaw):
        self.yaw = yaw
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w / 2
        
        # Background
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        
        # Tick Marks (Every 5 degrees)
        painter.setPen(QPen(QColor(0, 255, 255), 1))
        painter.setFont(QFont("Consolas", 9))
        
        # Scale: 2 pixels per degree
        for d in range(int(self.yaw - 45), int(self.yaw + 46)):
            x = cx + (d - self.yaw) * 4
            
            if d % 30 == 0:
                painter.drawLine(QPointF(x, 0), QPointF(x, 15))
                label = str(d % 360)
                if label == "0": label = "N"
                elif label == "90": label = "E"
                elif label == "180": label = "S"
                elif label == "270": label = "W"
                painter.drawText(int(x - 10), 30, label)
            elif d % 5 == 0:
                painter.drawLine(QPointF(x, 0), QPointF(x, 8))
        
        # Center Pointer
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawLine(QPointF(cx, 0), QPointF(cx, h))
