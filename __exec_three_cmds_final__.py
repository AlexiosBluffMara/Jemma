#!/usr/bin/env python3
import subprocess
import json
import os
from pathlib import Path

os.chdir(r"d:\JemmaRepo\Jemma")

results = {}

# Command 1
print("Executing command 1...")
try:
    result1 = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe --version',
        capture_output=True,
        text=True,
        timeout=30,
        shell=True
    )
    results['command_1'] = {
        'stdout': result1.stdout,
        'stderr': result1.stderr,
        'exit_code': result1.returncode
    }
except Exception as e:
    results['command_1'] = {'error': str(e), 'exit_code': -1}

print(f"Command 1 exit code: {results['command_1'].get('exit_code', 'error')}")

# Command 2
print("Executing command 2...")
try:
    result2 = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print(\'all ok\')"',
        capture_output=True,
        text=True,
        timeout=60,
        shell=True
    )
    results['command_2'] = {
        'stdout': result2.stdout,
        'stderr': result2.stderr,
        'exit_code': result2.returncode
    }
except Exception as e:
    results['command_2'] = {'error': str(e), 'exit_code': -1}

print(f"Command 2 exit code: {results['command_2'].get('exit_code', 'error')}")

# Command 3
print("Executing command 3...")
try:
    result3 = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1',
        capture_output=True,
        text=True,
        timeout=600,
        shell=True
    )
    results['command_3'] = {
        'stdout': result3.stdout,
        'stderr': result3.stderr,
        'exit_code': result3.returncode
    }
    
    # If command 3 failed, try to read the report
    if result3.returncode != 0:
        report_path = r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json'
        if Path(report_path).exists():
            try:
                with open(report_path, 'r') as f:
                    results['command_3']['notebook_report'] = json.load(f)
            except:
                pass
except Exception as e:
    results['command_3'] = {'error': str(e), 'exit_code': -1}

print(f"Command 3 exit code: {results['command_3'].get('exit_code', 'error')}")

print("\n" + "="*50)
print(json.dumps(results, indent=2))
