@echo off
setlocal
cd /d %~dp0

echo ==============================================
echo   Splatinator Setup - Installing Requirements
echo ==============================================
echo.

:: Check if python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to your PATH!
    echo Please install Python (3.9+) from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Found Python! Version:
python --version
echo.

echo Installing required packages (this might take a minute)...
echo.

:: Upgrade pip first
python -m pip install --upgrade pip

:: Install requirements
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install requirements. Check the error messages above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================
echo   Success! All requirements are installed.
echo   You can now launch the app or download binaries.
echo ==============================================
pause
