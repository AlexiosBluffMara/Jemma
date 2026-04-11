import subprocess
import sys

# Command 1
print("="*70)
print("CMD 1: Python Version")
print("="*70)
r1 = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'], capture_output=True, text=True)
print(r1.stdout, r1.stderr, "RC:", r1.returncode)

# Command 2
print("\n" + "="*70)
print("CMD 2: Dependencies Check")
print("="*70)
r2 = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 'import torch, unsloth, datasets, trl; print("all ok")'], capture_output=True, text=True)
print(r2.stdout, r2.stderr, "RC:", r2.returncode)

# Command 3
print("\n" + "="*70)
print("CMD 3: Notebook Execution (Starting)")
print("="*70)
r3 = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe', r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py', r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'], capture_output=True, text=True, timeout=3700)
print(r3.stdout)
if r3.stderr:
    print("STDERR:", r3.stderr)
print("RC:", r3.returncode)
