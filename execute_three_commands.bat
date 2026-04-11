@echo off
REM Execute the three required commands

setlocal enabledelayedexpansion

set PYTHON_EXE=d:\unsloth\studio\.venv\Scripts\python.exe
set NOTEBOOK_SCRIPT=d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py
set NOTEBOOK_FILE=d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb

cd /d "d:\JemmaRepo\Jemma"

echo.
echo ============================================================================
echo COMMAND 1: Python Version
echo ============================================================================
%PYTHON_EXE% --version
set RC1=!ERRORLEVEL!
echo Return Code: !RC1!

echo.
echo ============================================================================
echo COMMAND 2: Import Check
echo ============================================================================
%PYTHON_EXE% -c "import torch, unsloth, datasets, trl; print('all ok')"
set RC2=!ERRORLEVEL!
echo Return Code: !RC2!

echo.
echo ============================================================================
echo COMMAND 3: Run Notebook Cells
echo ============================================================================
%PYTHON_EXE% "%NOTEBOOK_SCRIPT%" "%NOTEBOOK_FILE%"
set RC3=!ERRORLEVEL!
echo Return Code: !RC3!

echo.
echo ============================================================================
echo SUMMARY
echo ============================================================================
echo Command 1 (Python --version) Return Code: !RC1!
echo Command 2 (Import Check) Return Code: !RC2!
echo Command 3 (Notebook Cells) Return Code: !RC3!

if !RC3! neq 0 (
    echo.
    echo ============================================================================
    echo Reading notebook run report (Command 3 failed)
    echo ============================================================================
    if exist "d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json" (
        type "d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json"
    ) else (
        echo Report file not found
    )
)

pause
