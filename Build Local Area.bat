@echo off
rem Builds the Local Area section for where you live: frost dates and weather, plants and wildlife seen nearby, maps.
title Build Local Area
setlocal
set "PY=%~dp0_scripts\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Library Manager is not set up yet - run Setup.bat first.
  pause
  exit /b 1
)
"%PY%" "%~dp0_scripts\build_local_area.py" %*
echo.
pause
