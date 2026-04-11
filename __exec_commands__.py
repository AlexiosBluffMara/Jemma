#!/usr/bin/env python3
import subprocess
import json
import sys
import os
from pathlib import Path

results = {
    "routes_attempted": ["direct_subprocess_execution"],
    "commands": {},
    "prior_known_failed_routes": [
        "powershell-tool failed before execution because pwsh missing",
        "pylance-run-code-snippet/python-subprocess timed out"
    ]
}

# Command 1
try:
    result = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe --version',
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    results["commands"]["1_python_version"] = {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
except Exception as e:
    results["commands"]["1_python_version"] = {"error": str(e)}

# Command 2
try:
    result = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print(\'all ok\')"',
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    results["commands"]["2_import_check"] = {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
except Exception as e:
    results["commands"]["2_import_check"] = {"error": str(e)}

# Command 3 - Long running
try:
    result = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb 2>&1',
        shell=True,
        capture_output=True,
        text=True,
        timeout=900
    )
    results["commands"]["3_notebook_execution"] = {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
    
    # Try to read report if command 3 failed
    if result.returncode != 0:
        report_path = Path(r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json')
        if report_path.exists():
            try:
                with open(report_path) as f:
                    report_data = json.load(f)
                results["notebook_run_report"] = report_data
            except Exception as e:
                results["notebook_run_report_error"] = str(e)
except Exception as e:
    results["commands"]["3_notebook_execution"] = {"error": str(e)}

print(json.dumps(results, indent=2))
