@echo off
REM ═══════════════════════════════════════════
REM  SIA - Premium Desktop Virtual Assistant
REM  One-Click Launcher
REM ═══════════════════════════════════════════

title Sia Desktop Assistant

REM Set UTF-8 encoding
chcp 65001 > nul 2>&1

REM Navigate to script directory
cd /d "%~dp0"

echo.
echo  ========================================
echo    SIA - Desktop AI Assistant
echo    Your Personal AI Companion
echo  ========================================
echo.

REM Check virtual environment
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment found
    set PYTHON=.venv\Scripts\python.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    echo [!] No virtual environment - using system Python
    set PYTHON=python
)

REM Check .env file
if not exist ".env" (
    echo [ERROR] .env file not found!
    pause
    exit /b 1
)

echo [OK] Starting Sia Desktop...
echo.

REM Launch Sia Desktop
%PYTHON% sia_desktop.py

REM If error occurred
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Sia failed to start! Error code: %errorlevel%
    echo.
    echo Troubleshooting:
    echo   1. Make sure .venv exists (run: python -m venv .venv)
    echo   2. Install requirements: .venv\Scripts\pip install -r requirements.txt
    echo   3. Check .env has GEMINI_API_KEY set
    echo.
    pause
)
