@echo off
setlocal
title System Environment Updater

echo -----------------------------------------------
echo Updating System Python Environment...
echo -----------------------------------------------

cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"

echo [1/2] Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/2] Updating Requirements...
python -m pip install --upgrade -r Requirements.txt
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