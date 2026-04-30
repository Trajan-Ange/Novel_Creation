@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo   Novel Creation System - Build Script
echo   v0.3.0 PyInstaller Packaging
echo ========================================
echo(

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

REM Clean previous build
echo [1/4] Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Install dependencies
echo [2/4] Installing dependencies...
python -m pip install -r requirements.txt -q 2>nul

REM Build with PyInstaller
echo [3/4] Building executable...
python -m PyInstaller --onedir --console ^
  --name "NovelCreation" ^
  --add-data "app/static;app/static" ^
  --add-data "config.example.json;." ^
  --hidden-import openai ^
  --hidden-import httpx ^
  --hidden-import fastapi ^
  --hidden-import uvicorn ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import asyncio ^
  --hidden-import app ^
  --hidden-import app.api ^
  --exclude-module numpy ^
  --exclude-module PyQt5 ^
  --exclude-module PIL ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module pandas ^
  --exclude-module setuptools ^
  --exclude-module pip ^
  --exclude-module pkg_resources ^
  --hidden-import app.services ^
  --hidden-import app.skills ^
  --hidden-import app.storage ^
  --hidden-import webview ^
  main.py

if errorlevel 1 (
    echo(
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo(
echo [4/4] Build complete!
echo(
echo Output: dist\NovelCreation\
echo Run:   dist\NovelCreation\NovelCreation.exe
echo(
echo Tip: For a single-file build, change --onedir to --onefile in this script.
echo Tip: For no console window, change --console to --windowed.
echo(
pause
