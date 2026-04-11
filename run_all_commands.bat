@echo off
REM Full notebook execution with all three commands
REM This batch file executes all three required commands and captures output

setlocal enabledelayedexpansion

set "PYTHON_EXE=d:\unsloth\studio\.venv\Scripts\python.exe"
set "NOTEBOOK_RUNNER=d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
set "NOTEBOOK=d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
set "REPORT_JSON=d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json"

echo.
echo ================================================================================
echo                    COMMAND 1: Check Python Version
echo ================================================================================
echo Executing: %PYTHON_EXE% --version
echo.
call %PYTHON_EXE% --version
echo.

echo ================================================================================
echo                    COMMAND 2: Check Dependencies
echo ================================================================================
echo Executing: %PYTHON_EXE% -c "import torch, unsloth, datasets, trl; print('all ok')"
echo.
call %PYTHON_EXE% -c "import torch, unsloth, datasets, trl; print('all ok')"
echo.

echo ================================================================================
echo                    COMMAND 3: Run Notebook
echo ================================================================================
echo Executing: %PYTHON_EXE% %NOTEBOOK_RUNNER% %NOTEBOOK%
echo.
echo This may take 10-60+ minutes. Please wait...
echo.
call %PYTHON_EXE% %NOTEBOOK_RUNNER% %NOTEBOOK%

if exist "%REPORT_JSON%" (
    echo.
    echo ================================================================================
    echo                    NOTEBOOK RUN REPORT
    echo ================================================================================
    type "%REPORT_JSON%"
)

echo.
echo ================================================================================
echo                    EXECUTION COMPLETE
echo ================================================================================
