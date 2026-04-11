#!/usr/bin/env python3
import subprocess
import sys

# Test 1
print("CMD1: Version")
r = subprocess.run([r"d:\unsloth\studio\.venv\Scripts\python.exe", "--version"], capture_output=True, text=True)
print(f"RC:{r.returncode} OUT:{r.stdout} ERR:{r.stderr}")

# Test 2
print("\nCMD2: Imports")
r = subprocess.run([r"d:\unsloth\studio\.venv\Scripts\python.exe", "-c", "import torch, unsloth, datasets, trl; print('all ok')"], capture_output=True, text=True)
print(f"RC:{r.returncode} OUT:{r.stdout} ERR:{r.stderr}")

# Test 3
print("\nCMD3: Notebook")
r = subprocess.run([r"d:\unsloth\studio\.venv\Scripts\python.exe", r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py", r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"], capture_output=True, text=True, timeout=600)
print(f"RC:{r.returncode}")
if r.stdout:
    print(f"OUT:{r.stdout[:1000]}")
if r.stderr:
    print(f"ERR:{r.stderr[:1000]}")
