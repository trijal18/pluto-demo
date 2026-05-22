import cv2
import mediapipe as mp
import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import mediapipe as mp
import time
import sys
import os
import math

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plutov2 import PlutoV2, CMD_NONE, CMD_TAKE_OFF, CMD_LAND

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- Embedded Legacy Utilities (Isolating from GCS Module) ---

class LowPassFilter:
    def __init__(self, alpha=0.35, initial_value=1500):
        self.alpha = alpha
        self.value = initial_value
    def apply(self, new_value):
        self.value = (self.alpha * new_value) + (1 - self.alpha) * self.value
        return int(self.value)

class HandChassis:
    def __init__(self, clutch_threshold=0.05):
        self.clutch_threshold = clutch_threshold
        self.neutral_throttle_y = 0.0
        self.neutral_pitch_y = 0.0
        self.neutral_roll = 0.0
        self.neutral_yaw = 0.0
        self.is_engaged = False

    def get_clutch_state(self, all_hands_landmarks, handedness_results):
        for idx, hand in enumerate(all_hands_landmarks):
            side = handedness_results[idx][0].category_name
            if side == "Right": # Physical Left Hand
                t_tip = hand[4]
                i_tip = hand[8]
                dist = math.sqrt((t_tip.x-i_tip.x)**2 + (t_tip.y-i_tip.y)**2)
                return dist < self.clutch_threshold
        return False

    def set_neutral(self, flight_hand, clutch_hand):
        if flight_hand:
            self.neutral_pitch_y = flight_hand[0].y # Right Wrist Y for Pitch
            self.neutral_roll = self._calculate_raw_roll(flight_hand) # Right wave slope for Roll
        if clutch_hand:
            self.neutral_throttle_y = clutch_hand[0].y # Left Wrist Y for Throttle
            self.neutral_yaw = self._calculate_raw_roll(clutch_hand) # Left wave slope for Yaw
        self.is_engaged = True

    def _calculate_raw_roll(self, lm):
        return lm[20].y - lm[4].y

    def get_decoupled_controls(self, flight_hand, clutch_hand):
        if not self.is_engaged or not flight_hand:
            return 0.0, 0.0, 0.0, 0.0
        
        # Right hand: Pitch & Roll
        pitch_delta = self.neutral_pitch_y - flight_hand[0].y
        roll_delta = self._calculate_raw_roll(flight_hand) - self.neutral_roll
        
        # Left hand: Throttle & Yaw
        throttle_delta = 0.0
        yaw_delta = 0.0
        if clutch_hand:
            throttle_delta = self.neutral_throttle_y - clutch_hand[0].y
            yaw_delta = self._calculate_raw_roll(clutch_hand) - self.neutral_yaw
            
        return roll_delta, pitch_delta, throttle_delta, yaw_delta

# --- Constants ---
MODEL_PATH = "hand_landmarker.task"
ALPHA = 0.20  # Cinematic Smoothing

# Sensitivities (Higher = faster response to smaller movements)
SENS_THROTTLE = 1200.0  # Wrist Y movement
SENS_ROLL     = 2500.0  # Wave slope
SENS_PITCH    = 3000.0  # Wrist Y translation
SENS_YAW      = 2500.0  # Wave slope (Left hand)

def clamp_rc(val):
    return max(1000, min(2000, int(val)))

