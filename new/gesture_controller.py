import cv2
import mediapipe as mp
import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plutov2 import PlutoV2, CMD_NONE, CMD_TAKE_OFF, CMD_LAND
from gcs.utils.filters import LowPassFilter, OneEuroFilter
from gcs.utils.gestures import HandChassis, HandChassisAdvanced
import gcs.utils.constants as C

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def clamp_rc(val):
    return max(1000, min(2000, int(val)))

def main():
    # 1. Initialize Drone
    drone = PlutoV2()
    drone.connect()
    
    # 2. Initialize MediaPipe (Two Hands)
    base_options = python.BaseOptions(model_asset_path=C.MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=C.NUM_HANDS,
        min_hand_detection_confidence=C.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=C.MIN_TRACKING_CONFIDENCE
    )
    
    # 3. Initialize Utils
    chassis = HandChassisStandard(clutch_threshold=C.CLUTCH_THRESHOLD, deadzone=C.DEADZONE)
    filters = {
        'roll': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
        'pitch': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
        'yaw': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA),
        'throttle': OneEuroFilter(min_cutoff=C.MC, beta=C.BETA, initial_value=1000)
    }
    
    last_throttle = 1000
    is_armed = False

    cap = cv2.VideoCapture(0)
    print("\n" + "="*40)
    print(" PLUTO GCS: TWO-HANDED PRECISION ")
    print("="*40)
    print("CONTROLS:")
    print(" [A] Arm/Disarm | [L] Land | [Q] Quit")
    print(" [LEFT HAND]  - Throttle & Clutch ('Okay')")
    print(" [RIGHT HAND] - Steering (Roll/Pitch/Yaw)")
    print(" GESTURES: Thumbs Up=Takeoff | Thumbs Down=Land | Fist=STOP")
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
                flight_idx = -1
                clutch_idx = -1
                for i, hand_info in enumerate(result.handedness):
                    if hand_info[0].category_name == "Left": flight_idx = i
                    elif hand_info[0].category_name == "Right": clutch_idx = i

                # Visual Feedback for All Hands
                for i, landmarks in enumerate(result.hand_landmarks):
                    side = result.handedness[i][0].category_name
                    color = (255, 0, 255) if side == "Left" else (0, 255, 0)
                    label = "RIGHT (STEER)" if side == "Left" else "LEFT (ALT/CLUTCH)"
                    
                    # 1. Discrete Gestures
                    if side == "Left" and chassis.detect_stop(landmarks):
                        color = (0, 0, 255)
                        label = "!!! STOP (FIST) !!!"
                        drone.disarm()
                        is_armed = False
                    
                    if side == "Right":
                        if chassis.detect_takeoff(landmarks):
                            color = (0, 255, 255)
                            label = ">>> TAKEOFF <<<"
                            drone.takeoff()
                        elif chassis.detect_land(landmarks):
                            color = (0, 165, 255)
                            label = "<<< LANDING >>>"
                            drone.land()

                    # Draw Skeleton
                    wrist_pt = (int(landmarks[0].x * w), int(landmarks[0].y * h) - 20)
                    cv2.putText(frame, label, wrist_pt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    for a, b in [(0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8), (9,10),(10,11),(11,12), (13,14),(14,15),(15,16), (17,18),(18,19),(19,20), (0,17), (5,9), (9,13), (13,17)]:
                        pt1 = (int(landmarks[a].x * w), int(landmarks[a].y * h))
                        pt2 = (int(landmarks[b].x * w), int(landmarks[b].y * h))
                        cv2.line(frame, pt1, pt2, color, 1)

                # 2. Control Logic
                if clutch_idx != -1:
                    clutch_active = chassis.get_clutch_state([result.hand_landmarks[clutch_idx]], [[result.handedness[clutch_idx][0]]])
                
                if flight_idx != -1 and clutch_idx != -1 and clutch_active:
                    flight_lm = result.hand_landmarks[flight_idx]
                    clutch_lm = result.hand_landmarks[clutch_idx]
                    
                    if not chassis.is_engaged:
                        chassis.set_neutral(flight_lm, clutch_lm)
                        print("\n[CLUTCH] Engaged")
                    
                    dr, dp, dt, dy = chassis.get_decoupled_controls(flight_lm, clutch_lm)
                    target_rc[0] = clamp_rc(1500 + (dr * C.SENS_ROLL))
                    target_rc[1] = clamp_rc(1500 + (dp * C.SENS_PITCH))
                    target_rc[2] = clamp_rc(last_throttle + (dt * C.SENS_THROTTLE))
                    target_rc[3] = clamp_rc(1500 + (dy * C.SENS_YAW))
                elif chassis.is_engaged:
                    chassis.is_engaged = False
                    print("\n[CLUTCH] Released")

            # Apply Smoothing and Update Drone
            roll = filters['roll'].apply(target_rc[0])
            pitch = filters['pitch'].apply(target_rc[1])
            throttle = filters['throttle'].apply(target_rc[2])
            yaw = filters['yaw'].apply(target_rc[3])
            
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
