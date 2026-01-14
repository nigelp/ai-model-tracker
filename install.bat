@echo off
echo ========================================
echo AI Model Tracker - One-Click Installer
echo ========================================
echo.

echo Step 1: Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found! Installing Python...
    start https://www.python.org/downloads/
    echo Please install Python 3.8+ and run this script again
    pause
    exit /b 1
)

echo Step 2: Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment
    echo Try: pip install virtualenv
    pause
    exit /b 1
)

 echo Step 3: Installing packages...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo Step 4: Creating project structure...
mkdir data 2>nul
mkdir reports 2>nul

echo.
echo ========================================
echo INSTALLATION COMPLETE!
echo ========================================
echo.
echo To start the tracker:
echo   1. Double-click 'start_tracker.bat'
echo   2. Open browser to: http://localhost:5000
echo.
pause
