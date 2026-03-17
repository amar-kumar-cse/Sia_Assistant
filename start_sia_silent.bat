@echo off
REM Sia Assistant - Silent Startup (for Windows Startup folder)
REM Starts Sia minimized to system tray

REM Change to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv\" (
    exit /b 1
)

REM Start Sia 2.0 minimized (no window)
start /min "" .venv\Scripts\pythonw.exe main_sia_2.py --startup

exit
