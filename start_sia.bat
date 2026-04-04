@echo off
title SIA - AI Desktop Assistant
color 0B
cls

echo.
echo  ============================================================
echo    SIA - Premium AI Desktop Assistant
echo    Built for: Amar Kumar ^| B.Tech CSE @ RIT Roorkee
echo  ============================================================
echo.

:: Navigate to project folder
cd /d "%~dp0"

:: Check Python is available
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! Please install Python 3.9+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Activate virtual environment if it exists
IF EXIST ".venv\Scripts\activate.bat" (
    echo [OK] Activating virtual environment...
    call .venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    echo [OK] Activating venv...
    call venv\Scripts\activate.bat
) ELSE (
    echo [WARN] No venv found - using system Python
    echo [HINT] Run: python -m venv .venv  to create one
)

:: Check if .env exists
IF NOT EXIST ".env" (
    echo [WARN] .env file not found! AI features will not work.
    echo [HINT] Create .env with: GEMINI_API_KEY=your_key_here
)

:: Install/check critical dependencies silently
echo [OK] Checking dependencies...
python -c "import PyQt5" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [INSTALL] Installing PyQt5...
    pip install PyQt5 --quiet
)

python -c "import edge_tts" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [INSTALL] Installing edge-tts...
    pip install edge-tts --quiet
)

echo.
echo  Starting Sia... Kaafi mehnat ki hai usne aaj! ^<3
echo  Press Ctrl+C in this window to quit.
echo.

:: Launch Sia with proper error capture
python sia_desktop.py 2>logs\startup_error.log

:: If Sia exited with error, show log
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Sia crashed! Error log:
    type logs\startup_error.log
    echo.
    pause
)
