import time
import logging
from plutov2 import PlutoV2

# Configure logging to see what's happening internally
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def main():
    # 1. Initialize the drone
    # Default IP is 192.168.4.1. Change if your drone is on a different IP.
    drone = PlutoV2(ip='192.168.4.1')
    
    print("--- PlutoV2 Robustness Test ---")
    print("Connecting to drone...")
    drone.connect()
    
    if not drone.connected:
        print("Failed to connect. Make sure you are connected to the drone's WiFi.")
        return

    try:
        # 2. Monitor Telemetry for a few seconds
        print("\n[1/3] Monitoring Telemetry (Check if values update)...")
        for _ in range(30): # ~3 seconds
            state = drone.get_state()
            print(f"\rRoll: {state['roll']:>6.1f}° | Pitch: {state['pitch']:>6.1f}° | Height: {state['height']:>4}cm | Bat: {state['battery']:.2f}V", end="")
            time.sleep(0.1)
        print("\nTelemetry OK.")

        # 3. Test Proportional RC Updates
        print("\n[2/3] Testing Proportional Input (Dry Run - No Arming)...")
        print("Moving simulated 'hand' left to right...")
        for i in range(1500, 1701, 10):
            drone.set_rc(roll=i)
            print(f"\rTarget Roll: {i}", end="")
            time.sleep(0.05)
        
        for i in range(1700, 1299, -10):
            drone.set_rc(roll=i)
            print(f"\rTarget Roll: {i}", end="")
            time.sleep(0.05)
        
        drone.set_rc(roll=1500) # Reset to neutral
        print("\nRC Updates OK.")

        # 4. Test Safety Watchdog
        print("\n[3/3] Testing Safety Watchdog & Telemetry Timeout...")
        print("Setting Pitch to 1700 and then STOPPING updates...")
        drone.set_rc(pitch=1700)
        
        print("Waiting 1.5 seconds...")
        time.sleep(1.5)
        
        # Check current internal targets
        with drone.lock:
            current_pitch = drone.target_rc[1]
            tele_lost = drone.telemetry_lost
            
        if current_pitch == 1500:
            print("Watchdog SUCCESS: Pitch was automatically reset to 1500.")
        else:
            print(f"Watchdog FAILED: Pitch is still {current_pitch}.")
            
        if tele_lost:
            print("Telemetry Timeout SUCCESS: 'telemetry_lost' flag is TRUE (Expected since no real drone is connected).")
        else:
            print("Telemetry Timeout NOTE: 'telemetry_lost' is FALSE (Maybe drone is connected or last_update is 0).")

    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        # 5. Cleanup
        print("\nCleaning up...")
        drone.disconnect()
        print("Test Complete.")

if __name__ == "__main__":
    main()
