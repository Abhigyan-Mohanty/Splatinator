@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

echo ==============================================
echo   Splatinator Binary Installer
echo ==============================================
echo.
echo Please select your target operating system:
echo 1) Windows (x86_64)
echo 2) macOS (Apple Silicon / Intel)
echo 3) Linux (x86_64)
echo.

set /p choice="Enter choice (1-3) [Default 1]: "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    set TARGET_OS=windows
    echo You selected Windows.
    echo Would you like the CUDA version of COLMAP? (Recommended for NVIDIA GPUs)
    set /p cuda="Enable CUDA? (y/n) [Default y]: "
    if "!cuda!"=="n" (set VARIANT=nocuda) else (set VARIANT=cuda)
    python download_binaries.py --os windows --colmap_variant !VARIANT!
) else if "%choice%"=="2" (
    echo You selected macOS.
    python download_binaries.py --os macos
) else if "%choice%"=="3" (
    echo You selected Linux.
    python download_binaries.py --os linux
) else (
    echo Invalid choice.
    pause
    exit /b 1
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================
echo   Installation successfully finished!
echo ==============================================
pause
