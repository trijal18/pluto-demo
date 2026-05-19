import cv2
import mediapipe as mp
import numpy as np
from collections import deque

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# =========================
# HAND CONNECTIONS
# =========================
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17)
]

# =========================
# MODEL
# =========================
MODEL_PATH = "hand_landmarker.task"

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# =========================
# TRAIL STORAGE (PARTICLES)
# =========================
trail = deque(maxlen=25)

# =========================
# HUD DRAWING
# =========================
def draw_hud(frame, w, h):
    color = (0, 255, 255)

    # corner brackets (Iron Man style HUD)
    cv2.line(frame, (20, 20), (120, 20), color, 2)
    cv2.line(frame, (20, 20), (20, 120), color, 2)

    cv2.line(frame, (w-20, 20), (w-120, 20), color, 2)
    cv2.line(frame, (w-20, 20), (w-20, 120), color, 2)

    cv2.line(frame, (20, h-20), (120, h-20), color, 2)
    cv2.line(frame, (20, h-20), (20, h-120), color, 2)

    cv2.line(frame, (w-20, h-20), (w-120, h-20), color, 2)
    cv2.line(frame, (w-20, h-20), (w-20, h-120), color, 2)


# =========================
# NEON HAND
# =========================
def draw_neon_hand(frame, hand, w, h):
    overlay = frame.copy()

    for a, b in HAND_CONNECTIONS:
        x1 = int(hand[a].x * w)
        y1 = int(hand[a].y * h)
        x2 = int(hand[b].x * w)
        y2 = int(hand[b].y * h)

        cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 255), 3)
        cv2.line(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1)

    for lm in hand:
        x = int(lm.x * w)
        y = int(lm.y * h)

        cv2.circle(overlay, (x, y), 7, (0, 255, 255), -1)
        cv2.circle(overlay, (x, y), 3, (255, 255, 255), -1)

    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)


# =========================
# MAIN
# =========================
cap = cv2.VideoCapture(0)

print("IRON MAN HUD HAND ACTIVE... Press Q to quit")

with vision.HandLandmarker.create_from_options(options) as landmarker:

    prev_x, prev_y = None, None
    gesture = ""
    scan_y = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = landmarker.detect(mp_image)

        # =========================
        # HUD OVERLAY
        # =========================
        draw_hud(frame, w, h)

        # scanning line animation
        scan_y = (scan_y + 8) % h
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 1)

        # =========================
        # HAND
        # =========================
        if result.hand_landmarks:
            hand = result.hand_landmarks[0]

            draw_neon_hand(frame, hand, w, h)

            wrist = hand[15]
            x, y = wrist.x, wrist.y

            cx, cy = int(x * w), int(y * h)

            # particle trail
            trail.append((cx, cy))

            for i in range(1, len(trail)):
                if trail[i - 1] is None:
                    continue
                thickness =max(1,int(i / 3))
                cv2.line(frame, trail[i - 1], trail[i], (0, 255, 255), thickness)

            # gesture logic
            if prev_x is None:
                prev_x, prev_y = x, y

            dx = x - prev_x
            dy = y - prev_y

            threshold = 0.02

            if abs(dx) > abs(dy):
                if dx > threshold:
                    gesture = "RIGHT ➡️"
                elif dx < -threshold:
                    gesture = "LEFT ⬅️"
            else:
                if dy > threshold:
                    gesture = "DOWN ⬇️"
                elif dy < -threshold:
                    gesture = "UP ⬆️"

            prev_x, prev_y = x, y

            # energy aura
            cv2.circle(frame, (cx, cy), 35, (0, 255, 255), 2)

        # =========================
        # HUD TEXT
        # =========================
        cv2.putText(frame, "J.A.R.V.I.S HAND INTERFACE", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        cv2.putText(frame, f"STATUS: {gesture}", (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.imshow("IRON MAN HUD HAND", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()