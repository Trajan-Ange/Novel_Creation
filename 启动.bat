@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo     Novel Creation System v0.1.1
echo ========================================
echo(

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b
)

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt -q 2>nul

echo [2/3] Opening browser...
start "" "http://127.0.0.1:8000"

echo [3/3] Starting server...
echo(
echo Server running at http://127.0.0.1:8000
echo Close this window to stop the server.
echo(

python main.py
pause
