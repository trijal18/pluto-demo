import sys
import os
import time
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

# Add parent directory to path to import plutov2
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from plutov2 import PlutoV2, CMD_NONE, CMD_TAKE_OFF, CMD_LAND

class DroneWorker(QThread):
    telemetry_signal = pyqtSignal(dict)
    connection_signal = pyqtSignal(bool)

    def __init__(self, ip='192.168.4.1', port=23):
        super().__init__()
        self.drone = PlutoV2(ip=ip, port=port)
        self._run_flag = True
        self.target_rc = [1500, 1500, 1000, 1500, 1500, 1000, 1500, 1000]

    def run(self):
        """Monitor telemetry and connection state"""
        while self._run_flag:
            if self.drone.connected:
                state = self.drone.get_state()
                self.telemetry_signal.emit(state)
            
            # Connection status check
            self.connection_signal.emit(self.drone.connected)
            
            self.msleep(50) # 20Hz UI update for smoothness

    def connect_drone(self):
        if not self.drone.connected:
            self.drone.connect()
            return self.drone.connected
        return True

    def disconnect_drone(self):
        if self.drone.connected:
            self.drone.disconnect()

    def set_rc(self, roll=None, pitch=None, throttle=None, yaw=None, aux1=None, aux2=None, aux3=None, aux4=None):
        if self.drone.connected:
            self.drone.set_rc(roll, pitch, yaw, throttle, aux1, aux2, aux3, aux4)

    def arm(self):
        if self.drone.connected:
            self.drone.arm()

    def disarm(self):
        if self.drone.connected:
            self.drone.disarm()

    def takeoff(self):
        if self.drone.connected:
            self.drone.takeoff()

    def land(self):
        if self.drone.connected:
            self.drone.land()

    def calibrate(self):
        if self.drone.connected:
            self.drone.calibrate_acc()

    def calibrate_mag(self):
        if self.drone.connected:
            self.drone.calibrate_mag()

    def save_config(self):
        if self.drone.connected:
            self.drone.save_config()

    def flip(self, direction):
        if self.drone.connected:
            self.drone.flip(direction)

    def stop(self):
        self._run_flag = False
        self.disconnect_drone()
        self.wait()
