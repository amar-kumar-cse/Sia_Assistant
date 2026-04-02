"""
Background Removal Script for Sia Avatar
Uses rembg to remove backgrounds from avatar images
Author: Sia Assistant
"""

import sys
import os

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    from rembg import remove
    from PIL import Image
except ImportError:
    print('Installing required packages...')
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'rembg[cpu]', 'Pillow'])
    from rembg import remove
    from PIL import Image

def remove_bg(input_path, output_name):
    """Remove background from image and save."""
    try:
        print(f'🖼️ Processing {output_name}...')
        with Image.open(input_path) as img:
            # Remove background
            output = remove(img)
            # Save to assets
            output_path = os.path.join(ASSETS_DIR, output_name)
            output.save(output_path, 'PNG')
            print(f'✅ Saved: {output_path}')
            return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def process_avatars():
    """Process all avatar images."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # Source paths - check for generated avatar first
    generated_path = r'C:\Users\yadav\.gemini\antigravity\brain\d8bab7b7-befe-4f62-9775-9078a502b1f2\sia_avatar_disney_1774861469181.png'
    
    if os.path.exists(generated_path):
        print('🎭 Found generated avatar!')
        source = generated_path
    else:
        # Use existing assets as source
        print('📦 Using existing assets...')
        source = os.path.join(ASSETS_DIR, 'Sia_closed.png')
    
    if not os.path.exists(source):
        print(f'❌ Source not found: {source}')
        return False
    
    print('🔄 Removing backgrounds... (First run downloads ML model, takes 1-2 mins)')
    print('Please wait...')
    
    # Process all 3 states
    success = True
    for name in ['Sia_closed.png', 'Sia_semi.png', 'Sia_open.png']:
        if not remove_bg(source, name):
            success = False
    
    if success:
        print('\n🎉 All avatars processed successfully!')
    return success

if __name__ == "__main__":
    process_avatars()
