"""
build_exe.py — PyInstaller Packaging Script for Sia Assistant
Bundles Sia Assistant into a standalone Windows executable.
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

SPEC_CONTENT = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('engine', 'engine'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'engine.brain',
        'engine.vision_engine',
        'engine.voice_engine',
        'engine.memory',
        'engine.validation',
        'engine.logger',
        'engine.intent',
        'engine.actions',
        'engine.automation',
        'google.generativeai',
        'PIL',
        'mss',
        'pygame',
        'pyttsx3',
        'speech_recognition',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SiaAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None
)
"""


def build():
    print("📦 Building Sia Assistant Executable with PyInstaller...")

    spec_file = BASE_DIR / "sia.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(SPEC_CONTENT)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "sia.spec"]
    try:
        res = subprocess.run(cmd, cwd=BASE_DIR, check=True)
        print("✅ Build complete! Output executable is in 'dist/SiaAssistant.exe'")
    except Exception as err:
        print(f"❌ Build failed: {err}")
        print("Ensure pyinstaller is installed: pip install pyinstaller")


if __name__ == "__main__":
    build()
