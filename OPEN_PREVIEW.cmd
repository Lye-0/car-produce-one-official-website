@echo off
cd /d "%~dp001_website"
set "PATH=C:\Users\kawau\AppData\Local\mise\installs\node\24.18.0;%PATH%"
if not exist node_modules call npm.cmd ci
call npm.cmd run dev
pause
