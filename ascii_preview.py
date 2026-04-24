from PIL import Image
import sys

def image_to_ascii(image_path, cx, cy, box_size=40):
    try:
        img = Image.open(image_path).convert("L")
    except Exception as e:
        print(f"Error: {e}")
        return

    W, H = img.size
    left = max(0, cx - box_size)
    right = min(W, cx + box_size)
    top = max(0, cy - box_size)
    bottom = min(H, cy + box_size)
    
    img_cropped = img.crop((left, top, right, bottom))
    # resize to maintain aspect ratio in text (characters are roughly 2x taller than wide)
    img_cropped = img_cropped.resize((img_cropped.width, img_cropped.height // 2))
    
    chars = "@%#*+=-:. "
    ascii_art = ""
    for y in range(img_cropped.height):
        for x in range(img_cropped.width):
            pixel = img_cropped.getpixel((x, y))
            ascii_art += chars[pixel * len(chars) // 256]
        ascii_art += "\n"
    
    print(ascii_art)

if __name__ == "__main__":
    img_path = "assets/sia_idle.png"
    # let's look at the center of the image, where the face should be
    # previous script used cx = W*0.495, cy = 221
    with Image.open(img_path) as img:
        W, H = img.size
    cx = int(W * 0.495)
    cy = 221
    print(f"Image size: {W}x{H}, Center at: {cx}, {cy}")
    image_to_ascii(img_path, cx, cy, 60)
