import os
from datetime import datetime
from html2image import Html2Image
from PIL import Image

def create_time_image(image_name: str = "calendar.jpg") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template_path = "index.html"
    
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    html_content = html_content.replace("{{time_placeholder}}", now)

    filename = image_name
    
    flags = [
        '--window-size=800,601', 
        '--hide-scrollbars',
        '--force-device-scale-factor=1',
        '--headless'
    ]
    
    hti = Html2Image(custom_flags=flags)
    
    print(f"[image generation] image rendering...")
    
    hti.screenshot(html_str=html_content, save_as=filename)

    print("[image generation] cropping image...")
    
    with Image.open(filename) as img:
        cropped_img = img.crop((0, 0, 800, 480))
        cropped_img.save(filename, quality=95)

    print(f"[image generation] success: '{filename}' saved.")

    return filename

if __name__ == "__main__":
    create_time_image()