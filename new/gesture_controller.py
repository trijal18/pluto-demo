import cv2
import mediapipe as mp
import time
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plutov2 import PlutoV2, CMD_NONE, CMD_TAKE_OFF, CMD_LAND
from utils.filters import LowPassFilter
from utils.gestures import HandChassis

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- Constants ---
MODEL_PATH = "hand_landmarker.task"
ALPHA = 0.35  # Smoothing factor (Lower = smoother/laggier)

# Sensitivities (Higher = faster response to smaller movements)
SENS_THROTTLE = 1500.0  # Wrist Y movement
SENS_ROLL     = 2000.0  # Wave slope
SENS_PITCH    = 2500.0  # Lean Z-depth
SENS_YAW      = 2500.0  # Screwdriver Z-depth

def main():
    # 1. Initialize Drone
    drone = PlutoV2()
    drone.connect()
    
    # 2. Initialize MediaPipe
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
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
    print(" PLUTO GCS: GESTURE CONTROL ACTIVE ")
    print("="*40)
    print("CONTROLS:")
    print(" [A] Arm/Disarm | [T] Takeoff | [L] Land")
    print(" [C] Calibrate Acc | [Q] Quit")
    print(" CLUTCH: Pinch Thumb + Pinky to engage")
    print("="*40 + "\n")

    with vision.HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            # Detect Landmarks
            result = landmarker.detect(mp_image)
            
            target_rc = [1500, 1500, last_throttle, 1500] # R, P, T, Y
            clutch_active = False

            if result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                
                # --- VISUALIZATION ---
                h, w, _ = frame.shape
                # 1. Full Skeleton Connections
                connections = [
                    (0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8),
                    (5,9),(9,10),(10,11),(11,12), (9,13),(13,14),(14,15),(15,16),
                    (13,17),(17,18),(18,19),(19,20), (0,17)
                ]
                for a, b in connections:
                    pt1 = (int(landmarks[a].x * w), int(landmarks[a].y * h))
                    pt2 = (int(landmarks[b].x * w), int(landmarks[b].y * h))
                    cv2.line(frame, pt1, pt2, (255, 255, 255), 1)

                # 2. The Chassis Triangle (Wrist, Index MCP, Pinky MCP)
                pts = [0, 5, 17]
                tri_pts = []
                for p in pts:
                    cp = (int(landmarks[p].x * w), int(landmarks[p].y * h))
                    tri_pts.append(cp)
                    cv2.circle(frame, cp, 6, (255, 0, 255), -1)
                
                cv2.line(frame, tri_pts[0], tri_pts[1], (255, 0, 255), 2)
                cv2.line(frame, tri_pts[1], tri_pts[2], (255, 0, 255), 2)
                cv2.line(frame, tri_pts[2], tri_pts[0], (255, 0, 255), 2)

                # 3. Clutch Visual (Thumb to Pinky)
                t_tip = (int(landmarks[4].x * w), int(landmarks[4].y * h))
                p_tip = (int(landmarks[20].x * w), int(landmarks[20].y * h))
                clutch_active = chassis.get_clutch_state(landmarks)
                color = (0, 255, 0) if clutch_active else (0, 0, 255)
                cv2.line(frame, t_tip, p_tip, color, 2)
                cv2.circle(frame, t_tip, 8, color, -1)
                cv2.circle(frame, p_tip, 8, color, -1)
                
                if clutch_active:
                    if not chassis.is_engaged:
                        chassis.set_neutral(landmarks)
                        print("\n[CLUTCH] Engaged - Zero Point Set")
                    
                    # Get Raw Control Deltas
                    dt, dp, dr, dy = chassis.get_controls(landmarks)
                    
                    # Map to RC (1000-2000)
                    target_rc[0] = 1500 + int(dr * SENS_ROLL)
                    target_rc[1] = 1500 + int(dp * SENS_PITCH)
                    target_rc[2] = last_throttle + int(dt * SENS_THROTTLE)
                    target_rc[3] = 1500 + int(dy * SENS_YAW)
                else:
                    if chassis.is_engaged:
                        chassis.is_engaged = False
                        print("\n[CLUTCH] Released - Entering Safe Hover")
            
            # Apply Filters
            f_roll.apply(target_rc[0])
            f_pitch.apply(target_rc[1])
            f_throttle.apply(target_rc[2])
            f_yaw.apply(target_rc[3])
            
            # Final Clamped Values
            roll = f_roll.value
            pitch = f_pitch.value
            throttle = f_throttle.value
            yaw = f_yaw.value
            
            # Update Drone
            drone.set_rc(roll=roll, pitch=pitch, throttle=throttle, yaw=yaw)
            if clutch_active:
                last_throttle = throttle # Remember throttle while flying

            # Terminal HUD
            state = drone.get_state()
            sys.stdout.write(f"\rRC: R:{int(roll)} P:{int(pitch)} T:{int(throttle)} Y:{int(yaw)} | Clutch: {'ON ' if clutch_active else 'OFF'} | Bat: {state['battery']}V  ")
            sys.stdout.flush()

            # OpenCV Window (Failsafe & Visual check)
            cv2.imshow("Pluto GCS - Camera", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            elif key == ord('a'):
                if not is_armed:
                    drone.arm()
                    is_armed = True
                    print("\n[COMMAND] Armed")
                else:
                    drone.disarm()
                    is_armed = False
                    print("\n[COMMAND] Disarmed")
            elif key == ord('t'):
                drone.takeoff()
                print("\n[COMMAND] Takeoff")
            elif key == ord('l'):
                drone.land()
                print("\n[COMMAND] Landing")
            elif key == ord('c'):
                drone.calibrate_acc()
                print("\n[COMMAND] Calibration Sent")

    drone.disconnect()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
