@echo off
echo ========================================
echo AI Model Tracker - Starting...
echo ========================================
echo.

echo Step 1: Activating Python environment...
call venv\Scripts\activate.bat

echo Step 2: Running initial model scrape...
python model_scraper.py

echo.
echo Step 3: Starting web dashboard...
echo.
echo ========================================
echo OPEN YOUR BROWSER TO: http://localhost:5000
echo ========================================
echo.
echo You'll see:
echo    - All tracked AI models
echo    - Filter by source/category
echo    - Chinese model highlights
echo    - Size estimates
echo.
echo Press Ctrl+C in this window to stop
echo.

python web_dashboard.py

pause
