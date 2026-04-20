@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo [SETUP] Virtual environment not found. Creating...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    
    echo [SETUP] Installing dependencies...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

if not exist ".browser_profile" (
    echo [SETUP] Chrome profile not found. Initializing...
    python -m src.tasks.create_profile
)

echo [INFO] Starting Automated Data Pipeline
python -m src.main

if errorlevel 1 (
    echo [ERROR] Application crashed or closed unexpectedly.
)

pause