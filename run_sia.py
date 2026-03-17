"""
Sia 2.0 launcher with proper UTF-8 encoding for Windows console
"""
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    # Set console to UTF-8 mode
    os.system('chcp 65001 > nul')
    
    # Reconfigure stdout/stderr to use UTF-8
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Now import and run the main application
import main_sia_2
main_sia_2.main()
