import serial
import time
import numpy as np
from PIL import Image
import binascii

PORT = '/dev/ttyACM0' 
BAUDRATE = 115200 
CHUNK_SIZE = 512 
WIDTH = 800
HEIGHT = 480
EXPECTED_SIZE = 96000
SEND_QUERY = "CAN_SEND"
SEND_OK = "YES"
SEND_BUSY = "BUSY"
SEND_ERR_PREFIX = "ERR"

def request_send_permission(ser, max_attempts=5, wait_seconds=2, timeout=2):
    for attempt in range(max_attempts):
        ser.write(f"{SEND_QUERY}\n".encode())
        ser.flush()
        start = time.time()
        while time.time() - start < timeout:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line == SEND_OK:
                    return True
                if line == SEND_BUSY:
                    print("Pico busy. Retrying...")
                    break
                if line.startswith(SEND_ERR_PREFIX):
                    print(f"Pico error: {line}")
                    return False
            time.sleep(0.01)
        if attempt < max_attempts - 1:
            time.sleep(wait_seconds)
    print("[send image] No response from Pico. Try again later.")
    return False

def process_image(image_path):
    img = Image.open(image_path).convert('L')
    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    pixels = np.array(img, dtype=np.uint8)
    pixels = np.digitize(pixels, [64, 128, 192])
    
    flat = pixels.flatten()
    p = flat.reshape(-1, 4)
    # Pack pixels in reverse order to match byte orientation (3,2,1,0).
    packed = (p[:, 3] << 6) | (p[:, 2] << 4) | (p[:, 1] << 2) | p[:, 0]
    return packed.astype(np.uint8).tobytes()

def send_image_to_pico(image_path):
    ser = None
    try:
        raw_data = process_image(image_path)
        if len(raw_data) != EXPECTED_SIZE:
            print(f"[send image] Size error: {len(raw_data)}")
            return

        hex_data = binascii.hexlify(raw_data)
        
        total_hex_len = len(hex_data)

        ser = serial.Serial(PORT, BAUDRATE, timeout=10)
        print(f"[send image] {PORT} connected.")
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        if not request_send_permission(ser):
            return

        print("[send image] Connection successful. Start sending text mode.")

        bytes_sent = 0
        
        while bytes_sent < total_hex_len:
            chunk_len = CHUNK_SIZE * 2
            chunk = hex_data[bytes_sent : bytes_sent + chunk_len]
            
            ser.write(chunk + b'\n')
            ser.flush()
            
            ack_received = False
            start_ack = time.time()
            while time.time() - start_ack < 3:
                if ser.in_waiting:
                    resp = ser.readline().decode().strip()
                    if "OK" in resp:
                        ack_received = True
                        break
                    elif "ERR" in resp:
                        print(f"\n{resp}")
                        return
                time.sleep(0.001)
                
            if not ack_received:
                print(f"\n[send image] Timeout")
                return

            bytes_sent += len(chunk)
            
            percent = (bytes_sent / total_hex_len) * 100
            print(f"\r[send image] Progress: {percent:.1f}%", end='')

        print("\n\n[send image] Sending complete. Waiting for update...")
        
        while True:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                if "DONE" in line:
                    print("[send image] Success")
                    break
            time.sleep(0.1)

    except Exception as e:
        print(f"\n[send image] Error: {e}")
    finally:
        if ser: ser.close()

if __name__ == "__main__":
    send_image_to_pico("grayscale_gradient.jpg")