import send_image
import generate_image
import time

image_name = generate_image.create_time_image()
time.sleep(1)
send_image.send_image_to_pico(image_name)