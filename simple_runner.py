#!/usr/bin/env python
"""Minimal command runner - just execute and print"""
import subprocess
import sys

print("TEST 1: Python version")
print("="*60)
result = subprocess.run(
    [r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'],
    capture_output=True, 
    text=True
)
print(f"RC: {result.returncode}")
print(f"STDOUT: {result.stdout}")
print(f"STDERR: {result.stderr}")
sys.stdout.flush()

print("\nTEST 2: Import check")
print("="*60)
result = subprocess.run(
    [r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 
     'import torch, unsloth, datasets, trl; print("all ok")'],
    capture_output=True,
    text=True,
    timeout=120
)
print(f"RC: {result.returncode}")
print(f"STDOUT: {result.stdout}")
print(f"STDERR: {result.stderr}")
sys.stdout.flush()

print("\nTEST 3: Notebook runner")
print("="*60)
result = subprocess.run(
    [r'd:\unsloth\studio\.venv\Scripts\python.exe',
     r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py',
     r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'],
    capture_output=True,
    text=True,
    timeout=3700  # 61+ minutes
)
print(f"RC: {result.returncode}")
print(f"STDOUT length: {len(result.stdout)}")
print("STDOUT (first 2000 chars):")
print(result.stdout[:2000])
if len(result.stdout) > 2000:
    print("\n... TRUNCATED ...\n")
    print("STDOUT (last 1000 chars):")
    print(result.stdout[-1000:])
print(f"\nSTDERR length: {len(result.stderr)}")
print("STDERR (first 2000 chars):")
print(result.stderr[:2000])
if len(result.stderr) > 2000:
    print("\n... TRUNCATED ...\n")
    print("STDERR (last 1000 chars):")
    print(result.stderr[-1000:])
sys.stdout.flush()
