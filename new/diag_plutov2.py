import time
import os
from plutov2 import PlutoV2

def log_to_file(filename, message):
    with open(filename, 'a') as f:
        timestamp = time.strftime("%H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def run_diagnostic():
    log_file = "diag_log_plutov2.txt"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    drone = PlutoV2()
    log_to_file(log_file, "Starting PlutoV2 Diagnostic...")
    
    try:
        drone.connect()
        # Wait a bit for connection thread to start
        time.sleep(1)
        
        if not drone.connected:
            log_to_file(log_file, "Failed to connect to drone.")
            return

        start_time = time.time()
        armed = False
        disarmed = False
        
        while time.time() - start_time < 15:
            elapsed = time.time() - start_time
            
            # Retrieve State
            state = drone.get_state()
            
            status = (f"ELAPSED: {elapsed:.1f}s | STATE: {state}")
            
            log_to_file(log_file, status)
            
            # Command Testing
            if elapsed > 5 and not armed:
                log_to_file(log_file, ">>> EXECUTING ARM COMMAND")
                drone.arm()
                armed = True
                
            if elapsed > 10 and not disarmed:
                log_to_file(log_file, ">>> EXECUTING DISARM COMMAND")
                drone.disarm()
                disarmed = True
                
            time.sleep(0.5)
            
    except Exception as e:
        log_to_file(log_file, f"ERROR: {str(e)}")
    finally:
        drone.disconnect()
        log_to_file(log_file, "Diagnostic Complete.")

if __name__ == "__main__":
    run_diagnostic()
