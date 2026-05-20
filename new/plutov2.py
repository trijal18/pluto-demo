import socket
import threading
import time
import struct
import logging

# MSP V1 Constants
MSP_HEADER = b'$M<'
MSP_RESPONSE_HEADER = b'$M>'

# MSP Command IDs
MSP_RAW_IMU = 102
MSP_RC = 105
MSP_ATTITUDE = 108
MSP_ALTITUDE = 109
MSP_ANALOG = 110
MSP_SET_RAW_RC = 200
MSP_ACC_CALIBRATION = 205
MSP_ACC_TRIM = 240
MSP_SET_COMMAND = 217

# Pluto Command Types (for MSP_SET_COMMAND)
CMD_NONE = 0
CMD_TAKE_OFF = 1
CMD_LAND = 2

class PlutoV2:
    def __init__(self, ip='192.168.4.1', port=23):
        self.ip = ip
        self.port = port
        self.client = None
        self.connected = False
        
        # Threading
        self.io_thread = None
        self.lock = threading.Lock()
        
        # Target RC Values (1000-2000)
        # 1500 is neutral for R,P,Y. 1000 is min for Throttle.
        self.target_rc = [1500, 1500, 1000, 1500, 1500, 1000, 1500, 1000]
        self.target_command = CMD_NONE
        
        # Shadow State (Telemetry)
        self.state = {
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'height': 0,
            'battery': 0.0,
            'rssi': 0,
            'rc': [1500] * 8,
            'acc': [0, 0, 0],
            'gyro': [0, 0, 0],
            'last_update': 0
        }
        
        # Watchdog
        self.last_input_time = time.time()
        self.watchdog_timeout = 0.5  # Increased to 500ms for safety
        
        # Telemetry Health
        self.telemetry_lost = False
        self.telemetry_timeout = 1.0  # 1 second
        
        # Logging
        self.logger = logging.getLogger("PlutoV2")
        logging.basicConfig(level=logging.INFO)

    def connect(self):
        """Establishes connection and starts the background I/O thread."""
        if self.connected:
            return
            
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(2.0)
            self.client.connect((self.ip, self.port))
            # Disable Nagle's algorithm for low latency
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client.setblocking(False)
            
            self.connected = True
            self.logger.info(f"Connected to Pluto at {self.ip}:{self.port}")
            
            # Send the initial trim packet as seen in original lib
            self.client.sendall(self._create_packet(MSP_ACC_TRIM, b''))
            
            self.io_thread = threading.Thread(target=self._io_loop, daemon=True)
            self.io_thread.start()
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.connected = False

    def disconnect(self):
        """Safely lands (if requested) and closes the connection."""
        self.logger.info("Disconnecting...")
        self.connected = False
        if self.io_thread:
            self.io_thread.join(timeout=1.0)
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.logger.info("Disconnected.")

    def _clamp(self, val, min_val=1000, max_val=2000):
        return max(min_val, min(max_val, int(val)))

    def set_rc(self, roll=None, pitch=None, yaw=None, throttle=None, aux1=None, aux2=None, aux3=None, aux4=None):
        """
        Updates target RC values. Values should be 1000-2000.
        Resets the safety watchdog.
        """
        with self.lock:
            if roll is not None:     self.target_rc[0] = self._clamp(roll)
            if pitch is not None:    self.target_rc[1] = self._clamp(pitch)
            if throttle is not None: self.target_rc[2] = self._clamp(throttle)
            if yaw is not None:      self.target_rc[3] = self._clamp(yaw)
            if aux1 is not None:     self.target_rc[4] = self._clamp(aux1)
            if aux2 is not None:     self.target_rc[5] = self._clamp(aux2)
            if aux3 is not None:     self.target_rc[6] = self._clamp(aux3)
            if aux4 is not None:     self.target_rc[7] = self._clamp(aux4)
            self.last_input_time = time.time()

    def send_command(self, cmd_type):
        """Sets a discrete command (Takeoff/Land)."""
        with self.lock:
            self.target_command = cmd_type

    def arm(self):
        """Arms the drone."""
        self.logger.info("Arming...")
        # Pluto original lib: rcThrottle=1000, rcAUX4=1500
        self.set_rc(throttle=1000, aux4=1500)

    def disarm(self):
        """Disarms the drone."""
        self.logger.info("Disarming...")
        # Pluto original lib: rcThrottle=1300, rcAUX4=1200
        self.set_rc(throttle=1300, aux4=1200)

    def calibrate_acc(self):
        """Sends the accelerometer calibration command."""
        self.logger.info("Calibrating Accelerometer...")
        self.send_command(MSP_ACC_CALIBRATION)

    def takeoff(self):
        """Sends takeoff sequence as seen in original lib."""
        self.logger.info("Taking off sequence...")
        # 1. Disarm pulse
        self.disarm()
        time.sleep(0.1)
        # 2. Box Arm (High throttle + Arm)
        self.logger.info("Box Arm...")
        self.set_rc(throttle=1800, aux4=1500)
        time.sleep(0.1)
        # 3. Takeoff command
        self.send_command(CMD_TAKE_OFF)

    def land(self):
        """Sends land command."""
        self.logger.info("Landing...")
        self.send_command(CMD_LAND)

    def get_state(self):
        """Returns a copy of the current shadow state."""
        with self.lock:
            return self.state.copy()

    def _create_packet(self, cmd, payload):
        """Creates an MSP V1 packet."""
        size = len(payload)
        checksum = size ^ cmd
        for b in payload:
            checksum ^= b
        return MSP_HEADER + struct.pack('<BB', size, cmd) + payload + struct.pack('<B', checksum)

    def _io_loop(self):
        """Background thread for non-blocking I/O at ~45Hz (matching original lib)."""
        buffer = b''
        
        # Pre-create telemetry request packets
        telemetry_requests = [
            self._create_packet(MSP_RC, b''),
            self._create_packet(MSP_ATTITUDE, b''),
            self._create_packet(MSP_RAW_IMU, b''),
            self._create_packet(MSP_ALTITUDE, b''),
            self._create_packet(MSP_ANALOG, b'')
        ]
        
        while self.connected:
            start_time = time.time()
            
            # 1. Watchdog & Telemetry Health Checks
            now = time.time()
            with self.lock:
                if now - self.last_input_time > self.watchdog_timeout:
                    # Fail-safe: Neutral hover
                    self.target_rc[0] = 1500
                    self.target_rc[1] = 1500
                    self.target_rc[2] = 1500
                    self.target_rc[3] = 1500
                
                if now - self.state['last_update'] > self.telemetry_timeout and self.state['last_update'] > 0:
                    if not self.telemetry_lost:
                        self.logger.warning("Telemetry stream timed out.")
                        self.telemetry_lost = True
                else:
                    self.telemetry_lost = False
            
            try:
                # 2. Send RC Packet
                with self.lock:
                    rc_payload = struct.pack('<8H', *self.target_rc)
                    rc_packet = self._create_packet(MSP_SET_RAW_RC, rc_payload)
                    self.client.sendall(rc_packet)
                    
                    if self.target_command != CMD_NONE:
                        cmd_packet = self._create_packet(MSP_SET_COMMAND, struct.pack('<B', self.target_command))
                        self.client.sendall(cmd_packet)
                        self.target_command = CMD_NONE

                # 3. Request Telemetry (Iterative to avoid buffer pressure)
                for req in telemetry_requests:
                    self.client.sendall(req)

                # 4. Read & Parse Responses
                # Loop a few times to drain the socket buffer
                for _ in range(5):
                    try:
                        data = self.client.recv(2048)
                        if data:
                            buffer += data
                        else:
                            break # Connection closed
                    except (BlockingIOError, socket.timeout):
                        break
                
                if buffer:
                    buffer = self._parse_buffer(buffer)

            except Exception as e:
                self.logger.error(f"Critical I/O Loop Error: {e}")
                self.connected = False
                break

            # Maintain ~45Hz (matching original lib's 22ms)
            elapsed = time.time() - start_time
            sleep_time = 0.022 - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _parse_buffer(self, buffer):
        """Robustly parses the byte buffer for MSP response packets."""
        while len(buffer) >= 6:
            idx = buffer.find(MSP_RESPONSE_HEADER)
            if idx == -1:
                return b''
            
            if idx > 0:
                buffer = buffer[idx:]
            
            if len(buffer) < 6:
                return buffer
            
            payload_size = buffer[3]
            cmd = buffer[4]
            total_size = 6 + payload_size
            
            if len(buffer) < total_size:
                return buffer
            
            payload = buffer[5:5+payload_size]
            checksum = buffer[5+payload_size]
            
            calc_checksum = payload_size ^ cmd
            for b in payload:
                calc_checksum ^= b
            
            if calc_checksum == checksum:
                self._handle_payload(cmd, payload)
                buffer = buffer[total_size:]
            else:
                buffer = buffer[1:]
            
        return buffer

    def _handle_payload(self, cmd, payload):
        """Updates internal state based on parsed MSP payloads."""
        with self.lock:
            try:
                if cmd == MSP_ATTITUDE:
                    r, p, y = struct.unpack('<hhh', payload)
                    self.state['roll'] = r / 10.0
                    self.state['pitch'] = p / 10.0
                    self.state['yaw'] = y / 10.0
                elif cmd == MSP_ALTITUDE:
                    h, v = struct.unpack('<ih', payload)
                    self.state['height'] = h
                elif cmd == MSP_ANALOG:
                    vbat = payload[0]
                    self.state['battery'] = vbat / 10.0
                    if len(payload) >= 5:
                        self.state['rssi'] = struct.unpack('<H', payload[3:5])[0]
                elif cmd == MSP_RC:
                    self.state['rc'] = list(struct.unpack('<8H', payload))
                elif cmd == MSP_RAW_IMU:
                    # 9 int16s: accX, accY, accZ, gyroX, gyroY, gyroZ, magX, magY, magZ
                    imu_data = struct.unpack('<9h', payload[:18])
                    self.state['acc'] = list(imu_data[0:3])
                    self.state['gyro'] = list(imu_data[3:6])
                
                self.state['last_update'] = time.time()
            except Exception as e:
                self.logger.debug(f"Payload parse error for cmd {cmd}: {e}")

    def _handle_payload(self, cmd, payload):
        """Updates internal state based on parsed MSP payloads."""
        with self.lock:
            try:
                if cmd == MSP_ATTITUDE:
                    # Roll, Pitch, Yaw are int16 in 0.1 degree steps
                    r, p, y = struct.unpack('<hhh', payload)
                    self.state['roll'] = r / 10.0
                    self.state['pitch'] = p / 10.0
                    self.state['yaw'] = y / 10.0
                elif cmd == MSP_ALTITUDE:
                    # Height (int32 cm), Vario (int16)
                    h, v = struct.unpack('<ih', payload)
                    self.state['height'] = h
                elif cmd == MSP_ANALOG:
                    # Vbat (uint8), Power (uint16), RSSI (uint16), Amperage (uint16)
                    vbat = payload[0]
                    self.state['battery'] = vbat / 10.0
                    if len(payload) >= 5:
                        self.state['rssi'] = struct.unpack('<H', payload[3:5])[0]
                elif cmd == MSP_RC:
                    # 8 channels of uint16
                    self.state['rc'] = list(struct.unpack('<8H', payload))
                
                self.state['last_update'] = time.time()
            except Exception as e:
                self.logger.debug(f"Payload parse error for cmd {cmd}: {e}")

# --- Simple Standalone Test ---
if __name__ == "__main__":
    drone = PlutoV2()
    drone.connect()
    try:
        while drone.connected:
            print(f"\rState: {drone.get_state()}", end="")
            time.sleep(0.1)
    except KeyboardInterrupt:
        drone.disconnect()
