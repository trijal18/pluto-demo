import cv2
import numpy as np
import math
import time
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont, QBrush, QPolygonF, QPainterPath
from PyQt6.QtCore import Qt, QRect, QPointF, QRectF, pyqtSignal

class ViewportWidget(QWidget):
    cal_acc_clicked = pyqtSignal()
    cal_mag_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.landmarks = None
        self.handedness = None
        self.mode = "DISCONNECTED"
        self.clutch_active = False
        
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.altitude = 0
        self.battery = 0.0
        self.soc = 0
        self.rssi = 0
        self.watchdog = False
        self.targets = [1500, 1500, 1000, 1500]
        
        self.video_rect = QRect(0, 0, 640, 480)
        self.setMouseTracking(True)

    def sizeHint(self):
        # Helps the layout shrink to the video frame
        return QRect(0, 0, 640, 480).size()

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
        painter.fillRect(self.rect(), QColor(5, 5, 5))

        if self.image is not None:
            h, w, ch = self.image.shape
            bytes_per_line = ch * w
            qt_image = QImage(self.image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            x_off = (self.width() - scaled_pixmap.width()) // 2
            y_off = (self.height() - scaled_pixmap.height()) // 2
            self.video_rect = QRect(x_off, y_off, scaled_pixmap.width(), scaled_pixmap.height())
            
            painter.drawPixmap(x_off, y_off, scaled_pixmap)
            
            painter.save()
            painter.setClipRect(self.video_rect)
            
            if self.landmarks and self.handedness:
                self._draw_landmarks(painter, self.video_rect)

            if self.watchdog:
                glow = int(abs(math.sin(time.time() * 5)) * 180)
                painter.setPen(QPen(QColor(255, 0, 0, glow), 6))
                painter.drawRect(self.video_rect.adjusted(3, 3, -3, -3))

            self._draw_horizon_gauge(painter, self.video_rect)
            self._draw_altitude_tape(painter, self.video_rect)
            self._draw_compass_ribbon(painter, self.video_rect)
            self._draw_system_badges(painter, self.video_rect)
            self._draw_target_bars(painter, self.video_rect)
            
            painter.restore()

    def _draw_landmarks(self, painter, rect):
        for i, (lm_list, hand) in enumerate(zip(self.landmarks, self.handedness)):
            label = hand[0].category_name # "Left" (Physical Right) or "Right" (Physical Left)
            
            # Determine color theme based on hand state
            if label == "Right": # Physical Left Hand (Clutch / Throttle / Yaw)
                color = QColor(0, 255, 100) if self.clutch_active else QColor(255, 170, 0)
            else: # Physical Right Hand (Flight: Pitch / Roll)
                color = QColor(0, 255, 255) if self.clutch_active else QColor(0, 180, 200, 150)
                
            # 1. Bounding Box & Corner Brackets Calculation
            xs = [rect.x() + int(pt.x * rect.width()) for pt in lm_list]
            ys = [rect.y() + int(pt.y * rect.height()) for pt in lm_list]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Add padding
            padding = 20
            min_x = max(rect.x(), min_x - padding)
            max_x = min(rect.x() + rect.width(), max_x + padding)
            min_y = max(rect.y(), min_y - padding)
            max_y = min(rect.y() + rect.height(), max_y + padding)
            
            # Draw military L-brackets
            painter.setPen(QPen(color, 2))
            L = 15 # Bracket line length
            # Top-Left
            painter.drawLine(min_x, min_y, min_x + L, min_y)
            painter.drawLine(min_x, min_y, min_x, min_y + L)
            # Top-Right
            painter.drawLine(max_x, min_y, max_x - L, min_y)
            painter.drawLine(max_x, min_y, max_x, min_y + L)
            # Bottom-Left
            painter.drawLine(min_x, max_y, min_x + L, max_y)
            painter.drawLine(min_x, max_y, min_x, max_y - L)
            # Bottom-Right
            painter.drawLine(max_x, max_y, max_x - L, max_y)
            painter.drawLine(max_x, max_y, max_x, max_y - L)

            # 2. Draw Skeletal Connections (Translucent)
            conn_color = QColor(color.red(), color.green(), color.blue(), 100)
            painter.setPen(QPen(conn_color, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            l = lm_list
            connections = [
                (0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8),
                (0,17),(17,18),(18,19),(19,20), (5,9),(9,13),(13,17),
                (9,10),(10,11),(11,12), (13,14),(14,15),(15,16)
            ]
            for s, e in connections:
                p1 = QPointF(rect.x() + l[s].x * rect.width(), rect.y() + l[s].y * rect.height())
                p2 = QPointF(rect.x() + l[e].x * rect.width(), rect.y() + l[e].y * rect.height())
                painter.drawLine(p1, p2)

            # 3. Draw Joints (Solid dots)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            for pt in lm_list:
                px = rect.x() + int(pt.x * rect.width())
                py = rect.y() + int(pt.y * rect.height())
                painter.drawEllipse(px - 3, py - 3, 6, 6)

            # 4. State-Driven Skeletal Highlights & Vectors
            if label == "Right": # Physical Left Hand (Clutch / Yaw)
                p4 = QPointF(rect.x() + l[4].x * rect.width(), rect.y() + l[4].y * rect.height())
                p8 = QPointF(rect.x() + l[8].x * rect.width(), rect.y() + l[8].y * rect.height())
                
                # Highlight pinch if clutch engaged
                if self.clutch_active:
                    cx, cy = int((p4.x() + p8.x()) / 2), int((p4.y() + p8.y()) / 2)
                    painter.setPen(QPen(QColor(0, 255, 100), 1, Qt.PenStyle.DashLine))
                    painter.drawEllipse(cx - 8, cy - 8, 16, 16)
                    painter.setPen(QPen(QColor(0, 255, 100), 2))
                    painter.drawLine(p4, p8)
                
                # Draw Yaw Wave reference line
                p20 = QPointF(rect.x() + l[20].x * rect.width(), rect.y() + l[20].y * rect.height())
                painter.setPen(QPen(QColor(255, 255, 255, 100), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(p4.x()), int(p4.y()), int(p20.x()), int(p4.y()))
                painter.setPen(QPen(color, 2))
                painter.drawLine(p4, p20)
                
            else: # Physical Right Hand (Flight stick: Pitch / Roll)
                p4 = QPointF(rect.x() + l[4].x * rect.width(), rect.y() + l[4].y * rect.height())
                p20 = QPointF(rect.x() + l[20].x * rect.width(), rect.y() + l[20].y * rect.height())
                p0 = QPointF(rect.x() + l[0].x * rect.width(), rect.y() + l[0].y * rect.height())
                p9 = QPointF(rect.x() + l[9].x * rect.width(), rect.y() + l[9].y * rect.height())
                
                # Draw Roll Wave reference line
                painter.setPen(QPen(QColor(255, 255, 255, 100), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(p4.x()), int(p4.y()), int(p20.x()), int(p4.y()))
                painter.setPen(QPen(color, 2))
                painter.drawLine(p4, p20)
                
                # Draw Pitch vector line
                painter.setPen(QPen(color, 2))
                painter.drawLine(p0, p9)

            # 5. Paint Console Status Label Badges
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            fm = painter.fontMetrics()
            
            if label == "Right": # Physical Left Hand
                title = "SYS_L: CLUTCH & HEIGHT"
                status_text = f"CLUTCH: {'ENGAGED' if self.clutch_active else 'STANDBY'} | THR: {self.targets[2]} | YAW: {self.targets[3]}"
            else: # Physical Right Hand
                title = "SYS_R: FLIGHT AXIS"
                status_text = f"PITCH: {self.targets[1]} | ROLL: {self.targets[0]}"
                
            # Title Badge
            tw_title = fm.horizontalAdvance(title)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.drawRect(min_x, min_y - 16, tw_title + 10, 15)
            painter.setPen(color)
            painter.drawText(min_x + 5, min_y - 4, title)
            
            # Status Text Badge
            tw_status = fm.horizontalAdvance(status_text)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.drawRect(min_x, max_y + 2, tw_status + 10, 15)
            painter.setPen(color)
            painter.drawText(min_x + 5, max_y + 13, status_text)

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
        # Alignment: Directly below Horizon gauge
        x, y = rect.x() + 20, rect.y() + 140
        
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
        painter.setPen(QColor(255, 255, 0))
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
            painter.setPen(QColor(0, 255, 204, 255))
            painter.drawText(int(bx), int(y - 5), f"CMD_{labels[i]}")
            painter.setPen(QPen(QColor(0, 255, 204, 120), 1))
            painter.setBrush(QBrush(QColor(20, 20, 20, 180)))
            painter.drawRect(QRectF(bx, y, bw, bh))
            fill_w = int(((val - 1000) / 1000) * bw)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 255, 204, 220)))
            painter.fillRect(QRectF(bx, y, fill_w, bh), painter.brush())
