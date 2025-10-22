@echo off
chcp 65001 >nul
title Paratranz Web Translator

REM UTF-8 Setting
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set USE_NGROK=false

echo ============================================
echo Paratranz Web Translator
echo ============================================
echo.

REM 필요한 패키지 자동 설치
echo [1/2] Installing packages...
pip install -q flask requests google-generativeai colorama pyngrok
if %errorlevel% neq 0 (
    echo      Failed to install packages
    pause
    exit /b 1
)
echo      Packages installed successfully!

REM 서버 실행
echo [2/2] Starting server...
echo.
echo ============================================
echo Browser will open automatically
echo To stop: Press Ctrl+C
echo ============================================
echo.

python web_translator.py

pause
