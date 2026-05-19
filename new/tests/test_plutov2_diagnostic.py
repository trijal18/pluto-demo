import time
import logging
import sys
import os

# Ensure we can import plutov2 from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plutov2 import PlutoV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def print_telemetry(state):
    # RC: [Roll, Pitch, Throttle, Yaw, AUX1, AUX2, AUX3, AUX4]
    rc = state.get('rc', [0]*8)
    print(f"\r[TEL] Bat: {state['battery']:.2f}V | Alt: {state['height']:>3}cm | "
          f"Att: R:{state['roll']:>5.1f} P:{state['pitch']:>5.1f} | "
          f"RC: R:{rc[0]} P:{rc[1]} T:{rc[2]} Y:{rc[3]} A1:{rc[4]} A2:{rc[5]} A3:{rc[6]} A4:{rc[7]}", end="")

def main():
    drone = PlutoV2(ip='192.168.4.1')
    
    print("--- PlutoV2 FULL Diagnostic Test ---")
    print("!!! REMOVE PROPELLERS !!!")
    input("Press Enter to start connection and monitor real-time data...")
    
    drone.connect()
    if not drone.connected:
        print("Failed to connect.")
        return

    try:
        print("\n[PHASE 1] SENSOR CALIBRATION")
        print("Drone MUST be on a flat surface.")
        drone.calibrate_acc()
        time.sleep(2)

        print("\n[PHASE 2] MONITORING IDLE STATE (5 Seconds)")
        print("Verify Throttle (T) is 1000 and Attitude (R/P) is near 0.0.")
        for _ in range(50):
            print_telemetry(drone.get_state())
            time.sleep(0.1)

        print("\n\n[PHASE 3] ATTEMPTING ARM...")
        print("Sending AUX4=1500 + Throttle=1000")
        drone.arm()
        for _ in range(50):
            print_telemetry(drone.get_state())
            time.sleep(0.1)

        print("\n\n[PHASE 4] THROTTLE BUMP (1200)...")
        drone.set_rc(throttle=1200)
        for _ in range(30):
            print_telemetry(drone.get_state())
            time.sleep(0.1)

        print("\n\n[PHASE 5] DISARMING...")
        drone.disarm()
        for _ in range(20):
            print_telemetry(drone.get_state())
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nInterrupted.")
        drone.disarm()
    finally:
        print("\nDisconnecting...")
        drone.disconnect()

if __name__ == "__main__":
    main()
