"""
Process and replace Sia avatar images.
Place new_semi.png, new_open.png, new_blink.png in the Sia_Assistant folder,
then run this script.
"""

from PIL import Image
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")

# Mapping: input file → output filename in assets
MAPPINGS = {
    "new_semi.png":  ("Sia_semi.png",  "semi-open mouth"),
    "new_open.png":  ("Sia_open.png",  "fully open mouth"),
    "new_blink.png": ("sia_blink.png", "eyes closed / blink"),
}

TARGET_SIZE = (640, 640)

def remove_bg(img: Image.Image, mode: str = "auto") -> Image.Image:
    """Remove white or black background and make it transparent."""
    img = img.convert("RGBA")
    data = img.getdata()

    # Detect dominant background color from corners
    corners = [
        data[0],                               # top-left
        data[TARGET_SIZE[0] - 1],              # top-right (if square)
        data[-1],                              # bottom-right
    ]
    avg_r = sum(c[0] for c in corners) / 3
    avg_b = sum(c[2] for c in corners) / 3
    bg_is_dark = (avg_r < 80 and avg_b < 80)

    new_data = []
    for pixel in data:
        r, g, b, a = pixel
        if bg_is_dark:
            # Remove black / very dark pixels
            brightness = (r + g + b) / 3
            if brightness < 30:
                new_data.append((r, g, b, 0))
                continue
        else:
            # Remove white / very light pixels
            if r > 240 and g > 240 and b > 240:
                new_data.append((r, g, b, 0))
                continue
        new_data.append(pixel)

    result = Image.new("RGBA", img.size)
    result.putdata(new_data)
    return result


def process_image(src_path: str, dst_path: str, label: str):
    print(f"\n📸 Processing [{label}]")
    print(f"   Source:  {src_path}")
    print(f"   Output:  {dst_path}")

    img = Image.open(src_path)
    print(f"   Original mode={img.mode}, size={img.size}")

    # Remove background
    img = remove_bg(img)

    # Resize to target (preserve aspect ratio with padding)
    img.thumbnail(TARGET_SIZE, Image.LANCZOS)
    canvas = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
    offset_x = (TARGET_SIZE[0] - img.width) // 2
    offset_y = (TARGET_SIZE[1] - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), img)

    # Save
    canvas.save(dst_path, "PNG")
    print(f"   ✅ Saved: mode=RGBA, size={canvas.size}")


if __name__ == "__main__":
    found_any = False
    for src_name, (dst_name, label) in MAPPINGS.items():
        src_path = os.path.join(SCRIPT_DIR, src_name)
        dst_path = os.path.join(ASSETS_DIR, dst_name)

        if not os.path.exists(src_path):
            print(f"⚠️  MISSING: {src_name} — please save it to the Sia_Assistant folder")
            continue

        found_any = True
        process_image(src_path, dst_path, label)

    if not found_any:
        print("\n❌ No images found! Please save the 3 images as:")
        for src_name in MAPPINGS:
            print(f"   → {os.path.join(SCRIPT_DIR, src_name)}")
        sys.exit(1)

    print("\n🎉 Done! Assets updated successfully.")
    print("   Run Sia to see the new look!")
