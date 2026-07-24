@echo off
title Attrix Lead Generator
color 0B
cd /d "%~dp0"

echo.
echo ============================================
echo      Attrix Lead Generator
echo ============================================
echo.
echo Developed by Vijay Goswami
echo Attrix Technologies | Infusionn Pvt. Ltd.
echo.

REM --- Check we're in the right folder ---
if not exist "app.py" (
    echo [ERROR] app.py not found. Please put this file inside the project folder and run again.
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found. Please put this file inside the project folder and run again.
    pause
    exit /b 1
)

REM --- Check Python is installed ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11 from https://www.python.org/downloads/
    echo IMPORTANT: During installation, enable "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/4] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install project dependencies.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo [3/4] Installing Chromium browser for Playwright...
set PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
python -m playwright install chromium
if errorlevel 1 (
    echo [WARNING] Mirror download failed. Retrying from the official Playwright source...
    set PLAYWRIGHT_DOWNLOAD_HOST=
    python -m playwright install chromium
    if errorlevel 1 (
        echo.
        echo ============================================
        echo      Chromium Installation Failed
        echo ============================================
        echo.
        echo Browser automation will not work until Chromium is installed.
        echo.
        echo Try one of the following:
        echo.
        echo   1. Connect using a VPN or Cloudflare WARP
        echo      https://1.1.1.1/
        echo.
        echo   2. Install manually:
        echo      venv\Scripts\activate
        echo      python -m playwright install chromium
        echo.
        pause
        exit /b 1
    )
)

echo [4/4] Launching Attrix Lead Generator...
echo.
echo Application URL:
echo http://127.0.0.1:5000
echo.
echo Developed by Vijay Goswami
echo https://vijaygoswami.com
echo.
echo Attrix Technologies
echo https://www.attrixtech.com
echo.
echo Technology Partner:
echo Infusionn Pvt. Ltd.
echo https://infusionn.in
echo.
echo Keep this window open while the application is running.
echo Press CTRL+C to stop the server.
echo.

REM --- Give Flask time to start before opening the browser ---
start "" cmd /c "timeout /t 4 >nul && start http://127.0.0.1:5000"

python app.py

pause
