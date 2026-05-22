import math


class SimpleOneHandController:
    """
    One-Hand Gesture Drone Controller

    Gesture Map
    ------------------------------------------------
    👍 Thumbs Up              -> ARM / TAKEOFF
    ✊ Closed Fist            -> DISARM

    ☝️ Index Up               -> UP
    👇 Index Down             -> DOWN

    ✌️ Index + Middle         -> FORWARD
    🤟 Index + Middle + Ring -> BACKWARD

    🤏 Thumb + Index          -> LEFT
    🤘 Index + Pinky          -> RIGHT

    🖐️ Four Fingers Wave      -> YAW LEFT / RIGHT
    """

    def __init__(
        self,
        finger_threshold=1.15,
        tilt_threshold=0.08
    ):
        self.finger_threshold = finger_threshold
        self.tilt_threshold = tilt_threshold

    # =========================================================
    # Utility Distance Function
    # =========================================================
    def distance(self, pt1, pt2):
        return math.sqrt(
            (pt1.x - pt2.x) ** 2 +
            (pt1.y - pt2.y) ** 2 +
            (pt1.z - pt2.z) ** 2
        )

    # =========================================================
    # Finger Extension Detection
    # =========================================================
    def get_finger_extensions(self, landmarks):
        """
        Returns:
            [thumb, index, middle, ring, pinky]

        True  = extended
        False = curled
        """

        extended = []

        wrist = landmarks[0]

        # -----------------------------------------------------
        # THUMB
        # -----------------------------------------------------
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        index_mcp = landmarks[5]

        thumb_dist = self.distance(thumb_tip, index_mcp)
        thumb_ref = self.distance(thumb_mcp, index_mcp)

        thumb_extended = (
            thumb_dist > thumb_ref * 1.15
        )

        extended.append(thumb_extended)

        # -----------------------------------------------------
        # OTHER FINGERS
        # -----------------------------------------------------
        finger_pairs = [
            (8, 5),    # Index
            (12, 9),   # Middle
            (16, 13),  # Ring
            (20, 17)   # Pinky
        ]

        for tip_idx, mcp_idx in finger_pairs:

            tip = landmarks[tip_idx]
            mcp = landmarks[mcp_idx]

            tip_dist = self.distance(tip, wrist)
            mcp_dist = self.distance(mcp, wrist)

            is_extended = (
                tip_dist >
                mcp_dist * self.finger_threshold
            )

            extended.append(is_extended)

        return extended

    # =========================================================
    # Main Gesture Controller
    # =========================================================
    def get_controls(self, landmarks, handedness_label="Right"):
        """
        Returns:
            command, (roll, pitch, throttle, yaw)

        RC Neutral:
            1500

        RC Low:
            1350

        RC High:
            1650
        """

        extended = self.get_finger_extensions(landmarks)

        thumb, index, middle, ring, pinky = extended

        # -----------------------------------------------------
        # Default Neutral RC
        # -----------------------------------------------------
        roll = 1500
        pitch = 1500
        throttle = 1500
        yaw = 1500

        command = "HOVER"

        # =====================================================
        # 1. DISARM -> Closed Fist
        # =====================================================
        if not any(extended):

            command = "DISARM"

            return command, (
                1500,
                1500,
                1300,
                1500
            )

        # =====================================================
        # 2. ARM / TAKEOFF -> Thumbs Up
        # =====================================================
        if (
            thumb and
            not index and
            not middle and
            not ring and
            not pinky
        ):

            # Thumb pointing upward
            is_up = (
                landmarks[4].y <
                landmarks[3].y <
                landmarks[2].y
            )

            if is_up:

                command = "ARM_TAKEOFF"

                return command, (
                    1500,
                    1500,
                    1500,
                    1500
                )

        # =====================================================
        # 3. INDEX ONLY -> UP / DOWN
        # =====================================================
        if (
            index and
            not thumb and
            not middle and
            not ring and
            not pinky
        ):

            dy = (
                landmarks[8].y -
                landmarks[5].y
            )

            # Smaller Y = upward on screen
            if dy < 0:

                command = "UP"

                throttle = 1650

            else:

                command = "DOWN"

                throttle = 1350

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # 4. TWO FINGERS -> FORWARD
        # Index + Middle
        # =====================================================
        if (
            index and
            middle and
            not ring and
            not pinky
        ):

            command = "FORWARD"

            pitch = 1650

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # 5. THREE FINGERS -> BACKWARD
        # Index + Middle + Ring
        # =====================================================
        if (
            index and
            middle and
            ring and
            not pinky
        ):

            command = "BACKWARD"

            pitch = 1350

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # 6. THUMB + INDEX -> LEFT
        # =====================================================
        if (
            thumb and
            index and
            not middle and
            not ring and
            not pinky
        ):

            command = "LEFT"

            roll = 1350

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # 7. INDEX + PINKY -> RIGHT
        # =====================================================
        if (
            index and
            pinky and
            not middle and
            not ring
        ):

            command = "RIGHT"

            roll = 1650

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # 8. FOUR FINGERS -> YAW
        # (No thumb)
        # =====================================================
        if (
            index and
            middle and
            ring and
            pinky and
            not thumb
        ):

            # Hand tilt estimate
            tilt = (
                landmarks[20].y -
                landmarks[8].y
            )

            # Compensate handedness
            if handedness_label == "Right":
                tilt = -tilt

            # -----------------------------
            # YAW RIGHT
            # -----------------------------
            if tilt > self.tilt_threshold:

                command = "YAW_RIGHT"

                yaw = 1650

            # -----------------------------
            # YAW LEFT
            # -----------------------------
            elif tilt < -self.tilt_threshold:

                command = "YAW_LEFT"

                yaw = 1350

            else:

                command = "HOVER"

            return command, (
                roll,
                pitch,
                throttle,
                yaw
            )

        # =====================================================
        # Default Hover
        # =====================================================
        return command, (
            roll,
            pitch,
            throttle,
            yaw
        )