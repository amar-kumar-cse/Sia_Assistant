from PIL import Image
import numpy as np

for fname in ["Sia_open.png", "Sia_semi.png", "sia_blink.png", "sia_idle.png"]:
    img = Image.open(f"assets/{fname}")
    mode = img.mode
    print(f"{fname} mode: {mode}")
    if mode == "RGBA":
        arr = np.array(img)
        # Check top-left pixel alpha
        alpha = arr[0, 0, 3]
        print(f"  Top-left alpha: {alpha}")
