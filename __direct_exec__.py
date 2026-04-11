#!/usr/bin/env python3
"""
Direct subprocess execution of the three commands.
This file self-executes to capture command outputs.
"""
import subprocess
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    results = {
        "routes_attempted": ["direct_subprocess_via_python_direct"],
        "commands": {},
        "prior_known_failed_routes": [
            "powershell-tool failed before execution because pwsh missing",
            "pylance-run-code-snippet/python-subprocess timed out"
        ]
    }
    
    # Command 1: Python version
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=10)
        results["commands"]["1_python_version"] = {
            "exit_code": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }
    except Exception as e:
        results["commands"]["1_python_version"] = {"error": str(e)}
    
    # Command 2: Import check
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 'import torch, unsloth, datasets, trl; print("all ok")'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=60)
        results["commands"]["2_import_check"] = {
            "exit_code": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }
    except Exception as e:
        results["commands"]["2_import_check"] = {"error": str(e)}
    
    # Command 3: Notebook execution
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py', r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout, _ = proc.communicate(timeout=900)
        results["commands"]["3_notebook_execution"] = {
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": None
        }
        
        # Check for report if failed
        if proc.returncode != 0:
            report_path = Path(r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json')
            if report_path.exists():
                try:
                    with open(report_path) as f:
                        report = json.load(f)
                    results["notebook_run_report"] = report
                except Exception as e:
                    results["notebook_run_report_error"] = str(e)
    except subprocess.TimeoutExpired:
        proc.kill()
        results["commands"]["3_notebook_execution"] = {"error": "timeout_after_900s"}
    except Exception as e:
        results["commands"]["3_notebook_execution"] = {"error": str(e)}
    
    print(json.dumps(results, indent=2))
