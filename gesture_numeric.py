from ultralytics import YOLO
import requests
import time
import logging
import os

# === CONFIG ===
MODEL_PATH = "models/numeric.pt"
GCS_BASE_URL = "http://127.0.0.1:8000"
COOLDOWN_SECONDS = 3
LOG_FILE = "gesture.log"

gesture_to_command = {
    "1": "arm",
    "2": "takeoff",
    "3": "land",
    "4": "disarm"
}

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),  # Append mode
        logging.StreamHandler()                   # Also log to console
    ]
)

# === Load Model ===
model = YOLO(MODEL_PATH)
last_gesture = None
last_time = 0

def send_command(cmd: str):
    url = f"{GCS_BASE_URL}/{cmd}"
    try:
        res = requests.post(url, timeout=1)
        if res.ok:
            logging.info(f"Sent command: {cmd}")
        else:
            logging.warning(f"Command failed: {cmd} (status {res.status_code})")
    except Exception as e:
        logging.error(f"Error sending command '{cmd}': {e}")

def main():
    global last_gesture, last_time
    logging.info("Gesture control started using model with classes 1-4")

    try:
        for result in model.predict(source=0, stream=True, show=True):
            now = time.time()
            for box in result.boxes:
                cls = int(box.cls[0])
                gesture = model.names[cls]

                if gesture not in gesture_to_command:
                    continue

                if gesture == last_gesture and (now - last_time) < COOLDOWN_SECONDS:
                    continue  # Cooldown active

                send_command(gesture_to_command[gesture])
                last_gesture = gesture
                last_time = now

    except KeyboardInterrupt:
        logging.info("Gesture control stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
