@echo off
setlocal
title Gemini CLI Cache Cleaner
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
echo -----------------------------------------------
echo Cleaning Gemini CLI Cache and Temp files...
echo -----------------------------------------------

if exist "%USERPROFILE%\.gemini" (
    echo [1/2] Cleaning User profile cache...
    del /s /q /f "%USERPROFILE%\.gemini\cache\*.*" >nul 2>&1
    del /s /q /f "%USERPROFILE%\.gemini\tmp\*.*" >nul 2>&1
    echo Done.
) else (
    echo [1/2] Standard .gemini folder not found. Skipping.
)

if exist "%PROJECT_DIR%\.gemini" (
    echo [2/2] Cleaning local project cache in cAlgo...
    del /s /q /f "%PROJECT_DIR%\.gemini\cache\*.*" >nul 2>&1
    del /s /q /f "%PROJECT_DIR%\.gemini\tmp\*.*" >nul 2>&1
    echo Done.
) else (
    echo [2/2] Local .gemini folder not found. Skipping.
)

echo -----------------------------------------------
echo Cleanup Complete. Your CLI should be faster now.
echo -----------------------------------------------
timeout /t 10 >nul