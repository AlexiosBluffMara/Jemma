@echo off
setlocal enabledelayedexpansion

echo === COMMAND 1 ===
d:\unsloth\studio\.venv\Scripts\python.exe --version
set code1=!ERRORLEVEL!
echo Return Code: !code1!
echo.

echo === COMMAND 2 ===
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
set code2=!ERRORLEVEL!
echo Return Code: !code2!
echo.

echo === COMMAND 3 ===
d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb
set code3=!ERRORLEVEL!
echo Return Code: !code3!
