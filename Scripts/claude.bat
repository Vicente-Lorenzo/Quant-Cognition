@echo off
title Claude CLI
echo -----------------------------------------------
echo Starting Claude CLI...
echo -----------------------------------------------

echo [1/1] Launching Claude in project directory...
cd /d "C:\Users\Admin\OneDrive\Documents\cAlgo"
claude --dangerously-skip-permissions

echo -----------------------------------------------
echo Claude CLI Terminated.
echo -----------------------------------------------
cmd /k