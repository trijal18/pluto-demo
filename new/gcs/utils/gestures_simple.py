import math

class SimpleOneHandController:
    """
    Translates simple one-handed MediaPipe gestures into discrete drone commands
    and target RC values.
    """
    def __init__(self, finger_threshold=1.15, tilt_threshold=0.08):
        self.finger_threshold = finger_threshold
        self.tilt_threshold = tilt_threshold
        self.is_armed = False

    def get_finger_extensions(self, landmarks):
        """
        Returns a list of 5 booleans indicating if each finger is extended.
        Indices: 0=Thumb, 1=Index, 2=Middle, 3=Ring, 4=Pinky
        """
        extended = []
        
        def d(pt1, pt2):
            return math.sqrt((pt1.x - pt2.x)**2 + (pt1.y - pt2.y)**2 + (pt1.z - pt2.z)**2)
            
        wrist = landmarks[0]
        
        # Thumb check: compare distance from thumb tip (4) to index MCP (5)
        # against thumb MCP (2) to index MCP (5)
        thumb_dist = d(landmarks[4], landmarks[5])
        thumb_ref = d(landmarks[2], landmarks[5])
        is_thumb_ext = thumb_dist > thumb_ref * 1.15
        extended.append(is_thumb_ext)
        
        # Index (8 vs 5)
        is_index_ext = d(landmarks[8], wrist) > d(landmarks[5], wrist) * self.finger_threshold
        extended.append(is_index_ext)
        
        # Middle (12 vs 9)
        is_middle_ext = d(landmarks[12], wrist) > d(landmarks[9], wrist) * self.finger_threshold
        extended.append(is_middle_ext)
        
        # Ring (16 vs 13)
        is_ring_ext = d(landmarks[16], wrist) > d(landmarks[13], wrist) * self.finger_threshold
        extended.append(is_ring_ext)
        
        # Pinky (20 vs 17)
        is_pinky_ext = d(landmarks[20], wrist) > d(landmarks[17], wrist) * self.finger_threshold
        extended.append(is_pinky_ext)
        
        return extended

    def get_controls(self, landmarks, handedness_label):
        """
        Analyzes the hand state and returns:
          - command: "ARM_TAKEOFF", "DISARM", "HOVER", "UP", "DOWN", "LEFT", "RIGHT", "FORWARD", "BACKWARD", "YAW_LEFT", "YAW_RIGHT"
          - rc_values: tuple (roll, pitch, throttle, yaw)
        """
        extended = self.get_finger_extensions(landmarks)
        ext_count = extended.count(True)
        
        # Default neutral values
        roll, pitch, throttle, yaw = 1500, 1500, 1500, 1500
        command = "HOVER"
        
        # 1. Fist (0 fingers extended) -> Disarm
        # (We also check if index, middle, ring, pinky are all curled for safety)
        if ext_count == 0 or not any(extended[1:]):
            command = "DISARM"
            return command, (1500, 1500, 1300, 1500) # Throttled down
            
        # 2. Thumbs Up / Down (Only Thumb extended)
        if extended[0] and not any(extended[1:]):
            # Check pointing direction of thumb: tip 4 vs joint 3 vs joint 2
            is_up = landmarks[4].y < landmarks[3].y < landmarks[2].y
            is_down = landmarks[4].y > landmarks[3].y > landmarks[2].y
            if is_up:
                command = "ARM_TAKEOFF"
                # Keep neutral RC values, the main application will trigger drone arming & takeoff
                return command, (1500, 1500, 1500, 1500)
            elif is_down:
                command = "DOWN"
                return command, (1500, 1500, 1350, 1500) # Descend/Land
        
        # 3. 1 Finger Extended (Index only) -> Up, Down, Left, Right
        if extended[1] and not any(extended[2:]):
            # Vector from Index MCP (5) to Index Tip (8)
            dx = landmarks[8].x - landmarks[5].x
            dy = landmarks[8].y - landmarks[5].y
            
            if abs(dy) > abs(dx):
                if dy < 0:
                    command = "UP"
                    throttle = 1650
                else:
                    command = "DOWN"
                    throttle = 1350
            else:
                if dx < 0:
                    command = "LEFT"
                    roll = 1350
                else:
                    command = "RIGHT"
                    roll = 1650
                    
            return command, (roll, pitch, throttle, yaw)
            
        # 4. 2 Fingers Extended (Index + Middle) -> Go Forward
        if extended[1] and extended[2] and not extended[3] and not extended[4]:
            command = "FORWARD"
            pitch = 1650
            return command, (roll, pitch, throttle, yaw)
            
        # 5. 3 Fingers Extended (Index + Middle + Ring) -> Go Backward
        if extended[1] and extended[2] and extended[3] and not extended[4]:
            command = "BACKWARD"
            pitch = 1350
            return command, (roll, pitch, throttle, yaw)
            
        # 6. 5 Fingers Extended (Palm) -> Hover or Yaw Wave
        if extended[1] and extended[2] and extended[3] and extended[4]:
            # Roll tilt calculation
            tilt = landmarks[20].y - landmarks[4].y
            # If hand is physical left (MediaPipe "Right"), invert the tilt
            if handedness_label == "Right":
                tilt = -tilt
                
            if tilt > self.tilt_threshold:
                command = "YAW_RIGHT"
                yaw = 1650
            elif tilt < -self.tilt_threshold:
                command = "YAW_LEFT"
                yaw = 1350
            else:
                command = "HOVER"
                
            return command, (roll, pitch, throttle, yaw)
            
        return command, (roll, pitch, throttle, yaw)
