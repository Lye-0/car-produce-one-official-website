@echo off
set "CPO_BLENDER=%ProgramFiles%\Blender Foundation\Blender 5.2\blender.exe"
if not exist "%CPO_BLENDER%" (
  echo Blender 5.2 was not found. Open assets\blender\CPO_v15_refined.blend manually.
  pause
  exit /b 1
)
start "" "%CPO_BLENDER%" "%~dp0assets\blender\CPO_v15_refined.blend"
