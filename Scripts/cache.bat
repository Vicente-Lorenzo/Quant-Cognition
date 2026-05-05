@echo off
title Gemini CLI Cache Cleaner
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

if exist "C:\Users\Admin\OneDrive\Documents\cAlgo\.gemini" (
    echo [2/2] Cleaning local project cache in cAlgo...
    del /s /q /f "C:\Users\Admin\OneDrive\Documents\cAlgo\.gemini\cache\*.*" >nul 2>&1
    del /s /q /f "C:\Users\Admin\OneDrive\Documents\cAlgo\.gemini\tmp\*.*" >nul 2>&1
    echo Done.
) else (
    echo [2/2] Local .gemini folder not found. Skipping.
)

echo -----------------------------------------------
echo Cleanup Complete. Your CLI should be faster now.
echo -----------------------------------------------
timeout /t 10 >nul