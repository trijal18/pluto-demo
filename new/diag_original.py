import time
import os
from original_pluto import Pluto

def log_to_file(filename, message):
    with open(filename, 'a') as f:
        timestamp = time.strftime("%H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def run_diagnostic():
    log_file = "diag_log_original.txt"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    drone = Pluto()
    log_to_file(log_file, "Starting Original Pluto Diagnostic...")
    
    try:
        drone.connect()
        if not drone.connected:
            log_to_file(log_file, "Failed to connect to drone.")
            return

        start_time = time.time()
        armed = False
        disarmed = False
        
        while time.time() - start_time < 15:
            elapsed = time.time() - start_time
            
            # Retrieve Telemetry
            roll = drone.get_roll()
            pitch = drone.get_pitch()
            yaw = drone.get_yaw()
            height = drone.get_height()
            battery = drone.get_battery()
            rssi = drone.get_rssi()
            rc = drone.rc_values()
            
            status = (f"ELAPSED: {elapsed:.1f}s | "
                      f"ATT: R:{roll:.1f} P:{pitch:.1f} Y:{yaw:.1f} | "
                      f"ALT: {height}cm | BAT: {battery:.2f}V | RSSI: {rssi} | "
                      f"RC: {rc}")
            
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
