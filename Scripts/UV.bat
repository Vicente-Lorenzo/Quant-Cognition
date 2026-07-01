@echo off
setlocal
title UV Environment Updater
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
set "UV_DIR=%USERPROFILE%\.local\bin"
set "REQUIREMENTS=%PROJECT_DIR%\Requirements.txt"

echo -----------------------------------------------
echo Updating System Python Environment (UV)...
echo -----------------------------------------------

cd /d "%UV_DIR%"

echo [1/1] Updating Requirements...
uv pip install --system --upgrade -r "%REQUIREMENTS%"
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