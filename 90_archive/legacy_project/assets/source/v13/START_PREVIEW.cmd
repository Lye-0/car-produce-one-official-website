@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py START_PREVIEW.py
) else (
  python START_PREVIEW.py
)
pause
