@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Splatinator

echo ==============================================================
echo    Splatinator - Gaussian Splatting made simple
echo ==============================================================
echo.

set "PYEXE="

:: ---------------------------------------------------------------
:: 1. Find a usable Python (3.9+). Try the venv from a previous run
::    first, then the py launcher, then PATH, then common locations.
:: ---------------------------------------------------------------
call :try_python "%~dp0.venv\Scripts\python.exe"
if defined PYEXE goto have_python

for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do call :try_python "%%P"
if defined PYEXE goto have_python

for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)" 2^>nul') do call :try_python "%%P"
if defined PYEXE goto have_python

for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if not defined PYEXE call :try_python %%D
)
if defined PYEXE goto have_python

:: ---------------------------------------------------------------
:: 2. No Python: install it. winget when available (no admin needed
::    for a per-user scope), otherwise the official installer.
:: ---------------------------------------------------------------
echo No suitable Python installation was found.
echo Splatinator needs Python 3.9 or newer.
echo.
set /p INSTALLPY="Install Python 3.12 automatically now? (Y/n): "
if /i "!INSTALLPY!"=="n" goto no_python

where winget >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo.
    echo Installing Python 3.12 via winget, please wait...
    winget install --id Python.Python.3.12 -e --scope user --silent ^
        --accept-package-agreements --accept-source-agreements
) else (
    call :download_python
)

echo.
echo Re-checking for Python...
for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do call :try_python "%%P"
if not defined PYEXE (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    ) do (
        if not defined PYEXE call :try_python %%D
    )
)
if not defined PYEXE goto no_python

:have_python
echo Using Python: !PYEXE!
echo.

set "QUIET="
echo %* | findstr /i /c:"--check" >nul 2>&1 && set "QUIET=1"

:: ---------------------------------------------------------------
:: 3. Hand over to the bootstrapper: it checks and installs COLMAP,
::    Brush, the MSVC runtime and the Python packages, then starts
::    the app.
:: ---------------------------------------------------------------
"!PYEXE!" "%~dp0bootstrap.py" %*
set "RC=!ERRORLEVEL!"

if not "!RC!"=="0" (
    if not defined QUIET (
        echo.
        echo ==============================================================
        echo   Something went wrong ^(exit code !RC!^).
        echo   Try running:  Splatinator.bat --repair
        echo ==============================================================
        pause
    )
)
endlocal & exit /b %RC%

:: ---------------------------------------------------------------
:try_python
if defined PYEXE exit /b 0
if not exist %1 exit /b 0
%1 -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,9) else 1)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    for %%A in (%1) do set "PYEXE=%%~fA"
)
exit /b 0

:download_python
echo.
echo Downloading the official Python 3.12 installer...
set "PYURL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PYURL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-arm64.exe"
set "PYSETUP=%TEMP%\splatinator-python-setup.exe"
powershell -NoProfile -Command ^
    "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYSETUP%' -UseBasicParsing } catch { exit 1 }"
if not exist "%PYSETUP%" (
    echo [ERROR] Download failed. Install Python manually from https://www.python.org/downloads/
    exit /b 1
)
echo Installing Python (this takes a minute, no admin rights required)...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_tcltk=1 Include_launcher=1
del "%PYSETUP%" >nul 2>&1
exit /b 0

:no_python
echo.
echo [ERROR] Python is still not available.
echo Install it from https://www.python.org/downloads/ and be sure to tick
echo "Add python.exe to PATH", then run Splatinator.bat again.
echo.
pause
endlocal & exit /b 1
