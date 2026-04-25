"""
fix_transparency_v3.py — Final version
Smart flood-fill BG removal + correct mouth positions for lip-sync.
"""

import os
import sys
import shutil
import numpy as np
from collections import deque

try:
    from PIL import Image, ImageFilter, ImageDraw
    print("✅ Pillow available")
except ImportError:
    print("❌ pip install Pillow")
    sys.exit(1)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ── Smart corner flood-fill BG removal ───────────────────────────────────────

def flood_fill_remove_bg(img: Image.Image, threshold: int = 230) -> Image.Image:
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

    # Seed from all 4 edges
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

    # Feather mask
    mask = Image.fromarray((bg * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MaxFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    mask_a = np.array(mask, dtype=np.float32) / 255.0

    orig_a = data[:, :, 3].astype(np.float32) / 255.0
    new_a = np.clip((orig_a * (1.0 - mask_a)) * 255, 0, 255).astype(np.uint8)
    data[:, :, 3] = new_a
    return Image.fromarray(data, "RGBA")


# ── Mouth overlay at correct face position ────────────────────────────────────
# Based on analysis: image 640x640
# Mouth center: ~50% X, ~39.7% Y → absolute (320, 254)

def apply_mouth(img: Image.Image, state: str) -> Image.Image:
    W, H = img.size
    cx = int(W * 0.50)
    cy = int(H * 0.397)   # 254 / 640 ≈ 0.397

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    if state == "closed":
        mw = int(W * 0.055)
        mh = int(H * 0.009)
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(120, 55, 55, 45))

    elif state == "semi":
        mw = int(W * 0.052)
        mh = int(H * 0.018)
        # Mouth cavity
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(45, 8, 8, 130))
        # Top teeth
        tw = int(W * 0.044)
        d.ellipse([cx-tw, cy-mh+2, cx+tw, cy+1], fill=(238, 232, 226, 110))

    elif state == "open":
        mw = int(W * 0.060)
        mh = int(H * 0.028)
        # Mouth cavity
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=(35, 6, 6, 165))
        # Teeth (top)
        tw = int(W * 0.050)
        d.ellipse([cx-tw, cy-mh+2, cx+tw, cy-1], fill=(240, 234, 230, 140))

    return Image.alpha_composite(img.convert("RGBA"), overlay)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🔧 Sia Transparency Fix v3 (Smart Flood-Fill)")
    print("━" * 50)

    # Restore from original backups
    fname_list = ["Sia_closed.png", "Sia_semi.png", "Sia_open.png", "sia_idle.png"]
    for fname in fname_list:
        bak = os.path.join(ASSETS_DIR, fname.replace(".png", "_backup_orig.png"))
        dest = os.path.join(ASSETS_DIR, fname)
        if os.path.exists(bak):
            shutil.copy2(bak, dest)
            print(f"   ♻️  Restored {fname}")

    # Load base image
    base_path = os.path.join(ASSETS_DIR, "sia_idle.png")
    print(f"\n📂 Source: {base_path}")
    base = Image.open(base_path).convert("RGBA")
    print(f"   Size: {base.size}")

    print("\n⚙️  Removing white background (flood-fill from corners)...")
    clean = flood_fill_remove_bg(base, threshold=228)

    alpha = np.array(clean)[:, :, 3]
    trans_pct = (alpha < 10).sum() / alpha.size * 100
    char_pct  = (alpha > 200).sum() / alpha.size * 100
    print(f"   ✅ {trans_pct:.1f}% transparent | {char_pct:.1f}% character pixels kept")

    # Lip-sync frames
    frames = [
        ("Sia_closed.png", "closed"),
        ("Sia_semi.png",   "semi"),
        ("Sia_open.png",   "open"),
    ]

    print("\n🎭 Generating lip-sync frames...")
    for fname, state in frames:
        frame = apply_mouth(clean, state)
        out = os.path.join(ASSETS_DIR, fname)
        frame.save(out, format="PNG")
        kb = os.path.getsize(out) // 1024
        print(f"   ✅ {fname} [{state}] → {kb} KB")

    clean.save(os.path.join(ASSETS_DIR, "sia_idle.png"), format="PNG")
    print(f"   ✅ sia_idle.png [idle]")

    print("\n✨ Done! Background is transparent, lip-sync frames ready.")
    print("   '▶ Start_Sia.bat' to launch!")
    print("━" * 50)


if __name__ == "__main__":
    main()
