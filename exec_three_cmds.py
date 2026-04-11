#!/usr/bin/env python3
"""Execute the three required commands and write results"""
import subprocess
import json
import sys
from pathlib import Path

python_exe = r'd:\unsloth\studio\.venv\Scripts\python.exe'
notebook_script = r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py'
notebook_file = r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'
report_output = r'd:\JemmaRepo\Jemma\COMMAND_EXECUTION_REPORT.txt'

results = []

# Command 1
print("=" * 80)
print("COMMAND 1: Python Version")
print("=" * 80)
try:
    result = subprocess.run(
        [python_exe, '--version'],
        capture_output=True,
        text=True,
        timeout=30
    )
    results.append({
        'command': 1,
        'description': 'd:\\unsloth\\studio\\.venv\\Scripts\\python.exe --version',
        'method': 'subprocess.run with list',
        'return_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    })
    print(f"Return Code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
except Exception as e:
    results.append({
        'command': 1,
        'error': str(e)
    })
    print(f"ERROR: {e}")

# Command 2
print("\n" + "=" * 80)
print("COMMAND 2: Import Check")
print("=" * 80)
try:
    result = subprocess.run(
        [python_exe, '-c', 'import torch, unsloth, datasets, trl; print("all ok")'],
        capture_output=True,
        text=True,
        timeout=120
    )
    results.append({
        'command': 2,
        'description': 'd:\\unsloth\\studio\\.venv\\Scripts\\python.exe -c "import torch, unsloth, datasets, trl; print(\'all ok\')"',
        'method': 'subprocess.run with list',
        'return_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    })
    print(f"Return Code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")
except Exception as e:
    results.append({
        'command': 2,
        'error': str(e)
    })
    print(f"ERROR: {e}")

# Command 3
print("\n" + "=" * 80)
print("COMMAND 3: Run Notebook Cells")
print("=" * 80)
try:
    result = subprocess.run(
        [python_exe, notebook_script, notebook_file],
        capture_output=True,
        text=True,
        timeout=3600
    )
    results.append({
        'command': 3,
        'description': 'd:\\unsloth\\studio\\.venv\\Scripts\\python.exe d:\\JemmaRepo\\Jemma\\toolbox\\run_notebook_cells.py d:\\JemmaRepo\\Jemma\\gemma4-31b-unsloth-local-5090.ipynb',
        'method': 'subprocess.run with list',
        'return_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    })
    print(f"Return Code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
except Exception as e:
    results.append({
        'command': 3,
        'error': str(e)
    })
    print(f"ERROR: {e}")

# If command 3 failed, check the report
if results and results[2].get('return_code') != 0:
    print("\n" + "=" * 80)
    print("READING NOTEBOOK RUN REPORT (Command 3 failed)")
    print("=" * 80)
    try:
        report_path = Path(r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json')
        if report_path.exists():
            report_content = report_path.read_text(encoding='utf-8')
            print(report_content)
            results.append({
                'notebook_report': json.loads(report_content)
            })
        else:
            print("Report file not found")
    except Exception as e:
        print(f"Error reading report: {e}")

# Write summary report
print("\n" + "=" * 80)
print("WRITING EXECUTION REPORT")
print("=" * 80)
with open(report_output, 'w', encoding='utf-8') as f:
    f.write("COMMAND EXECUTION REPORT\n")
    f.write("=" * 80 + "\n\n")
    for result in results:
        f.write(json.dumps(result, indent=2) + "\n\n")
    
print(f"Report written to: {report_output}")
print("Done!")
