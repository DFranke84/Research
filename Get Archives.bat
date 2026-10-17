@echo off
rem Downloads the free Kiwix archives the starter packs are built from (current versions, resumable, checked).
title Get Archives
setlocal
set "PY=%~dp0_scripts\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Library Manager is not set up yet - run Setup.bat first.
  pause
  exit /b 1
)
"%PY%" "%~dp0_scripts\get_archives.py" %*
echo.
pause
