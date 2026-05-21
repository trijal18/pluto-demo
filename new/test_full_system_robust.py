import time
from plutov2 import PlutoV2, CMD_FRONT_FLIP, CMD_BACK_FLIP, CMD_RIGHT_FLIP, CMD_LEFT_FLIP

def robust_stress_test():
    log_file = open("robust_stress_test_log.txt", "w")
    def log(msg):
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    drone = PlutoV2()
    log("--- ROBUST STRESS TEST STARTING ---")
    drone.connect()
    time.sleep(2)
    
    if not drone.connected:
        log("CRITICAL: Could not connect.")
        log_file.close()
        return

    try:
        # 0. ARM THE DRONE FIRST (Required for RC updates to be accepted)
        log("\n[0/5] Arming for RC Test...")
        drone.arm()
        time.sleep(2) 

        # 1. Test RC Range Persistence
        log("\n[1/5] Testing RC Range Persistence...")
        rc_configs = [
            {"roll": 1000, "pitch": 1000, "throttle": 1000, "yaw": 1000},
            {"roll": 2000, "pitch": 2000, "throttle": 2000, "yaw": 2000},
            {"roll": 1500, "pitch": 1500, "throttle": 1500, "yaw": 1500}
        ]
        for cfg in rc_configs:
            drone.set_rc(**cfg)
            time.sleep(0.5)
            rc_back = drone.get_state()['rc']
            log(f"Sent: {list(cfg.values())} | Drone Reports: {rc_back[0:4]}")

        # 2. Test Discrete Commands
        log("\n[2/5] Testing Flight Commands...")
        for cmd in [CMD_FRONT_FLIP, CMD_BACK_FLIP, CMD_LEFT_FLIP, CMD_RIGHT_FLIP]:
            log(f"Executing command ID: {cmd}")
            drone.send_command(cmd)
            time.sleep(0.3)

        # 3. Test Sensor Feedback
        log("\n[3/5] Testing Sensor Feedback...")
        for _ in range(10):
            state = drone.get_state()
            log(f"ALT: {state['height']} | BAT: {state['battery']}V | ACC: {state['acc']} | MAG: {state['mag']}")
            time.sleep(0.2)

        # 4. Calibration Sequence
        log("\n[4/5] Triggering Calibrations...")
        drone.calibrate_acc()
        time.sleep(0.5)
        drone.calibrate_mag()
        time.sleep(0.5)

        # 5. Stability Test
        log("\n[5/5] Stability Test (10s continuous monitoring)...")
        for _ in range(20):
            state = drone.get_state()
            if state['last_update'] > 0:
                log(f"Telemetry Live: {state['last_update']} | Cycle time OK")
            time.sleep(0.5)

    except Exception as e:
        log(f"Stress Test Failed: {e}")
    finally:
        log("\n--- DISARMING AND CLEANUP ---")
        drone.disarm()
        time.sleep(1)
        drone.disconnect()
        log_file.close()

if __name__ == "__main__":
    robust_stress_test()
