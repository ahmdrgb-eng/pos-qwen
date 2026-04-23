@echo off
color 0A
title POS Qwen - Local Server Launcher
echo.
echo ========================================
echo   🚀 Starting POS Qwen Application
echo ========================================
echo.

REM الانتقال إلى مجلد الملف تلقائياً (حتى لو فتحته من مكان آخر)
cd /d "%~dp0"

REM التحقق من وجود البيئة الافتراضية
if not exist "venv\Scripts\activate.bat" (
    echo ❌ ERROR: Virtual environment not found!
    echo    Please create it first: python -m venv venv
    echo    Then install dependencies: pip install -r requirements.txt
    echo.
    pause
    exit
)

echo ✅ Activating virtual environment...
call venv\Scripts\activate.bat

echo 🌐 Starting Flask server on http://127.0.0.1:5000
echo 💡 Press Ctrl+C to stop the server safely.
echo.

python app.py

pause