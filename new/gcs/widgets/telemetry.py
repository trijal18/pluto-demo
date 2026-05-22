from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRect

class VUMeter(QWidget):
    def __init__(self, label="CH", min_val=1000, max_val=2000, initial_val=1000, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val
        self.setMinimumWidth(55)
        self.setMinimumHeight(120)

    def set_value(self, val):
        self.current_val = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # Draw Label & Value (Smaller fonts to fit width)
        painter.setPen(QColor(0, 255, 255))
        painter.setFont(QFont("Consolas", 8))
        painter.drawText(5, 15, self.label_text)
        
        # Dynamic color based on value
        color = QColor(0, 255, 100)
        if self.current_val > 1800: color = QColor(255, 0, 0)
        elif self.current_val > 1600: color = QColor(255, 255, 0)
        
        painter.setPen(color)
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(5, 35, str(int(self.current_val)))

        # Draw VU Segments
        margin = 5
        meter_top = 45
        meter_bottom = self.height() - margin
        meter_height = meter_bottom - meter_top
        
        num_segments = 12
        seg_height = (meter_height // num_segments) - 2
        
        # Calculate how many segments to light up
        normalized = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        lit_segments = int(normalized * num_segments)
        
        for i in range(num_segments):
            y = meter_bottom - (i + 1) * (seg_height + 2)
            
            # Segment color
            if i < lit_segments:
                if i > 12: seg_color = QColor(255, 0, 0)
                elif i > 9: seg_color = QColor(255, 255, 0)
                else: seg_color = QColor(0, 255, 100)
            else:
                seg_color = QColor(50, 50, 50) # Dimmed
                
            painter.fillRect(margin, y, self.width() - 2 * margin, seg_height, seg_color)

class TelemetryRack(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self) # Changed to vertical for grouping
        self.layout.setSpacing(10)
        
        # 1. RC Gauges (Horizontal)
        self.rc_group = QWidget()
        self.rc_layout = QHBoxLayout(self.rc_group)
        self.rc_layout.setContentsMargins(0, 0, 0, 0)
        self.meters = {
            'roll': VUMeter("ROLL", initial_val=1500),
            'pitch': VUMeter("PITCH", initial_val=1500),
            'throttle': VUMeter("THROTTLE", initial_val=1000),
            'yaw': VUMeter("YAW", initial_val=1500)
        }
        for m in self.meters.values():
            self.rc_layout.addWidget(m)
        self.layout.addWidget(self.rc_group)
            
        # 2. System Stats Area
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        
        # Battery Section
        self.bat_row = QHBoxLayout()
        self.lbl_bat = QLabel("BAT: 0.00V")
        self.lbl_soc = QLabel("100%")
        self.lbl_soc.setStyleSheet("color: #0f0; font-family: Consolas; font-size: 14px; font-weight: bold;")
        self.bat_row.addWidget(self.lbl_bat)
        self.bat_row.addStretch()
        self.bat_row.addWidget(self.lbl_soc)
        self.stats_layout.addLayout(self.bat_row)
        
        # Amperage & RSSI Section
        self.extra_row = QHBoxLayout()
        self.lbl_amp = QLabel("0 mA")
        self.lbl_rssi = QLabel("RSSI: 0")
        self.extra_row.addWidget(self.lbl_amp)
        self.extra_row.addStretch()
        self.extra_row.addWidget(self.lbl_rssi)
        self.stats_layout.addLayout(self.extra_row)
        
        # Heartbeat & Link Status
        self.status_row = QHBoxLayout()
        self.lbl_heartbeat = QLabel("●") # Heartbeat LED
        self.lbl_heartbeat.setStyleSheet("color: #555; font-size: 18px;")
        self.lbl_link = QLabel("LINK: OFFLINE")
        self.lbl_wd = QLabel("WATCHDOG")
        self.lbl_wd.setStyleSheet("color: #555; font-family: Consolas; font-size: 11px; font-weight: bold; background: #222; padding: 2px;")
        self.status_row.addWidget(self.lbl_heartbeat)
        self.status_row.addWidget(self.lbl_link)
        self.status_row.addWidget(self.lbl_wd)
        self.status_row.addStretch()
        self.stats_layout.addLayout(self.status_row)
        
        for lbl in [self.lbl_bat, self.lbl_rssi, self.lbl_amp, self.lbl_link]:
            lbl.setStyleSheet("color: #0ff; font-family: Consolas; font-size: 11px; font-weight: bold;")
            
        self.layout.addWidget(self.stats_widget)
        self.heartbeat_state = False

    def update_telemetry(self, state):
        # Update RC meters
        rc = state.get('rc', [1500]*8)
        self.meters['roll'].set_value(rc[0])
        self.meters['pitch'].set_value(rc[1])
        self.meters['throttle'].set_value(rc[2])
        self.meters['yaw'].set_value(rc[3])
        
        # Update Power Stats
        v = state.get('battery', 0.0)
        soc = state.get('battery_percentage', 0)
        amp = state.get('amperage', 0)
        rssi = state.get('rssi', 0)
        wd = state.get('watchdog_active', False)
        
        self.lbl_bat.setText(f"BAT: {v:.2f}V")
        self.lbl_soc.setText(f"{soc}%")
        self.lbl_amp.setText(f"{amp} mA")
        self.lbl_rssi.setText(f"RSSI: {rssi}")
        
        # Watchdog Status
        if wd:
            self.lbl_wd.setStyleSheet("color: #fff; font-family: Consolas; font-size: 11px; font-weight: bold; background: #f00; padding: 2px;")
        else:
            self.lbl_wd.setStyleSheet("color: #555; font-family: Consolas; font-size: 11px; font-weight: bold; background: #222; padding: 2px;")
        
        # Battery Health Color
        if v < 3.4 or soc < 20: self.lbl_soc.setStyleSheet("color: #f00; font-family: Consolas; font-size: 14px; font-weight: bold;")
        elif v < 3.6 or soc < 40: self.lbl_soc.setStyleSheet("color: #ff0; font-family: Consolas; font-size: 14px; font-weight: bold;")
        else: self.lbl_soc.setStyleSheet("color: #0f0; font-family: Consolas; font-size: 14px; font-weight: bold;")

        # Heartbeat & Telemetry Loss
        tele_lost = state.get('telemetry_lost', False)
        if tele_lost:
            self.lbl_heartbeat.setStyleSheet("color: #f00; font-size: 18px;")
            self.lbl_link.setText("LINK: DATA LOST")
            self.lbl_link.setStyleSheet("color: #f00; font-family: Consolas; font-size: 11px; font-weight: bold;")
        else:
            self.heartbeat_state = not self.heartbeat_state
            color = "#0f0" if self.heartbeat_state else "#050"
            self.lbl_heartbeat.setStyleSheet(f"color: {color}; font-size: 18px;")
            self.lbl_link.setText("LINK: ACTIVE")
            self.lbl_link.setStyleSheet("color: #0f0; font-family: Consolas; font-size: 11px; font-weight: bold;")
