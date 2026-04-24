from PIL import Image
import sys

def image_to_ascii(image_path, cx, cy, box_width, box_height):
    try:
        img = Image.open(image_path).convert("L")
    except Exception as e:
        print(f"Error: {e}")
        return

    W, H = img.size
    left = max(0, cx - box_width)
    right = min(W, cx + box_width)
    top = max(0, cy - box_height)
    bottom = min(H, cy + box_height)
    
    img_cropped = img.crop((left, top, right, bottom))
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
    # The mouth was at cx=316, cy=221
    # Eyes are usually higher up, maybe around cy=160
    image_to_ascii(img_path, 316, 160, 60, 40)
