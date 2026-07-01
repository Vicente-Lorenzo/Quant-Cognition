@echo off
setlocal
title Antigravity CLI
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
echo -----------------------------------------------
echo Starting Antigravity CLI...
echo -----------------------------------------------

echo [1/1] Launching Antigravity in project directory...
cd /d "%PROJECT_DIR%"
agy --dangerously-skip-permissions

echo -----------------------------------------------
echo Antigravity CLI Terminated.
echo -----------------------------------------------
cmd /k