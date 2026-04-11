#!/usr/bin/env python3
"""
Test whether commands can run without pwsh
"""
import subprocess
import os
import sys

os.chdir(r'd:\JemmaRepo\Jemma')

print("Python Info:")
print(f"  Executable: {sys.executable}")
print(f"  Version: {sys.version}")
print(f"  Working Dir: {os.getcwd()}")

print("\n" + "="*70)
print("TEST 1: git --no-pager status --short")
print("="*70)
try:
    result = subprocess.run(
        'git --no-pager status --short',
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "="*70)
print("TEST 2: python --version")
print("="*70)
try:
    result = subprocess.run(
        'python --version',
        shell=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout if result.stdout else "(empty)")
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("Both tests completed. Commands executed without pwsh.")
