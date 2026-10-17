@echo off
rem Builds the starter packs you pick into library pages (safe to stop and run again).
title Build Starter Library
setlocal
set "PY=%~dp0_scripts\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Library Manager is not set up yet - run Setup.bat first.
  pause
  exit /b 1
)
"%PY%" "%~dp0_scripts\build_starter.py" %*
echo.
pause
