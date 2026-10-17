@echo off
rem Installs or repairs everything Library Manager and the library tools need (safe to run again).
title Library Manager - Setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_scripts\setup.ps1" %*
echo.
pause
