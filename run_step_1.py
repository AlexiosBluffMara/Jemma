#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(["python", "--version"], capture_output=True, text=True, cwd=r"D:\JemmaRepo\Jemma")
print("=" * 60)
print("STEP 1: python --version")
print("=" * 60)
print(f"Exit Code: {result.returncode}")
print(f"Output:\n{result.stdout}")
if result.stderr:
    print(f"Errors:\n{result.stderr}")
sys.exit(result.returncode)
