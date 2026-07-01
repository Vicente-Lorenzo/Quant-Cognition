@echo off
setlocal
title Conda Environment Updater
set CONDA_ALWAYS_YES=true
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
set "CONDA_DIR=C:\ProgramData\miniforge3\condabin"
set "ENVS_DIR=C:\ProgramData\miniforge3\envs"

echo -----------------------------------------------
echo Updating Conda Environments...
echo -----------------------------------------------

cd /d "%CONDA_DIR%"

echo [1/3] Quant Environment...
call :ensure_env Quant "%PROJECT_DIR%\Quant.yml"
if %ERRORLEVEL% NEQ 0 goto :failed

echo [2/3] Future Environment...
call :ensure_env Future "%PROJECT_DIR%\Future.yml"
if %ERRORLEVEL% NEQ 0 goto :failed

echo [3/3] Exotics Environment...
call :ensure_env Exotics "%PROJECT_DIR%\Exotics.yml"
if %ERRORLEVEL% NEQ 0 goto :failed

echo -----------------------------------------------
echo Update Complete.
echo -----------------------------------------------
timeout /t 10
exit /b 0

:ensure_env
if exist "%ENVS_DIR%\%~1\conda-meta\history" (
    echo Updating %~1 ...
    call mamba env update -f "%~2" --prune
) else (
    echo Creating %~1 ...
    call mamba env create -f "%~2"
)
exit /b %ERRORLEVEL%

:failed
echo -----------------------------------------------
echo Update Failed.
echo -----------------------------------------------
timeout /t 10
exit /b 1