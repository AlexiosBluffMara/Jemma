@echo off
setlocal enabledelayedexpansion

cd /d D:\JemmaRepo\Jemma

REM Execute Python directly to run the inline workflow
python inline_workflow.py

echo.
echo Workflow execution completed.
pause
