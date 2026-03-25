@echo off
cd /d "%~dp0"
call npm.cmd run dev:native
if errorlevel 1 pause
