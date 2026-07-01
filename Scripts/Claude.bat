@echo off
setlocal
title Claude CLI
set "PROJECT_DIR=C:\Users\Admin\OneDrive\Documents\cAlgo"
echo -----------------------------------------------
echo Starting Claude CLI...
echo -----------------------------------------------

echo [1/1] Launching Claude in project directory...
cd /d "%PROJECT_DIR%"
claude --dangerously-skip-permissions

echo -----------------------------------------------
echo Claude CLI Terminated.
echo -----------------------------------------------
cmd /k