@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp002_render\scripts\render.ps1" -Action final -Profile both -Job all
if errorlevel 1 (
  echo Render or encode stopped. Run this file again to resume.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp002_render\scripts\render.ps1" -Action install
if errorlevel 1 (
  echo Website installation did not complete. Check the error above.
  pause
  exit /b 1
)
echo Repaired production media installed on the local website.
pause
