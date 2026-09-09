@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp002_render\scripts\render.ps1" %*
if errorlevel 1 (
  echo CPO pipeline stopped. Verified output is retained for resume.
  pause
  exit /b 1
)
pause
