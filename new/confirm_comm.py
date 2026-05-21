import socket
import time

def confirm_comm():
    # MSP V1 Constants
    MSP_HEADER_IN = b'$M<'
    MSP_RESPONSE_HEADER = b'$M>'
    
    # Simple Request Packet (MSP_IDENT = 100)
    # Length: 0, Cmd: 100, Checksum: 0^100 = 100 (0x64)
    # Header: $M< (0x24 0x4D 0x3C)
    packet = b'\x24\x4D\x3C\x00\x64\x64'
    
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(2.0)
    try:
        client.connect(('192.168.4.1', 23))
        print("Connected. Sending MSP_IDENT request...")
        client.sendall(packet)
        
        start = time.time()
        while time.time() - start < 5:
            data = client.recv(1024)
            if data:
                print(f"Received {len(data)} bytes: {data.hex()}")
                if MSP_RESPONSE_HEADER in data:
                    print("SUCCESS: Valid MSP Response detected!")
                else:
                    print("Received data, but no valid MSP Header.")
            time.sleep(0.1)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    confirm_comm()
