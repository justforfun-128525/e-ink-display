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

def process_image(image_path):
    img = Image.open(image_path).convert('L')
    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    pixels = np.array(img, dtype=np.uint8)
    pixels = np.digitize(pixels, [64, 128, 192])
    
    flat = pixels.flatten()
    p = flat.reshape(-1, 4)
    packed = (p[:, 0] << 6) | (p[:, 1] << 4) | (p[:, 2] << 2) | p[:, 3]
    return packed.astype(np.uint8).tobytes()

def send_image_to_pico(image_path):
    ser = None
    try:
        raw_data = process_image(image_path)
        if len(raw_data) != EXPECTED_SIZE:
            print(f"Size error: {len(raw_data)}")
            return

        hex_data = binascii.hexlify(raw_data)
        
        total_hex_len = len(hex_data)

        ser = serial.Serial(PORT, BAUDRATE, timeout=10)
        print(f"{PORT} connected.")
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        print("READY wait")
        
        while True:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "READY" in line:
                    print("Connection successful. Start sending text mode.")
                    break
            time.sleep(0.01)

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
                print(f"\nTimeout")
                return

            bytes_sent += len(chunk)
            
            percent = (bytes_sent / total_hex_len) * 100
            print(f"\rProgress: {percent:.1f}%", end='')

        print("\n\nSending complete. Waiting for update...")
        
        while True:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                if "DONE" in line:
                    print("Success")
                    break
            time.sleep(0.1)

    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if ser: ser.close()

if __name__ == "__main__":
    send_image_to_pico("test.jpg")