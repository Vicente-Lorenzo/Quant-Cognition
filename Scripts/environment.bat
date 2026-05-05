@echo off
title Environment Updater
echo -----------------------------------------------
echo Updating Conda Environment...
echo -----------------------------------------------

echo [1/1] Executing Mamba update...
cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"
call mamba env update -f Requirements.yml --prune

if %ERRORLEVEL% NEQ 0 (
    echo -----------------------------------------------
    echo Update Failed.
    echo -----------------------------------------------
    cmd /k
) else (
    echo -----------------------------------------------
    echo Update Complete.
    echo -----------------------------------------------
    timeout /t 10 >nul
)