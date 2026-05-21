# --- OneEuro Filter Tuning ---
# MC (Min Cutoff): Lower values (0.1) = heavy smoothing for hover.
# BETA: Lower values (0.005) = smoother transitions, less lag-reduction.
MC = 0.1
BETA = 0.005

# --- Hand Chassis Tuning ---
DEADZONE = 0.02
CLUTCH_THRESHOLD = 0.05

# --- RC Sensitivities ---
# How much hand movement translates to RC units (1000-2000).
# Larger values = faster response to smaller hand movements.
SENS_ROLL     = 2000.0
SENS_PITCH    = 2500.0
SENS_YAW      = 2500.0
SENS_THROTTLE = 500.0

# --- Vision Settings ---
MODEL_PATH = "hand_landmarker.task"
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
NUM_HANDS = 2
