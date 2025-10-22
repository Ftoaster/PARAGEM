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
echo Installing packages...
pip install -q flask requests google-generativeai colorama pyngrok

echo.
echo Starting server...
echo Browser will open automatically
echo.
echo To stop: Press Ctrl+C
echo ============================================
echo.

python web_translator.py

pause

