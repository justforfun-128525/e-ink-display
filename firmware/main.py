import machine
import sys
import time
import epaper7in5
import gc
import binascii

gc.enable()
led = machine.Pin(25, machine.Pin.OUT)
TOTAL_SIZE = 96000
CHUNK_HEX_SIZE = 1024 

def main():
    try:
        epd = epaper7in5.EPD_7in5()
        
        try:
            img_buffer = bytearray(TOTAL_SIZE)
        except MemoryError:
            print("ERR_MEM")
            return

        for _ in range(5):
            led.toggle()
            time.sleep(0.1)
        led.value(0)
        
        time.sleep(2)
        print("READY")
        
        current_byte_pos = 0
        led.value(1)
        
        mv = memoryview(img_buffer)

        while current_byte_pos < TOTAL_SIZE:
            hex_line = sys.stdin.readline()
            
            if not hex_line:
                time.sleep(0.01)
                continue
                
            hex_line = hex_line.strip()
            
            if not hex_line:
                continue

            try:
                chunk_data = binascii.unhexlify(hex_line)
                length = len(chunk_data)
                
                mv[current_byte_pos : current_byte_pos + length] = chunk_data
                current_byte_pos += length
                
                print("OK")
                
            except Exception as e:
                print(f"ERR:{e}")
                return

        led.value(0)
        epd.init_4Gray()
        epd.display_4Gray(img_buffer)
        epd.sleep()
        print("DONE")
        
    except Exception as e:
        print(f"FATAL:{e}")

    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()