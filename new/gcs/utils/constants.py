# --- OneEuro Filter Tuning ---
# MC (Min Cutoff): Higher values (1.0) = less lag, slightly more jitter.
# BETA: Higher values (0.02) = faster reaction to quick hand movements.
MC = 1.0
BETA = 0.02

# --- Hand Chassis Tuning ---
DEADZONE = 0.05  # Increased to 5% for better "locked-in" feel
CLUTCH_THRESHOLD = 0.05

# --- RC Sensitivities ---
# How much hand movement translates to RC units (1000-2000).
# Larger values = faster response to smaller hand movements.
# Adjusted for new 2D slope scales.
SENS_ROLL     = 2500.0  # Wave (Pinky-Thumb Y)
SENS_PITCH    = 3500.0  # Slope (Wrist-MiddleBase Y)
SENS_YAW      = 2500.0  # Rotation (Thumb-Pinky Z)
SENS_THROTTLE = 1200.0  # Decoupled Height (Wrist Y)

# --- Vision Settings ---
MODEL_PATH = "hand_landmarker.task"
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
NUM_HANDS = 2
