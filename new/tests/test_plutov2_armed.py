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

def main():
    drone = PlutoV2(ip='192.168.4.1')
    
    print("!!! WARNING: THIS TEST WILL SPIN THE MOTORS !!!")
    print("!!! REMOVE PROPELLERS OR HOLD THE DRONE SECURELY !!!")
    
    input("\nPress Enter only if you have taken safety precautions...")
    
    print("Connecting to drone...")
    drone.connect()
    
    if not drone.connected:
        print("Failed to connect.")
        return

    try:
        # 1. Telemetry Check
        print("\nChecking Telemetry...")
        time.sleep(1)
        state = drone.get_state()
        print(f"Battery: {state['battery']:.2f}V | Ready to Arm.")

        # 2. Arming
        print("\n[STEP 1] ARMING MOTORS...")
        drone.arm()
        time.sleep(2) # Motors should be spinning at idle now
        
        # 3. Movement Tests (Small bumps)
        print("\n[STEP 2] MOVEMENT BUMPS (Checking Tilt/Rotate response)...")
        
        # Throttle
        print(" -> Throttle Bump")
        drone.set_rc(throttle=1200)
        time.sleep(1)
        drone.set_rc(throttle=1000)
        time.sleep(0.5)

        # Roll
        print(" -> Roll Left")
        drone.set_rc(roll=1400)
        time.sleep(0.5)
        print(" -> Roll Right")
        drone.set_rc(roll=1600)
        time.sleep(0.5)
        drone.set_rc(roll=1500)
        time.sleep(0.5)

        # Pitch
        print(" -> Pitch Forward")
        drone.set_rc(pitch=1600)
        time.sleep(0.5)
        print(" -> Pitch Backward")
        drone.set_rc(pitch=1400)
        time.sleep(0.5)
        drone.set_rc(pitch=1500)
        time.sleep(0.5)

        # Yaw
        print(" -> Yaw Left")
        drone.set_rc(yaw=1400)
        time.sleep(0.5)
        print(" -> Yaw Right")
        drone.set_rc(yaw=1600)
        time.sleep(0.5)
        drone.set_rc(yaw=1500)
        time.sleep(0.5)
        
        # 4. Disarm
        print("\n[STEP 3] DISARMING...")
        drone.disarm()
        time.sleep(1)
        
        print("\nArmed Test SUCCESS.")

    except KeyboardInterrupt:
        print("\nEmergency Stop requested.")
        drone.disarm()
    except Exception as e:
        print(f"\nError: {e}")
        drone.disarm()
    finally:
        drone.disconnect()

if __name__ == "__main__":
    main()
