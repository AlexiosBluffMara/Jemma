#!/usr/bin/env python
"""Direct CLI test - execute git and python commands"""

import subprocess
import sys
import os

os.chdir(r'd:\JemmaRepo\Jemma')

print("=" * 60)
print("Test 1: git --no-pager status --short")
print("=" * 60)
try:
    result = subprocess.run(['git', '--no-pager', 'status', '--short'], 
                          capture_output=True, text=True)
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test 2: python --version")
print("=" * 60)
try:
    result = subprocess.run(['python', '--version'], 
                          capture_output=True, text=True)
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test 3: python.exe --version (explicit)")
print("=" * 60)
try:
    result = subprocess.run(['python.exe', '--version'], 
                          capture_output=True, text=True)
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test 4: git.exe --version")
print("=" * 60)
try:
    result = subprocess.run(['git.exe', '--version'], 
                          capture_output=True, text=True)
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
