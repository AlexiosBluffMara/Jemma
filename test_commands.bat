@echo off
chcp 65001
cd /d "d:\JemmaRepo\Jemma"

echo ================================================================================
echo COMMAND 1: Python version
echo ================================================================================
echo.
d:\unsloth\studio\.venv\Scripts\python.exe --version
echo Return Code: %ERRORLEVEL%
echo.

echo ================================================================================
echo COMMAND 2: Import check
echo ================================================================================
echo.
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
echo Return Code: %ERRORLEVEL%
echo.

echo ================================================================================
echo COMMAND 3: Notebook execution (long-running)
echo ================================================================================
echo.
echo Starting at %date% %time%
d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb
echo Completed at %date% %time%
echo Return Code: %ERRORLEVEL%
echo.

pause
