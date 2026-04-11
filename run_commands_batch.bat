@echo off
setlocal enabledelayedexpansion

echo ================================================================================
echo COMMAND 1: Check Python version
echo ================================================================================
d:\unsloth\studio\.venv\Scripts\python.exe --version
echo Return code: !ERRORLEVEL!

echo.
echo ================================================================================
echo COMMAND 2: Check imports
echo ================================================================================
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
echo Return code: !ERRORLEVEL!

echo.
echo ================================================================================
echo COMMAND 3: Run notebook cells
echo ================================================================================
d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1
echo Return code: !ERRORLEVEL!
