"""
fix_transparency_v4.py
Final exact position for mouth is Y=221
"""

import os
import sys
import shutil
import numpy as np
from collections import deque

try:
    from PIL import Image, ImageFilter, ImageDraw
    pass
except ImportError:
    sys.exit(1)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def flood_fill_remove_bg(img: Image.Image, threshold: int = 225) -> Image.Image:
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.uint8)
    H, W = data.shape[:2]

    r = data[:, :, 0].astype(np.int32)
    g = data[:, :, 1].astype(np.int32)
    b = data[:, :, 2].astype(np.int32)

    def is_bg(y, x):
        return r[y, x] > threshold and g[y, x] > threshold and b[y, x] > threshold

    visited = np.zeros((H, W), dtype=bool)
    bg = np.zeros((H, W), dtype=bool)
    queue = deque()

    for x in range(W):
        for y in [0, H - 1]:
            if not visited[y, x] and is_bg(y, x):
                visited[y, x] = True
                queue.append((y, x))
    for y in range(H):
        for x in [0, W - 1]:
            if not visited[y, x] and is_bg(y, x):
                visited[y, x] = True
                queue.append((y, x))

    while queue:
        y, x = queue.popleft()
        bg[y, x] = True
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not visited[ny, nx] and is_bg(ny, nx):
                visited[ny, nx] = True
                queue.append((ny, nx))

    mask = Image.fromarray((bg * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MaxFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    mask_a = np.array(mask, dtype=np.float32) / 255.0

    orig_a = data[:, :, 3].astype(np.float32) / 255.0
    new_a = np.clip((orig_a * (1.0 - mask_a)) * 255, 0, 255).astype(np.uint8)
    data[:, :, 3] = new_a
    return Image.fromarray(data, "RGBA")


def apply_mouth(img: Image.Image, state: str) -> Image.Image:
    W, H = img.size
    cx = int(W * 0.495)
    cy = 221  # Exact Y coordinate based on visual calibration!

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    if state == "closed":
        mw = int(W * 0.045)
        mh = int(H * 0.007)
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(120, 55, 55, 45))

    elif state == "semi":
        mw = int(W * 0.040)
        mh = int(H * 0.015)
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(45, 8, 8, 140))
        tw = int(W * 0.032)
        d.ellipse([cx-tw, cy-mh+2, cx+tw, cy+0], fill=(238, 232, 226, 120))

    elif state == "open":
        mw = int(W * 0.045)
        mh = int(H * 0.022)
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(35, 6, 6, 170))
        tw = int(W * 0.038)
        d.ellipse([cx-tw, cy-mh+2, cx+tw, cy-1], fill=(240, 234, 230, 150))

    return Image.alpha_composite(img.convert("RGBA"), overlay)


def main():
    print("Running final fix with exact mouth coordinates...")
    for fname in ["Sia_closed.png", "Sia_semi.png", "Sia_open.png", "sia_idle.png"]:
        bak = os.path.join(ASSETS_DIR, fname.replace(".png", "_backup_orig.png"))
        dest = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(bak): shutil.copy2(bak, dest)

    base = Image.open(os.path.join(ASSETS_DIR, "sia_idle.png")).convert("RGBA")
    clean = flood_fill_remove_bg(base, threshold=228)

    for fname, state in [("Sia_closed.png", "closed"), ("Sia_semi.png", "semi"), ("Sia_open.png", "open")]:
        frame = apply_mouth(clean, state)
        frame.save(os.path.join(ASSETS_DIR, fname), format="PNG")
        
    clean.save(os.path.join(ASSETS_DIR, "sia_idle.png"), format="PNG")
    print("Done!")

if __name__ == "__main__":
    main()
