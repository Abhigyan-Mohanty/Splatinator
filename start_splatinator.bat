@echo off
:: Compatibility shim - Splatinator.bat is the launcher now.
cd /d "%~dp0"
call "%~dp0Splatinator.bat" %*
