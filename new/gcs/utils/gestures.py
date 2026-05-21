import math

class HandChassis:
    """
    Translates MediaPipe Hand Landmarks into normalized drone control signals.
    Uses the "Super-Triangle": Wrist (0), Thumb Tip (4), Pinky Tip (20).
    """
    def __init__(self, clutch_threshold=0.05):
        self.clutch_threshold = clutch_threshold
        
        # Neutral offsets (captured on clutch engagement)
        self.neutral_y = 0.0
        self.neutral_pitch = 0.0
        self.neutral_roll = 0.0
        self.neutral_yaw = 0.0
        
        self.is_engaged = False

    def get_clutch_state(self, all_hands_landmarks, handedness_results):
        """
        Looks for the 'Okay' pinch (Thumb 4 to Index 8).
        In mirrored view:
        - Physical Left Hand (Clutch) is detected as 'Right'.
        - Physical Right Hand (Flight) is detected as 'Left'.
        """
        for idx, hand in enumerate(all_hands_landmarks):
            side = handedness_results[idx][0].category_name
            if side == "Right": # Physical Left Hand
                t_tip = hand[4]
                i_tip = hand[8]
                dist = math.sqrt((t_tip.x-i_tip.x)**2 + (t_tip.y-i_tip.y)**2)
                return dist < self.clutch_threshold
        return False

    def set_neutral(self, landmarks):
        """Captures the current hand state as the 'Zero' point."""
        self.neutral_y = landmarks[0].y
        self.neutral_pitch = self._calculate_raw_pitch(landmarks)
        self.neutral_roll = self._calculate_raw_roll(landmarks)
        self.neutral_yaw = self._calculate_raw_yaw(landmarks)
        self.is_engaged = True

    def _calculate_raw_pitch(self, lm):
        # Lean: Center of Thumb/Pinky line vs Wrist Z
        mid_z = (lm[4].z + lm[20].z) / 2.0
        return mid_z - lm[0].z

    def _calculate_raw_roll(self, lm):
        # Wave: Pinky Y minus Thumb Y. 
        # Tilting right (CW) -> Pinky moves down (larger Y), Thumb moves up (smaller Y).
        # result: positive.
        return lm[20].y - lm[4].y

    def _calculate_raw_yaw(self, lm):
        # Screwdriver: Thumb Z minus Pinky Z.
        # Rotating right (CW) -> Thumb moves away (larger Z), Pinky moves toward (smaller Z).
        # result: positive.
        return lm[4].z - lm[20].z

    def get_controls(self, landmarks):
        """Returns normalized deltas relative to neutral."""
        if not self.is_engaged:
            return 0.0, 0.0, 0.0, 0.0

        throttle_delta = self.neutral_y - landmarks[0].y
        pitch_delta = self._calculate_raw_pitch(landmarks) - self.neutral_pitch
        roll_delta = self._calculate_raw_roll(landmarks) - self.neutral_roll
        yaw_delta = self._calculate_raw_yaw(landmarks) - self.neutral_yaw

        return throttle_delta, pitch_delta, roll_delta, yaw_delta

class HandChassisAdvanced(HandChassis):
    """
    Advanced version of HandChassis with Deadzone support.
    """
    def __init__(self, clutch_threshold=0.05, deadzone=0.02):
        super().__init__(clutch_threshold)
        self.deadzone = deadzone

    def _apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        return value

    def get_controls(self, landmarks):
        """Returns normalized deltas relative to neutral with deadzone applied."""
        dt, dp, dr, dy = super().get_controls(landmarks)
        
        # Apply deadzone to R, P, Y (Throttle usually doesn't need it as much)
        dp = self._apply_deadzone(dp)
        dr = self._apply_deadzone(dr)
        dy = self._apply_deadzone(dy)
        
        return dt, dp, dr, dy
