@echo off
setlocal enabledelayedexpansion

REM Command 1: Python version
echo ============================================================
echo COMMAND 1: Python version
echo ============================================================
d:\unsloth\studio\.venv\Scripts\python.exe --version
set "cmd1_code=!errorlevel!"
echo Return code: !cmd1_code!

REM Command 2: Import test
echo.
echo ============================================================
echo COMMAND 2: Import test
echo ============================================================
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
set "cmd2_code=!errorlevel!"
echo Return code: !cmd2_code!

REM Command 3: Run notebook script
echo.
echo ============================================================
echo COMMAND 3: Run notebook cells script
echo ============================================================
d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb
set "cmd3_code=!errorlevel!"
echo Return code: !cmd3_code!

REM If command 3 failed, try to read report
if !cmd3_code! neq 0 (
    echo.
    echo ============================================================
    echo Reading notebook_run_report.json (command 3 failed with code !cmd3_code!)
    echo ============================================================
    if exist "d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json" (
        type "d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json"
    ) else (
        echo Report file not found
    )
)

endlocal
