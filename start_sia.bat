@echo off
REM Sia Assistant - Quick Launcher
REM Activates virtual environment and starts Sia Desktop

echo ================================
echo   SIA DESKTOP - STARTING...
echo ================================
echo.

cd /d "%~dp0"
chcp 65001 > nul 2>&1

REM Check if virtual environment exists
if not exist ".venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if .env has API keys
findstr /C:"your_gemini_api_key_here" .env >nul 2>&1
if %errorlevel%==0 (
    echo WARNING: Please configure your API keys in .env file!
    echo.
    pause
)

REM Set console to UTF-8
chcp 65001 > nul

REM Start Sia Desktop
echo Starting Sia Desktop Assistant...
echo.
.venv\Scripts\python.exe sia_desktop.py

REM Keep window open if error occurs
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Sia failed to start!
    pause
)
