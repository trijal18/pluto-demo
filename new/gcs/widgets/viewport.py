import cv2
import numpy as np
import math
import time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont, QBrush, QPolygonF, QPainterPath
from PyQt6.QtCore import Qt, QRect, QPointF, QRectF, pyqtSignal

class ViewportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.landmarks = None
        self.handedness = None
        self.mode = "DISCONNECTED"
        self.clutch_active = False
        
        # HUD State
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.altitude = 0
        self.battery = 0.0
        self.soc = 0
        self.rssi = 0
        self.watchdog = False
        self.targets = [1500, 1500, 1000, 1500] # R, P, T, Y
        
        self.video_rect = QRect(0, 0, 0, 0)

    def update_frame(self, frame):
        self.image = frame
        self.update()

    def update_landmarks(self, landmarks, handedness):
        self.landmarks = landmarks
        self.handedness = handedness
        self.update()

    def update_hud(self, state):
        self.roll = state.get('roll', 0.0)
        self.pitch = state.get('pitch', 0.0)
        self.yaw = state.get('yaw', 0.0)
        self.altitude = state.get('height', 0)
        self.battery = state.get('battery', 0.0)
        self.soc = state.get('battery_percentage', 0)
        self.rssi = state.get('rssi', 0)
        self.watchdog = state.get('watchdog_active', False)
        self.update()

    def update_targets(self, r, p, t, y):
        """Updates the COMMANDED targets (what we are sending)"""
        self.targets = [r, p, t, y]
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def set_clutch(self, active):
        self.clutch_active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Background
        painter.fillRect(self.rect(), QColor(5, 5, 5))

        # 2. Video Frame
        if self.image is not None:
            h, w, ch = self.image.shape
            bytes_per_line = ch * w
            qt_image = QImage(self.image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            x_off = (self.width() - scaled_pixmap.width()) // 2
            y_off = (self.height() - scaled_pixmap.height()) // 2
            self.video_rect = QRect(x_off, y_off, scaled_pixmap.width(), scaled_pixmap.height())
            
            painter.drawPixmap(x_off, y_off, scaled_pixmap)
            
            # Watchdog Pulse
            if self.watchdog:
                glow = int(abs(math.sin(time.time() * 5)) * 180)
                painter.setPen(QPen(QColor(255, 0, 0, glow), 6))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self.video_rect.adjusted(3, 3, -3, -3))

            # HUD Layer
            painter.save()
            painter.setClipRect(self.video_rect)
            
            # Draw Hand Skeleton
            if self.landmarks and self.handedness:
                self._draw_landmarks(painter, self.video_rect)

            # Draw HUD Instruments
            self._draw_horizon_gauge(painter, self.video_rect)
            self._draw_altitude_tape(painter, self.video_rect)
            self._draw_compass_ribbon(painter, self.video_rect)
            self._draw_system_badges(painter, self.video_rect)
            self._draw_target_bars(painter, self.video_rect)
            
            painter.restore()

    def _draw_landmarks(self, painter, rect):
        for i, (lm_list, hand) in enumerate(zip(self.landmarks, self.handedness)):
            label = hand[0].category_name # 'Left' or 'Right'
            color = QColor(0, 255, 255, 200) if label == "Left" else QColor(0, 255, 100, 200)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            for pt in lm_list:
                px = rect.x() + int(pt.x * rect.width())
                py = rect.y() + int(pt.y * rect.height())
                painter.drawEllipse(px - 2, py - 2, 4, 4)
            
            # Skeleton
            painter.setPen(QPen(color, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            l = lm_list
            conn = [(0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8), (0,17),(17,18),(18,19),(19,20), (5,9),(9,13),(13,17), (9,10),(10,11),(11,12), (13,14),(14,15),(15,16)]
            for s, e in conn:
                p1 = QPointF(rect.x() + l[s].x * rect.width(), rect.y() + l[s].y * rect.height())
                p2 = QPointF(rect.x() + l[e].x * rect.width(), rect.y() + l[e].y * rect.height())
                painter.drawLine(p1, p2)

    def _draw_horizon_gauge(self, painter, rect):
        size = 110
        x, y = rect.x() + 20, rect.y() + 20
        cx, cy = x + size/2, y + size/2
        
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.addEllipse(QRectF(x+5, y+5, size-10, size-10))
        painter.setClipPath(path)
        
        painter.translate(cx, cy)
        painter.rotate(-self.roll)
        po = self.pitch * 1.5
        painter.fillRect(QRectF(-size, -size - po, size*2, size + po), QColor(0, 100, 255, 120)) # Sky
        painter.fillRect(QRectF(-size, -po, size*2, size + po), QColor(150, 75, 0, 120)) # Ground
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawLine(QPointF(-size/2, -po), QPointF(size/2, -po))
        painter.restore()
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 255, 204), 2))
        painter.drawEllipse(QRectF(x+5, y+5, size-10, size-10))

    def _draw_altitude_tape(self, painter, rect):
        tw, th = 55, 220
        x, y = rect.x() + 20, rect.y() + 150
        
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.translate(x, y)
        painter.fillRect(0, 0, tw, th, QColor(0, 0, 0, 100))
        painter.setPen(QPen(QColor(0, 255, 204, 120), 1))
        painter.drawRect(0, 0, tw, th)
        
        clip = QPainterPath()
        clip.addRect(QRectF(0, 0, tw, th))
        painter.setClipPath(clip)
        
        cy = th / 2
        alt = int(self.altitude)
        painter.setFont(QFont("Consolas", 8))
        for v in range((alt // 20 - 6) * 20, (alt // 20 + 7) * 20, 20):
            yy = cy + (self.altitude - v) * 2
            painter.setPen(QColor(0, 255, 204))
            painter.drawLine(40, int(yy), tw, int(yy))
            painter.drawText(5, int(yy + 4), str(v))
        painter.restore()
        
        painter.setPen(QPen(Qt.GlobalColor.yellow, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.yellow))
        arrow = QPolygonF([QPointF(x+tw, y+cy), QPointF(x+tw+10, y+cy-6), QPointF(x+tw+10, y+cy+6)])
        painter.drawPolygon(arrow)
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(x+tw+14, y+int(cy+5), f"{self.altitude}cm")

    def _draw_compass_ribbon(self, painter, rect):
        cx = rect.x() + rect.width() / 2
        rw, rh = 350, 25
        ry = rect.y() + 15
        r_rect = QRectF(cx - rw/2, ry, rw, rh)
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
        painter.setPen(QPen(QColor(0, 255, 204, 120), 1))
        painter.drawRect(r_rect)
        
        painter.save()
        painter.setClipRect(r_rect)
        yaw = self.yaw % 360
        painter.setFont(QFont("Consolas", 9))
        for d in range(int(yaw - 45), int(yaw + 46)):
            xx = cx + (d - yaw) * 4
            if d % 30 == 0:
                label = str(d % 360)
                if label == "0": label = "N"
                elif label == "90": label = "E"
                elif label == "180": label = "S"
                elif label == "270": label = "W"
                painter.setPen(QColor(0, 255, 204))
                painter.drawLine(QPointF(xx, ry), QPointF(xx, ry + 12))
                painter.drawText(int(xx - 8), int(ry + 23), label)
            elif d % 5 == 0:
                painter.setPen(QColor(0, 255, 204, 80))
                painter.drawLine(QPointF(xx, ry), QPointF(xx, ry + 8))
        painter.restore()
        
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.drawLine(QPointF(cx, ry - 3), QPointF(cx, ry + rh + 3))

    def _draw_system_badges(self, painter, rect):
        x = rect.x() + rect.width() - 120
        y = rect.y() + 25
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        color = QColor(0, 255, 0) if self.soc > 40 else QColor(255, 255, 0) if self.soc > 20 else QColor(255, 50, 50)
        painter.setPen(color)
        painter.drawText(x, y, f"{self.battery:.2f}V")
        painter.drawText(x, y + 20, f"SOC: {self.soc}%")
        painter.setPen(QColor(0, 255, 204))
        painter.drawText(x, y + 40, f"RSSI: {self.rssi}")

    def _draw_target_bars(self, painter, rect):
        bw, bh = 140, 10
        labels = ["ROL", "PIT", "THR", "YAW"]
        total_w = len(labels) * (bw + 15)
        start_x = rect.x() + (rect.width() - total_w) / 2
        y = rect.y() + rect.height() - 30
        
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        for i, val in enumerate(self.targets):
            bx = start_x + i * (bw + 15)
            # Label as "CMD" to indicate Commanded/Sent values
            painter.setPen(QColor(0, 255, 204, 255))
            painter.drawText(int(bx), int(y - 5), f"CMD_{labels[i]}")
            
            painter.setPen(QPen(QColor(0, 255, 204, 120), 1))
            painter.setBrush(QBrush(QColor(20, 20, 20, 180)))
            painter.drawRect(QRectF(bx, y, bw, bh))
            
            fill_w = int(((val - 1000) / 1000) * bw)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 255, 204, 220)))
            painter.fillRect(QRectF(bx, y, fill_w, bh), painter.brush())
