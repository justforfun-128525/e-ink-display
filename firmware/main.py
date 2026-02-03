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
SEND_QUERY = "CAN_SEND"
SEND_OK = "YES"
SEND_BUSY = "BUSY"

def main():
    epd = None
    img_buffer = None
    
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
        
        while True:
            gc.collect()
            
            while True:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.01)
                    continue
                
                line = line.strip()
                if line == SEND_QUERY:
                    print(SEND_OK)
                    break
            
            current_byte_pos = 0
            led.value(1)
            mv = memoryview(img_buffer)

            receive_error = False
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
                    
                    if current_byte_pos + length > TOTAL_SIZE:
                        print(f"ERR:OVERFLOW")
                        receive_error = True
                        break

                    mv[current_byte_pos : current_byte_pos + length] = chunk_data
                    current_byte_pos += length
                    
                    print("OK")
                    
                except Exception as e:
                    print(f"ERR:{e}")
                    receive_error = True
                    break
            
            if receive_error:
                led.value(0)
                continue

            try:
                led.value(0)
                epd.init_4Gray()
                epd.display_4Gray(img_buffer)
                epd.sleep()
                print("DONE")
            except Exception as e:
                print(f"ERR_DISP:{e}")

    except Exception as e:
        print(f"FATAL:{e}")
        while True:
            led.toggle()
            time.sleep(0.5)

if __name__ == '__main__':
    main()