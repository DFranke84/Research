@echo off
rem Desktop launcher for 64_add_email_recipe.py: asks for words from the email's subject, adds that recipe email
rem (Outlook folder Email\Recipes) to the personal recipe collection.
setlocal EnableDelayedExpansion
title Add Recipe from Email
cd /d "%~dp0.."

:ask
echo.
echo Put the recipe email in the Outlook folder Email\Recipes first.
set "S="
set /p "S=Words from the email's subject (or just press Enter to quit): "
if not defined S goto :eof
set "OPT="
set "R="
set /p "R=Replace it if it is already in the collection? (y/N): "
if /i "!R!"=="y" set "OPT=--force"
echo.
echo Working - this can take a few minutes...
_scripts\.venv\Scripts\python _scripts\64_add_email_recipe.py "!S!" !OPT!
goto ask
