from PIL import Image, ImageDraw
import os

ASSETS_DIR = "assets"

def apply_mouth(img_path, dest_path, state):
    img = Image.open(img_path).convert("RGBA")
    W, H = img.size
    cx = 316
    cy = 221
    
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    
    # Anime style cute mouths
    outline_color = (30, 10, 10, 240)
    inside_color = (200, 80, 80, 220)
    teeth_color = (250, 250, 250, 240)
    
    if state == "semi":
        mw, mh = 8, 4
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=outline_color)
        d.ellipse([cx-mw+1, cy-mh+1, cx+mw-1, cy+mh-1], fill=inside_color)
        d.ellipse([cx-mw+2, cy-mh+1, cx+mw-2, cy], fill=teeth_color)
        
    elif state == "open":
        mw, mh = 12, 9
        d.ellipse([cx-mw, cy-mh, cx+mw, cy+mh], fill=outline_color)
        d.ellipse([cx-mw+2, cy-mh+2, cx+mw-2, cy+mh-2], fill=inside_color)
        d.ellipse([cx-mw+3, cy-mh+2, cx+mw-3, cy-mh+6], fill=teeth_color)
        d.ellipse([cx-mw+4, cy+mh-5, cx+mw-4, cy+mh-2], fill=(240, 120, 120, 220))
        
    elif state == "blink":
        # Erase open eyes with skin color
        skin_color = img.getpixel((cx, 140)) # forehead
        # Skin color must be opaque
        skin_color = (skin_color[0], skin_color[1], skin_color[2], 255)
        
        ey1, ex1 = 175, 275
        ey2, ex2 = 175, 355
        ew, eh = 25, 5
        
        # Erase eyes (draw thick skin-colored rectangles)
        d.rectangle([ex1-30, ey1-15, ex1+30, ey1+15], fill=skin_color)
        d.rectangle([ex2-30, ey2-15, ex2+30, ey2+15], fill=skin_color)
        
        # Draw closed eyes arcs
        d.arc([ex1-ew, ey1-eh, ex1+ew, ey1+eh], start=180, end=360, fill=outline_color, width=3)
        d.arc([ex2-ew, ey2-eh, ex2+ew, ey2+eh], start=180, end=360, fill=outline_color, width=3)

    out = Image.alpha_composite(img, overlay)
    out.save(dest_path, "PNG")

def main():
    base_img = os.path.join(ASSETS_DIR, "sia_idle.png")
    
    apply_mouth(base_img, os.path.join(ASSETS_DIR, "Sia_semi.png"), "semi")
    apply_mouth(base_img, os.path.join(ASSETS_DIR, "Sia_open.png"), "open")
    apply_mouth(base_img, os.path.join(ASSETS_DIR, "sia_blink.png"), "blink")
    
    Image.open(base_img).save(os.path.join(ASSETS_DIR, "Sia_closed.png"))
    
    print("Cute mouths and blink generated successfully!")

if __name__ == "__main__":
    main()
