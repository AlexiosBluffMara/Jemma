import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
notebook = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
runner = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"

# CMD 1: Version
print("="*80)
print("COMMAND 1: Python Version")
print("="*80)
r1 = subprocess.run([py_exe, "--version"], capture_output=True, text=True)
print(r1.stdout, r1.stderr)

# CMD 2: Dependencies
print("\n" + "="*80)
print("COMMAND 2: Check Dependencies")
print("="*80)
r2 = subprocess.run([py_exe, "-c", "import torch, unsloth, datasets, trl; print('all ok')"], capture_output=True, text=True, timeout=120)
print(r2.stdout, r2.stderr)

# CMD 3: Notebook
print("\n" + "="*80)
print("COMMAND 3: Execute Notebook (will take 10-60+ minutes)")
print("="*80)
r3 = subprocess.run([py_exe, runner, notebook], capture_output=True, text=True, timeout=4000)
print(r3.stdout[-3000:] if len(r3.stdout) > 3000 else r3.stdout)
if r3.stderr:
    print("STDERR:", r3.stderr[-1000:])
print(f"\nReturn Code: {r3.returncode}")

# Check report
report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
if report_path.exists():
    print("\n" + "="*80)
    print("NOTEBOOK RUN REPORT")
    print("="*80)
    report = json.loads(report_path.read_text())
    print(json.dumps(report, indent=2))
