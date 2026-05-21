import time
from plutov2 import PlutoV2, CMD_FRONT_FLIP

def test_full_system():
    drone = PlutoV2()
    print("Connecting to drone...")
    drone.connect()
    time.sleep(2) # Allow connection thread to stabilize
    
    if not drone.connected:
        print("Failed to connect!")
        return

    try:
        print("--- 1. Testing Arm/Disarm ---")
        drone.arm()
        time.sleep(1)
        print(f"Current State: {drone.get_state()}")
        drone.disarm()
        time.sleep(1)
        
        print("\n--- 2. Testing RC Updates ---")
        # Set some specific values
        drone.set_rc(roll=1600, pitch=1400, throttle=1200, yaw=1500)
        time.sleep(1)
        state = drone.get_state()
        print(f"RC Received by Drone: {state['rc']}")
        
        print("\n--- 3. Testing Command (Flip) ---")
        drone.flip(CMD_FRONT_FLIP)
        time.sleep(0.5)
        
        print("\n--- 4. Testing Calibration ---")
        drone.calibrate_acc()
        time.sleep(0.5)
        
        print("\n--- 5. Final State Dump ---")
        for _ in range(5):
            print(f"Telemetry: BAT={state['battery']}V, ALT={state['height']}cm, MAG={state['mag']}")
            time.sleep(0.5)
            state = drone.get_state()
            
    finally:
        print("\nDisconnecting...")
        drone.disconnect()

if __name__ == "__main__":
    test_full_system()
