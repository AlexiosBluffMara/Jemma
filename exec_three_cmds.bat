@echo off
setlocal enabledelayedexpansion

REM Command 1: Python version
echo Running Command 1...
d:\unsloth\studio\.venv\Scripts\python.exe --version 2>&1
set CMD1_EXIT=!ERRORLEVEL!

REM Command 2: Import check  
echo.
echo Running Command 2...
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')" 2>&1
set CMD2_EXIT=!ERRORLEVEL!

REM Command 3: Notebook execution
echo.
echo Running Command 3...
d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1
set CMD3_EXIT=!ERRORLEVEL!

echo.
echo Command 1 Exit Code: !CMD1_EXIT!
echo Command 2 Exit Code: !CMD2_EXIT!
echo Command 3 Exit Code: !CMD3_EXIT!

REM Check for report file if command 3 failed
if !CMD3_EXIT! NEQ 0 (
    echo.
    echo Checking for notebook_run_report.json...
    if exist "d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json" (
        echo Report found, displaying first 500 chars:
        powershell -Command "Get-Content 'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json' -Head 500"
    )
)

endlocal
