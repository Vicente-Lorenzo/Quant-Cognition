@echo off
title Environment Updater
set CONDA_ALWAYS_YES=true
set "ENVS_DIR=C:\ProgramData\miniforge3\envs"

echo -----------------------------------------------
echo Updating Conda Environments...
echo -----------------------------------------------

cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"

echo [1/3] Quant Environment...
call :ensure_env Quant Quant.yml
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/3] Future Environment...
call :ensure_env Future Future.yml
if %ERRORLEVEL% NEQ 0 goto :failed

echo [3/3] Exotics Environment...
call :ensure_env Exotics Exotics.yml
if %ERRORLEVEL% NEQ 0 goto :failed

echo -----------------------------------------------
echo Update Complete.
echo -----------------------------------------------
timeout /t 10
goto :eof

:ensure_env
if exist "%ENVS_DIR%\%~1\conda-meta\history" (
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
timeout /t 10
goto :eof