@echo off
chcp 65001 >nul
color 0B
title POS Qwen - Remote Server Manager

:: Check SSH
where ssh >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: SSH client not found!
    echo Install it from: Settings > Apps > Optional Features > OpenSSH Client
    echo.
    pause
    exit
)

:menu
cls
echo.
echo ==========================================
echo   POS Qwen Remote Server Manager
echo   Server IP: 165.227.237.32
echo ==========================================
echo.
echo [1] Update Code and Restart Server
echo [2] Check Server Status
echo [3] View Live Logs
echo [4] Open SSH Terminal
echo [0] Exit
echo.
set /p choice="Choose option (0-4): "

if "%choice%"=="1" goto update
if "%choice%"=="2" goto status
if "%choice%"=="3" goto logs
if "%choice%"=="4" goto ssh
if "%choice%"=="0" exit
echo Invalid choice! & pause & goto menu

:update
echo.
echo Connecting to server...
ssh root@165.227.237.32 "cd /var/www/pos_qwen && source venv/bin/activate && git pull origin master && sudo systemctl restart pos_qwen && echo. && echo SUCCESS: Updated and Restarted!"
echo.
pause
goto menu

:status
echo.
echo Server Status:
ssh root@165.227.237.32 "sudo systemctl is-active pos_qwen && sudo systemctl status pos_qwen --no-pager -n 12"
echo.
pause
goto menu

:logs
echo.
echo Live Logs (Press Ctrl+C to return)...
ssh root@165.227.237.32 "sudo journalctl -u pos_qwen -f --no-pager"
goto menu

:ssh
echo.
echo Opening SSH connection...
ssh root@165.227.237.32
goto menu