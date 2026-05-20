import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRect

class ViewportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(320, 240)
        
        self.current_frame = None
        self.landmarks = None
        self.handedness = None
        self.clutch_active = False
        self.mode = "STANDBY"
        
        # Retro Colors
        self.color_skeleton = QColor(0, 255, 100, 200) # Phosphor Green
        self.color_hud = QColor(0, 255, 255, 180) # Cyan
        self.color_clutch = QColor(255, 165, 0) # Amber

    def update_frame(self, frame):
        self.current_frame = frame
        self.update()

    def update_landmarks(self, landmarks, handedness):
        self.landmarks = landmarks
        self.handedness = handedness
        self.update()

    def set_clutch(self, active):
        self.clutch_active = active
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Draw Background
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        
        if self.current_frame is None:
            painter.setPen(self.color_hud)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "WAITING FOR VIDEO STREAM...")
            return

        # 2. Draw Base Video
        h, w, ch = self.current_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(self.current_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
        
        # Scale to fit widget
        target_w = self.width()
        target_h = self.height()
        scaled_pixmap = QPixmap.fromImage(q_img).scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio)
        
        # Calculate offset for centering
        x_off = (target_w - scaled_pixmap.width()) // 2
        y_off = (target_h - scaled_pixmap.height()) // 2
        
        painter.drawPixmap(x_off, y_off, scaled_pixmap)
        
        # Calculate scale factor for landmarks
        scale_x = scaled_pixmap.width() / w
        scale_y = scaled_pixmap.height() / h

        # 2. Draw Skeleton
        if self.landmarks:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            for i, hand_landmarks in enumerate(self.landmarks):
                side = self.handedness[i][0].category_name # "Left" or "Right"
                
                # Colors based on side
                if side == "Left": # Physical Right (Flight)
                    base_color = QColor(255, 0, 255, 180) # Magenta
                    highlight_color = QColor(0, 255, 255) # Cyan
                    label = "RIGHT (FLIGHT)"
                else: # Physical Left (Clutch)
                    base_color = QColor(0, 255, 100, 180) # Green
                    highlight_color = QColor(0, 255, 0) # Bright Green
                    label = "LEFT (CLUTCH)"

                painter.setPen(QPen(base_color, 1))
                
                # 2.1 Full Skeleton (Thin)
                connections = [
                    (0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8),
                    (5,9),(9,10),(10,11),(11,12), (9,13),(13,14),(14,15),(15,16),
                    (13,17),(17,18),(18,19),(19,20), (0,17)
                ]
                
                for start_idx, end_idx in connections:
                    pt1 = hand_landmarks[start_idx]
                    pt2 = hand_landmarks[end_idx]
                    p1 = (int(pt1.x * scaled_pixmap.width()) + x_off, int(pt1.y * scaled_pixmap.height()) + y_off)
                    p2 = (int(pt2.x * scaled_pixmap.width()) + x_off, int(pt2.y * scaled_pixmap.height()) + y_off)
                    painter.drawLine(p1[0], p1[1], p2[0], p2[1])

                # 2.2 Highlights
                if side == "Left": # Flight Hand Highlights
                    painter.setPen(QPen(highlight_color, 2))
                    painter.setBrush(highlight_color)
                    pts = [0, 4, 20] # Wrist, Thumb, Pinky
                    tri_pts = []
                    for idx in pts:
                        lm = hand_landmarks[idx]
                        px = int(lm.x * scaled_pixmap.width()) + x_off
                        py = int(lm.y * scaled_pixmap.height()) + y_off
                        painter.drawEllipse(px-4, py-4, 8, 8)
                        tri_pts.append((px, py))
                    
                    # Draw Super-Triangle
                    painter.drawLine(tri_pts[0][0], tri_pts[0][1], tri_pts[1][0], tri_pts[1][1])
                    painter.drawLine(tri_pts[1][0], tri_pts[1][1], tri_pts[2][0], tri_pts[2][1])
                    painter.drawLine(tri_pts[2][0], tri_pts[2][1], tri_pts[0][0], tri_pts[0][1])
                
                else: # Clutch Hand Highlights
                    painter.setPen(QPen(highlight_color, 2))
                    painter.setBrush(highlight_color)
                    for idx in [4, 8]: # Thumb and Index Tips
                        lm = hand_landmarks[idx]
                        px = int(lm.x * scaled_pixmap.width()) + x_off
                        py = int(lm.y * scaled_pixmap.height()) + y_off
                        painter.drawEllipse(px-4, py-4, 8, 8)

                # 2.3 Label
                wrist = hand_landmarks[0]
                wx = int(wrist.x * scaled_pixmap.width()) + x_off
                wy = int(wrist.y * scaled_pixmap.height()) + y_off
                painter.setPen(base_color)
                painter.drawText(wx, wy - 20, label)

        # 3. Draw Tactical HUD
        painter.setPen(QPen(self.color_hud, 2))
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        
        # HUD Corners
        margin = 20
        painter.drawText(x_off + margin, y_off + margin + 20, f"MODE: {self.mode}")
        
        # Clutch Indicator
        if self.clutch_active:
            painter.setBrush(self.color_clutch)
            painter.drawEllipse(x_off + scaled_pixmap.width() - 40, y_off + margin, 20, 20)
            painter.drawText(x_off + scaled_pixmap.width() - 140, y_off + margin + 15, "CLUTCH ENGAGED")
