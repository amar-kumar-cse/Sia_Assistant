# Sia Assistant - Setup Script
# Creates virtual environment and installs all dependencies

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  SIA ASSISTANT - SETUP" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✓ Python found: $($pythonCmd.Version)" -ForegroundColor Green
Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv .venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "✓ pip upgraded" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
Write-Host "(This may take a few minutes)" -ForegroundColor Gray
pip install -r requirements.txt --quiet
Write-Host "✓ All dependencies installed" -ForegroundColor Green
Write-Host ""

# Check for .env file
Write-Host "Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "! Creating .env template..." -ForegroundColor Yellow
    
    $envTemplate = @"
# Sia Assistant Configuration
# Fill in your API keys below

# Gemini API Key (Get from: https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# ElevenLabs API Key (Get from: https://elevenlabs.io/app/settings/api-keys)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# ElevenLabs Voice ID (Default: Rachel)
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# ElevenLabs Model (Turbo for speed)
ELEVENLABS_MODEL=eleven_turbo_v2
"@
    
    $envTemplate | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ .env template created" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT: Please edit .env and add your API keys!" -ForegroundColor Red
}
Write-Host ""

# Create assets folder if needed
if (-not (Test-Path "assets")) {
    New-Item -ItemType Directory -Path "assets" | Out-Null
    Write-Host "✓ Created assets folder" -ForegroundColor Green
}

# Create study_notes folder for RAG
if (-not (Test-Path "study_notes")) {
    New-Item -ItemType Directory -Path "study_notes" | Out-Null
    Write-Host "✓ Created study_notes folder (for PDF notes)" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file with your API keys" -ForegroundColor White
Write-Host "2. Place avatar images in assets/ folder" -ForegroundColor White
Write-Host "3. Run: .\start_sia.bat" -ForegroundColor White
Write-Host ""
pause
