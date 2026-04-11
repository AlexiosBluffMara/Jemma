#!/usr/bin/env python3
import subprocess
import json
import os
import sys

os.chdir(r"d:\JemmaRepo\Jemma")

results = {}

# Command 1: EXACT command as specified
cmd1 = r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe --version"'
try:
    p1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    results["cmd1"] = {
        "stdout": p1.stdout.strip(),
        "stderr": p1.stderr.strip(),
        "exit_code": p1.returncode
    }
except Exception as e:
    results["cmd1"] = {"stdout": "", "stderr": str(e), "exit_code": -1}

# Command 2: EXACT command as specified
cmd2 = r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe -c \"import torch, unsloth, datasets, trl; print(\'all ok\')\""'
try:
    p2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    results["cmd2"] = {
        "stdout": p2.stdout.strip(),
        "stderr": p2.stderr.strip(),
        "exit_code": p2.returncode
    }
except Exception as e:
    results["cmd2"] = {"stdout": "", "stderr": str(e), "exit_code": -1}

# Command 3: EXACT command as specified - wait for completion
cmd3 = r'cmd /c "d:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1"'
try:
    p3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True, timeout=3600)
    results["cmd3"] = {
        "stdout": p3.stdout.strip() if len(p3.stdout.strip()) < 50000 else p3.stdout.strip()[:50000] + "\n...[truncated]",
        "stderr": p3.stderr.strip() if len(p3.stderr.strip()) < 50000 else p3.stderr.strip()[:50000] + "\n...[truncated]",
        "exit_code": p3.returncode
    }
except subprocess.TimeoutExpired:
    results["cmd3"] = {"stdout": "", "stderr": "Timeout after 3600 seconds", "exit_code": -1}
except Exception as e:
    results["cmd3"] = {"stdout": "", "stderr": str(e), "exit_code": -1}

# If command 3 failed, read the report
if results.get("cmd3", {}).get("exit_code") != 0:
    try:
        report_path = r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json"
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report_data = json.load(f)
                results["cmd3_report"] = report_data
    except Exception as e:
        results["cmd3_report_error"] = str(e)

print(json.dumps(results, indent=2))
