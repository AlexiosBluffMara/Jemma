@echo off
REM Command 1: Check Python version
echo ===== COMMAND 1: Python Version =====
call d:\unsloth\studio\.venv\Scripts\python.exe --version
echo.

REM Command 2: Check dependencies
echo ===== COMMAND 2: Check Dependencies =====
call d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
echo.

REM Command 3: Run notebook
echo ===== COMMAND 3: Run Notebook =====
call d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb
