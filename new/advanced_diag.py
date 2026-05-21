import socket
import time
import os

def log(file, message):
    print(message)
    file.write(message + "\n")
    file.flush()

def send_and_wait(client, name, cmd_id, payload, log_file):
    # MSP Packet: $M< (3 bytes) + Length (1 byte) + Cmd (1 byte) + Payload (N bytes) + Checksum (1 byte)
    # Checksum: XOR of Length, Cmd, and Payload bytes
    length = len(payload)
    checksum = length ^ cmd_id
    for b in payload:
        checksum ^= b
    
    packet = b'$M<' + bytes([length, cmd_id]) + payload + bytes([checksum])
    
    log(log_file, f"--- Requesting {name} (ID: {cmd_id}) ---")
    log(log_file, f"TX: {packet.hex()}")
    
    try:
        client.sendall(packet)
        # Wait a short moment for the drone's response
        time.sleep(0.2)
        response = client.recv(1024)
        if response:
            log(log_file, f"RX: {response.hex()}")
            if b'$M>' in response:
                log(log_file, f"SUCCESS: Valid header found in response")
            else:
                log(log_file, "WARNING: No valid MSP header in response")
        else:
            log(log_file, "RESULT: No data received")
    except Exception as e:
        log(log_file, f"ERROR: {e}")
    log(log_file, "\n")

def run_advanced_diagnostic():
    log_file_path = "advanced_diag_log.txt"
    with open(log_file_path, "w") as f:
        log(f, "--- Starting Advanced MSP Diagnostic ---")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2.0)
        
        try:
            client.connect(('192.168.4.1', 23))
            log(f, "Connected to drone.")
            
            # Scenario 1: MSP_IDENT (100) - Basic Identification
            send_and_wait(client, "MSP_IDENT", 100, b'', f)
            
            # Scenario 2: MSP_STATUS (101) - Basic Status
            send_and_wait(client, "MSP_STATUS", 101, b'', f)
            
            # Scenario 3: MSP_ANALOG (110) - Telemetry
            send_and_wait(client, "MSP_ANALOG", 110, b'', f)
            
            # Scenario 4: MSP_ATTITUDE (108) - Attitude
            send_and_wait(client, "MSP_ATTITUDE", 108, b'', f)

            # Scenario 5: Try alternative Header (maybe the drone uses a different one?)
            # Some older MultiWii implementations used raw packets or different sync bytes.
            # We'll just log if it works at all.
            
        except Exception as e:
            log(f, f"CONNECTION ERROR: {e}")
        finally:
            client.close()
            log(f, "Diagnostic Finished.")

if __name__ == "__main__":
    run_advanced_diagnostic()
