@echo off
title Environment Updater
echo -----------------------------------------------
echo Updating Conda Environments...
echo -----------------------------------------------

cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"

echo [1/2] Quant Environment...
call :ensure_env Quant Quant.yml
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/2] Future Environment...
call :ensure_env Future Future.yml
if %ERRORLEVEL% NEQ 0 goto :failed

echo -----------------------------------------------
echo Update Complete.
echo -----------------------------------------------
timeout /t 10 >nul
goto :eof

:ensure_env
mamba env list | findstr /B /C:"%~1 " >nul
if %ERRORLEVEL% EQU 0 (
    echo Updating %~1 ...
    call mamba env update -f %~2 --prune
) else (
    echo Creating %~1 ...
    call mamba env create -f %~2
)
exit /b %ERRORLEVEL%

:failed
echo -----------------------------------------------
echo Update Failed.
echo -----------------------------------------------
cmd /k
