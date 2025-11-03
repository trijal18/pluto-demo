from ultralytics import YOLO
import requests
import time
import logging

# 🔧 Config
GCS_BASE = "http://127.0.0.1:8000"   # change if running on different host
COOLDOWN_SECONDS = 3
MODEL_PATH = r"models/best_5.pt"

# Gesture → endpoint mapping (MUST match your existing GCS endpoints)
gesture_to_endpoint = {
    "V": "arm",
    "W": "disarm",
    "U": "takeoff",
    "ThumbDown": "land",
    "Left": "left",
    "Right": "right",
    "Fist": "forward",
    "Palm": "backward"
}

# Load model
model = YOLO(MODEL_PATH)
last_gesture = None
last_time = 0

# Log setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

def send_command(cmd: str):
    url = f"{GCS_BASE}/{cmd}"
    try:
        response = requests.post(url, timeout=1)
        if response.status_code == 200:
            logging.info(f"Gesture triggered: {cmd}")
        else:
            logging.warning(f"Failed to send command '{cmd}', status: {response.status_code}")
    except Exception as e:
        logging.error(f"Error sending command '{cmd}': {e}")

def main():
    global last_gesture, last_time
    logging.info("🖐️  Gesture detection started")
    try:
        for result in model.predict(source=0, stream=True, show=True):
            current_time = time.time()
            for box in result.boxes:
                gesture = model.names[int(box.cls[0])]
                if gesture not in gesture_to_endpoint:
                    continue
                if gesture == last_gesture and current_time - last_time < COOLDOWN_SECONDS:
                    continue  # still in cooldown
                send_command(gesture_to_endpoint[gesture])
                last_gesture = gesture
                last_time = current_time
    except KeyboardInterrupt:
        logging.info("👋 Gesture detection stopped")
    except Exception as e:
        logging.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
