#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path
import sys

python_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"

# Command 1: Python Version
print("=" * 60)
print("COMMAND 1: Python Version")
print("=" * 60)
result1 = subprocess.run([python_exe, "--version"], capture_output=True, text=True)
print("STDOUT:", result1.stdout)
if result1.stderr:
    print("STDERR:", result1.stderr)
print("Return Code:", result1.returncode)
print()

# Command 2: Import Check
print("=" * 60)
print("COMMAND 2: Import Check")
print("=" * 60)
result2 = subprocess.run(
    [python_exe, "-c", "import torch, unsloth, datasets, trl; print('all ok')"],
    capture_output=True,
    text=True
)
print("STDOUT:", result2.stdout)
if result2.stderr:
    print("STDERR:", result2.stderr)
print("Return Code:", result2.returncode)
print()

# Command 3: Run Notebook
print("=" * 60)
print("COMMAND 3: Running Notebook")
print("=" * 60)
print("Starting notebook execution...")
import datetime
print(f"Start time: {datetime.datetime.now()}")

notebook_path = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
script_path = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"

try:
    result3 = subprocess.run(
        [python_exe, script_path, notebook_path],
        capture_output=True,
        text=True,
        timeout=3600  # 1 hour timeout
    )
    print("STDOUT:")
    print(result3.stdout)
    if result3.stderr:
        print("\nSTDERR:")
        print(result3.stderr)
    print("\nReturn Code:", result3.returncode)
    print(f"End time: {datetime.datetime.now()}")
except subprocess.TimeoutExpired:
    print("ERROR: Notebook execution timed out after 1 hour")
    print(f"End time: {datetime.datetime.now()}")

# Check for failure report
print()
print("=" * 60)
print("Checking for failure report...")
print("=" * 60)
report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
if report_path.exists():
    print("Found report file. Contents:")
    with open(report_path, 'r') as f:
        report_content = f.read()
        print(report_content)
        try:
            report_json = json.loads(report_content)
            print("\nParsed JSON:")
            print(json.dumps(report_json, indent=2))
        except Exception as e:
            print(f"(Could not parse as JSON: {e})")
else:
    print("Report file not found at:", report_path)
