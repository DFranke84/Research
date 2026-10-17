@echo off
rem Desktop launcher for 63_add_recipe.py: asks for a recipe link, adds it to the personal recipe collection.
setlocal EnableDelayedExpansion
title Add Recipe from URL
cd /d "%~dp0.."

:ask
echo.
set "URL="
set /p "URL=Paste the recipe link (or just press Enter to quit): "
if not defined URL goto :eof
echo Folder: press Enter to sort it automatically, or type  1 = Air Fryer   2 = Instant Pot   3 = Food Recipes
set "F="
set /p "F=Folder: "
set "OPT="
if "!F!"=="1" set "OPT=--folder air-fryer"
if "!F!"=="2" set "OPT=--folder instant-pot"
if "!F!"=="3" set "OPT=--folder food-recipes"
echo.
_scripts\.venv\Scripts\python _scripts\63_add_recipe.py "!URL!" !OPT!
goto ask
