@echo off
setlocal
title Cache Cleaner
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"

echo -----------------------------------------------
echo Cleaning Python Cache and Temp files...
echo -----------------------------------------------

cd /d "%PROJECT_DIR%"

echo [1/2] Removing Python cache folders...
for /d /r . %%d in (__pycache__ .pytest_cache .mypy_cache .ruff_cache .ipynb_checkpoints) do @if exist "%%d" rd /s /q "%%d"

echo [2/2] Removing stray compiled files...
del /s /q /f "%PROJECT_DIR%\*.pyc" >nul 2>&1
del /s /q /f "%PROJECT_DIR%\*.pyo" >nul 2>&1

echo -----------------------------------------------
echo Cleanup Complete.
echo -----------------------------------------------
timeout /t 10 >nul