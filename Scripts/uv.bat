@echo off
setlocal
title UV Environment Updater

echo -----------------------------------------------
echo Updating System Python Environment (UV)...
echo -----------------------------------------------

cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"

echo [1/1] Updating Requirements...
uv pip install --system --upgrade -r Requirements.txt
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