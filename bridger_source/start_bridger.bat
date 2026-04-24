@echo off
chcp 65001 >nul 2>&1
title Bridger Fishing Macro
cd /d "%~dp0"

REM Check Python 3.14
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+ from python.org
    pause
    exit /b 1
)

REM Try Python 3.14 first, fall back to python
py -3.14 -c "import sys; print(sys.version)" >nul 2>&1
if %errorlevel% equ 0 (
    set PY=py -3.14
) else (
    python -c "import sys; print(sys.version)" >nul 2>&1
    if %errorlevel% equ 0 (
        set PY=python
    ) else (
        echo [ERROR] Python 3.11+ not found.
        pause
        exit /b 1
    )
)

REM Check dependencies
echo [BRIDGER] Checking dependencies...
%PY% -c "import numpy, scipy, pyautogui, pyaudio, mss, cv2, PIL, pytesseract, keyboard, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Missing dependencies. Run:
    echo   pip install -r requirements.txt
    echo.
    echo Or use the installer:
    echo   BridgerSetup.exe
    pause
    exit /b 1
)

REM Check Tesseract
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Tesseract OCR not found in PATH.
    echo        Install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo        Or copy tesseract folder to: %~dp0assets\tesseract\
    echo.
)

REM Launch
echo [BRIDGER] Starting Bridger Fishing Macro...
echo.
echo   Controls:
echo   F3  - Start / Stop
echo   F1  - Select OCR region
echo   F2  - Exit
echo.
echo   Press F3 to begin. Switch to Roblox.
echo.

REM Run in GUI mode (starts Tkinter status overlay)
REM For headless/HTTP-only mode, use: BridgerBackend.py --headless
cd /d "%~dp0src"
%PY% BridgerBackend.py

pause
