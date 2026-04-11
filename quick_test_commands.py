#!/usr/bin/env python
"""Quick test - no long timeouts"""
import subprocess
import sys
import os

os.chdir(r'd:\JemmaRepo\Jemma')

print("QUICK TEST 1: Python version")
print("="*60)
try:
    result = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe --version',
        shell=True,
        capture_output=True, 
        text=True,
        timeout=10
    )
    print(f"Return code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
except Exception as e:
    print(f"Exception: {e}")

print("\n\nQUICK TEST 2: Import check (short timeout)")
print("="*60)
try:
    result = subprocess.run(
        r'd:\unsloth\studio\.venv\Scripts\python.exe -c "import torch; print(\'torch ok\')"',
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    print(f"Return code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
except Exception as e:
    print(f"Exception: {e}")