def main():
    # 1. Initialize Drone
    drone = PlutoV2()
    drone.connect()

    # 2. Initialize MediaPipe (Two Hands)
    import os
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), MODEL_PATH)
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 3. Initialize Utils
    chassis = HandChassis()
    f_roll = LowPassFilter(alpha=ALPHA)
    f_pitch = LowPassFilter(alpha=ALPHA)
    f_yaw = LowPassFilter(alpha=ALPHA)
    f_throttle = LowPassFilter(alpha=ALPHA, initial_value=1000)

    last_throttle = 1000
    is_armed = False

    cap = cv2.VideoCapture(0)
    print("\n" + "="*40)
    print(" PLUTO GCS: TWO-HANDED PRECISION (LEGACY MODE) ")
    print("="*40)
    print("CONTROLS:")
    print(" [A] Arm/Disarm | [L] Land | [Q] Quit")
    print(" [LEFT]  - 'Okay' Pinch to Clutch")
    print(" [RIGHT] - Super-Triangle Flight")
    print("="*40 + "\n")

    with vision.HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: continue

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            result = landmarker.detect(mp_image)

            target_rc = [1500, 1500, last_throttle, 1500] # R, P, T, Y
            clutch_active = False

            if result.hand_landmarks:
                # 1. Check Clutch
                clutch_active = chassis.get_clutch_state(result.hand_landmarks, result.handedness)

                # 2. Find Flight Hand (Physical Right, MediaPipe "Left") and Clutch Hand (Physical Left, MediaPipe "Right")
                right_idx = -1
                left_idx = -1
                for i, hand_info in enumerate(result.handedness):
                    if hand_info[0].category_name == "Left":
                        right_idx = i
                    elif hand_info[0].category_name == "Right":
                        left_idx = i

                # Visual Feedback for All Hands
                for i, landmarks in enumerate(result.hand_landmarks):
                    side = result.handedness[i][0].category_name

                    if side == "Left":
                        color = (255, 0, 255)
                        label = "RIGHT (FLIGHT)"
                    else:
                        color = (0, 255, 0)
                        label = "LEFT (CLUTCH)"

                    # 0. Draw Label
                    wrist_pt = (int(landmarks[0].x * w), int(landmarks[0].y * h) - 20)
                    cv2.putText(frame, label, wrist_pt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                    # 1. Full Skeleton (Thin)
                    connections = [
                        (0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8),
                        (5,9),(9,10),(10,11),(11,12), (9,13),(13,14),(14,15),(15,16),
                        (13,17),(17,18),(18,19),(19,20), (0,17)
                    ]
                    for a, b in connections:
                        pt1 = (int(landmarks[a].x * w), int(landmarks[a].y * h))
                        pt2 = (int(landmarks[b].x * w), int(landmarks[b].y * h))
                        cv2.line(frame, pt1, pt2, color, 1)

                    if side == "Left": # Physical Right
                        # Highlight Super-Triangle (Wrist, Thumb Tip, Pinky Tip)
                        pts = [0, 4, 20]
                        tri_pts = [ (int(landmarks[p].x * w), int(landmarks[p].y * h)) for p in pts ]
                        for pt in tri_pts: cv2.circle(frame, pt, 8, (0, 255, 255), -1)
                        cv2.line(frame, tri_pts[0], tri_pts[1], (0, 255, 255), 2)
                        cv2.line(frame, tri_pts[1], tri_pts[2], (0, 255, 255), 2)
                        cv2.line(frame, tri_pts[2], tri_pts[0], (0, 255, 255), 2)

                    if side == "Right": # Physical Left
                        # Highlight Clutch Pinch
                        t_tip = (int(landmarks[4].x * w), int(landmarks[4].y * h))
                        i_tip = (int(landmarks[8].x * w), int(landmarks[8].y * h))
                        cv2.circle(frame, t_tip, 8, (0, 255, 0), -1)
                        cv2.circle(frame, i_tip, 8, (0, 255, 0), -1)

                if right_idx != -1 and clutch_active:
                    flight_hand = result.hand_landmarks[right_idx]
                    clutch_hand = result.hand_landmarks[left_idx] if left_idx != -1 else None
                    
                    if not chassis.is_engaged:
                        chassis.set_neutral(flight_hand, clutch_hand)
                        print("\n[CLUTCH] Engaged")

                    dr, dp, dt, dy = chassis.get_decoupled_controls(flight_hand, clutch_hand)
                    target_rc[0] = clamp_rc(1500 + (dr * SENS_ROLL))
                    target_rc[1] = clamp_rc(1500 + (dp * SENS_PITCH))
                    target_rc[2] = clamp_rc(last_throttle + (dt * SENS_THROTTLE))
                    target_rc[3] = clamp_rc(1500 + (dy * SENS_YAW))
                elif chassis.is_engaged:
                    chassis.is_engaged = False
                    print("\n[CLUTCH] Released")

            # Apply Smoothing and Update Drone
            roll = f_roll.apply(target_rc[0])
            pitch = f_pitch.apply(target_rc[1])
            throttle = f_throttle.apply(target_rc[2])
            yaw = f_yaw.apply(target_rc[3])

            drone.set_rc(roll=roll, pitch=pitch, throttle=throttle, yaw=yaw)
            if clutch_active: last_throttle = throttle

            # Terminal HUD
            state = drone.get_state()
            sys.stdout.write(f"\rRC: R:{roll} P:{pitch} T:{throttle} Y:{yaw} | Clutch: {'ON ' if clutch_active else 'OFF'} | Bat: {state['battery']}V  ")
            sys.stdout.flush()

            cv2.imshow("Pluto GCS - Camera", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            elif key == ord('a'):
                is_armed = not is_armed
                drone.arm() if is_armed else drone.disarm()
                print(f"\n[COMMAND] {'Armed' if is_armed else 'Disarmed'}")
            elif key == ord('l'):
                drone.land()
                print("\n[COMMAND] Landing")

    drone.disconnect()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
