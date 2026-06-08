@echo off
title Environment Updater
echo -----------------------------------------------
echo Updating Conda Environments...
echo -----------------------------------------------

cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"

echo [1/2] Updating Quant Environment...
call mamba env update -f Quant.yml --prune
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/2] Updating Future Environment...
call mamba env update -f Future.yml --prune
if %ERRORLEVEL% NEQ 0 goto :failed

echo -----------------------------------------------
echo Update Complete.
echo -----------------------------------------------
timeout /t 10 >nul
goto :eof

:failed
echo -----------------------------------------------
echo Update Failed.
echo -----------------------------------------------
cmd /k
