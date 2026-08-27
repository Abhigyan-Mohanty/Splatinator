@echo off
cd /d "%~dp0"
set "TARGET=%~dp0Splatinator.bat"
set "ICON=%~dp0assets\splatinator.ico"
if not exist "%ICON%" set "ICON=%SystemRoot%\System32\shell32.dll,43"
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Splatinator.lnk');" ^
  "$s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%ICON%';" ^
  "$s.Description='Splatinator - Gaussian Splatting pipeline'; $s.Save()"
if %ERRORLEVEL% EQU 0 (
    echo Desktop shortcut created.
) else (
    echo Could not create the shortcut.
)
pause
