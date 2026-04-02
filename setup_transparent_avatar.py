"""
Script to remove background from Sia avatar images and make them transparent.
This creates transparent PNG files suitable for desktop overlay display.
"""

import os
from PIL import Image
import numpy as np

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

def remove_background_rembg(image_path, output_path):
    """
    Remove background using rembg library (best quality).
    Install with: pip install rembg
    """
    try:
        from rembg import remove
        
        input_img = Image.open(image_path)
        output_img = remove(input_img)
        output_img.save(output_path)
        print(f"✅ Background removed (rembg): {output_path}")
        return True
    except ImportError:
        print("⚠️  rembg not installed. Install with: pip install rembg")
        return False
    except Exception as e:
        print(f"❌ Error with rembg: {e}")
        return False

def remove_background_color_based(image_path, output_path, bg_color=(255, 255, 255), threshold=50):
    """
    Remove background using color-based thresholding (faster, for solid backgrounds).
    Good for images with white/uniform backgrounds.
    
    Args:
        image_path: Path to input image
        output_path: Path to save transparent PNG
        bg_color: RGB tuple of background color to remove
        threshold: Color similarity threshold (0-255)
    """
    try:
        img = Image.open(image_path).convert('RGBA')
        data = np.array(img)
        
        # Extract RGB channels
        red, green, blue, alpha = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
        
        # Calculate distance from background color
        r_diff = np.absolute(red.astype(float) - bg_color[0])
        g_diff = np.absolute(green.astype(float) - bg_color[1])
        b_diff = np.absolute(blue.astype(float) - bg_color[2])
        
        # Maximum distance in any channel
        max_diff = np.maximum(np.maximum(r_diff, g_diff), b_diff)
        
        # Create transparency mask
        alpha[max_diff <= threshold] = 0
        
        # Update image data
        data[:,:,3] = alpha
        
        # Save
        result = Image.fromarray(data)
        result.save(output_path, 'PNG')
        print(f"✅ Background removed (color-based): {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def batch_process_avatars():
    """Try both methods to create transparent versions of all avatar images."""
    avatar_files = ["Sia_closed.png", "Sia_semi.png", "Sia_open.png"]
    
    print("🎨 Processing Sia avatar images for transparency...")
    print(f"📁 Assets directory: {ASSETS_DIR}\n")
    
    for avatar_file in avatar_files:
        input_path = os.path.join(ASSETS_DIR, avatar_file)
        
        if not os.path.exists(input_path):
            print(f"⚠️  File not found: {input_path}")
            continue
        
        print(f"\n📸 Processing: {avatar_file}")
        print(f"   File size: {os.path.getsize(input_path) / 1024:.1f} KB")
        
        # Backup original
        backup_path = input_path.replace('.png', '_backup.png')
        if not os.path.exists(backup_path):
            try:
                import shutil
                shutil.copy2(input_path, backup_path)
                print(f"   📦 Backup created: {avatar_file.replace('.png', '_backup.png')}")
            except Exception as e:
                print(f"   ⚠️  Backup failed: {e}")
        
        # Try rembg first (best quality)
        if remove_background_rembg(input_path, input_path):
            continue
        
        # Fallback: color-based removal
        print(f"   🔄 Trying color-based background removal...")
        if remove_background_color_based(input_path, input_path, bg_color=(255, 255, 255), threshold=40):
            continue
        
        print(f"   ❌ Failed to process {avatar_file}")
    
    print("\n" + "="*60)
    print("✅ Avatar processing complete!")
    print("")
    print("📝 Next steps:")
    print("1. Install rembg for best results: pip install rembg")
    print("2. Re-run this script for better quality background removal")
    print("3. Restart Sia for transparent avatars to appear")
    print("="*60)

if __name__ == "__main__":
    # Check if rembg is available
    try:
        import rembg
        print("✅ rembg library found! Running with best quality...\n")
    except ImportError:
        print("💡 Tip: Install rembg for better quality:")
        print("   pip install rembg\n")
    
    batch_process_avatars()
