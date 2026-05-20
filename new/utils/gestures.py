import math

class HandChassis:
    """
    Translates MediaPipe Hand Landmarks into normalized drone control signals.
    Uses the triangle: Wrist (0), Index Knuckle (5), Pinky Knuckle (17).
    """
    def __init__(self, clutch_threshold=0.06):
        self.clutch_threshold = clutch_threshold
        
        # Neutral offsets (captured on clutch engagement)
        self.neutral_y = 0.0
        self.neutral_pitch = 0.0
        self.neutral_roll = 0.0
        self.neutral_yaw = 0.0
        
        self.is_engaged = False

    def get_clutch_state(self, landmarks):
        """Checks if Thumb (4) and Pinky (20) are pinched."""
        t_tip = landmarks[4]
        p_tip = landmarks[20]
        
        dist = math.sqrt(
            (t_tip.x - p_tip.x)**2 + 
            (t_tip.y - p_tip.y)**2 + 
            (t_tip.z - p_tip.z)**2
        )
        return dist < self.clutch_threshold

    def set_neutral(self, landmarks):
        """Captures the current hand state as the 'Zero' point."""
        self.neutral_y = landmarks[0].y
        self.neutral_pitch = self._calculate_raw_pitch(landmarks)
        self.neutral_roll = self._calculate_raw_roll(landmarks)
        self.neutral_yaw = self._calculate_raw_yaw(landmarks)
        self.is_engaged = True

    def _calculate_raw_pitch(self, lm):
        # Lean: Average Z of knuckles vs Wrist Z
        knuckle_z = (lm[5].z + lm[17].z) / 2.0
        return knuckle_z - lm[0].z

    def _calculate_raw_roll(self, lm):
        # Wave: Y-difference between Index and Pinky knuckles
        return lm[5].y - lm[17].y

    def _calculate_raw_yaw(self, lm):
        # Screwdriver: Z-difference between Index and Pinky knuckles
        return lm[5].z - lm[17].z

    def get_controls(self, landmarks):
        """
        Returns normalized deltas (-1.0 to 1.0) relative to neutral.
        """
        if not self.is_engaged:
            return 0.0, 0.0, 0.0, 0.0

        # 1. Throttle (Wrist Y) - Up is lower Y in screen space, so we invert
        throttle_delta = self.neutral_y - landmarks[0].y
        
        # 2. Pitch (Lean)
        pitch_delta = self._calculate_raw_pitch(landmarks) - self.neutral_pitch
        
        # 3. Roll (Wave)
        roll_delta = self._calculate_raw_roll(landmarks) - self.neutral_roll
        
        # 4. Yaw (Screwdriver)
        yaw_delta = self._calculate_raw_yaw(landmarks) - self.neutral_yaw

        return throttle_delta, pitch_delta, roll_delta, yaw_delta
