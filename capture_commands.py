#!/usr/bin/env python3
import subprocess
import json
import sys
import os

os.chdir(r"d:\JemmaRepo\Jemma")

commands = [
    r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe --version"',
    r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe -c \"import torch, unsloth, datasets, trl; print(\'all ok\')\""',
    r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1"'
]

results = []

for cmd in commands:
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=600)  # 10 minute timeout for cmd 3
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        exit_code = -1
        stderr = "TIMEOUT after 600 seconds"
    except Exception as e:
        exit_code = 1
        stdout = ""
        stderr = str(e)
    
    results.append({
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code
    })

output = {"commands": results}

# Check if command 3 failed and read report
if results[2]["exit_code"] != 0:
    report_path = r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json"
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r') as f:
                output["notebook_run_report"] = json.load(f)
        except:
            pass

print(json.dumps(output, indent=2))
