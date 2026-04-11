#!/usr/bin/env python3
import subprocess
import sys
import os
import json

os.chdir('d:\\JemmaRepo\\Jemma')

results = {}

# Command 1
print("=== COMMAND 1: Python version ===")
try:
    r = subprocess.run(['d:\\unsloth\\studio\\.venv\\Scripts\\python.exe', '--version'], capture_output=True, text=True, timeout=10)
    results['cmd1'] = {
        'returncode': r.returncode,
        'stdout': r.stdout,
        'stderr': r.stderr
    }
    print(f"Return code: {r.returncode}")
    print(f"stdout: {r.stdout}")
    print(f"stderr: {r.stderr}")
except Exception as e:
    results['cmd1'] = {'error': str(e)}
    print(f"Exception: {e}")

# Command 2
print("\n=== COMMAND 2: Import check ===")
try:
    r = subprocess.run(['d:\\unsloth\\studio\\.venv\\Scripts\\python.exe', '-c', "import torch, unsloth, datasets, trl; print('all ok')"], capture_output=True, text=True, timeout=30)
    results['cmd2'] = {
        'returncode': r.returncode,
        'stdout': r.stdout,
        'stderr': r.stderr
    }
    print(f"Return code: {r.returncode}")
    print(f"stdout: {r.stdout}")
    print(f"stderr: {r.stderr}")
except Exception as e:
    results['cmd2'] = {'error': str(e)}
    print(f"Exception: {e}")

# Command 3
print("\n=== COMMAND 3: Run notebook ===")
try:
    r = subprocess.run(['d:\\unsloth\\studio\\.venv\\Scripts\\python.exe', 'd:\\JemmaRepo\\Jemma\\toolbox\\run_notebook_cells.py', 'd:\\JemmaRepo\\Jemma\\gemma4-31b-unsloth-local-5090.ipynb'], capture_output=True, text=True, timeout=600)
    results['cmd3'] = {
        'returncode': r.returncode,
        'stdout': r.stdout,
        'stderr': r.stderr
    }
    print(f"Return code: {r.returncode}")
    print(f"stdout: {r.stdout[:1000]}")  # First 1000 chars
    print(f"stderr: {r.stderr[:1000]}")
except subprocess.TimeoutExpired:
    results['cmd3'] = {'error': 'TIMEOUT: Command exceeded 600 seconds'}
    print("TIMEOUT: Command exceeded 600 seconds")
except Exception as e:
    results['cmd3'] = {'error': str(e)}
    print(f"Exception: {e}")

print("\n=== SUMMARY ===")
print(json.dumps(results, indent=2))
