@echo off
setlocal
title System Environment Updater
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
set "PYTHON_DIR=C:\Users\Admin\AppData\Local\Microsoft\WindowsApps"
set "REQUIREMENTS=%PROJECT_DIR%\Requirements.txt"

echo -----------------------------------------------
echo Updating System Python Environment...
echo -----------------------------------------------

cd /d "%PYTHON_DIR%"

echo [1/2] Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/2] Updating Requirements...
python -m pip install --upgrade -r "%REQUIREMENTS%"
if %ERRORLEVEL% NEQ 0 goto :failed

echo -----------------------------------------------
echo Update Complete.
echo -----------------------------------------------
timeout /t 10
exit /b 0

:failed
echo -----------------------------------------------
echo Update Failed.
echo -----------------------------------------------
timeout /t 10
exit /b 1