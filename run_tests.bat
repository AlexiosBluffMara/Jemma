@echo off
setlocal enabledelayedexpansion

REM Create a temporary Python script to run the commands
(
echo import subprocess
echo import json
echo import os
echo.
echo results = {}
echo.
echo # Command 1
echo print("Command 1...", flush=True^)
echo try:
echo     result1 = subprocess.run(
echo         [r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'],
echo         capture_output=True,
echo         text=True,
echo         timeout=30
echo     ^)
echo     results['cmd1'] = {
echo         'stdout': result1.stdout,
echo         'stderr': result1.stderr,
echo         'exit_code': result1.returncode
echo     }
echo except Exception as e:
echo     results['cmd1'] = {'error': str(e^)}
echo.
echo # Command 2
echo print("Command 2...", flush=True^)
echo try:
echo     result2 = subprocess.run(
echo         [r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 
echo          "import torch, unsloth, datasets, trl; print('all ok'^)"],
echo         capture_output=True,
echo         text=True,
echo         timeout=180
echo     ^)
echo     results['cmd2'] = {
echo         'stdout': result2.stdout,
echo         'stderr': result2.stderr,
echo         'exit_code': result2.returncode
echo     }
echo except Exception as e:
echo     results['cmd2'] = {'error': str(e^)}
echo.
echo # Command 3
echo print("Command 3...", flush=True^)
echo try:
echo     result3 = subprocess.run(
echo         [r'd:\unsloth\studio\.venv\Scripts\python.exe', 
echo          r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py',
echo          r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'],
echo         capture_output=True,
echo         text=True,
echo         timeout=7200
echo     ^)
echo     results['cmd3'] = {
echo         'stdout': result3.stdout,
echo         'stderr': result3.stderr,
echo         'exit_code': result3.returncode
echo     }
echo except Exception as e:
echo     results['cmd3'] = {'error': str(e^)}
echo.
echo print(json.dumps(results, indent=2^)^)
) > d:\JemmaRepo\Jemma\temp_run_cmds.py

REM Run the Python script
python d:\JemmaRepo\Jemma\temp_run_cmds.py

REM Clean up
del d:\JemmaRepo\Jemma\temp_run_cmds.py
