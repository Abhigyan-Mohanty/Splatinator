@echo off
setlocal
cd /d %~dp0

echo ==============================================
echo   Splatinator - Starting Application
echo ==============================================
echo.

:: Check if python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed. 
    echo Please run 'install_requirements.bat' first!
    pause
    exit /b 1
)

:: Launch the script
python splatinator.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] App crashed or encountered an error.
    echo.
    pause
)
