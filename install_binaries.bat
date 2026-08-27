@echo off
:: Kept for compatibility - Splatinator.bat now does this automatically.
:: Runs the setup steps (COLMAP, Brush, packages) without launching the app.
cd /d "%~dp0"
call "%~dp0Splatinator.bat" --setup
pause
