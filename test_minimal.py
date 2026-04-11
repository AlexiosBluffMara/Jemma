#!/usr/bin/env python3
import subprocess
import sys

repo = r"D:\JemmaRepo\Jemma"

# Step 1
print("Step 1: python --version")
r = subprocess.run(["python", "--version"], cwd=repo, capture_output=True, text=True)
print(f"Exit: {r.returncode}")
print(f"Output: {r.stdout}")
if r.stderr: print(f"Error: {r.stderr}")

# Step 2
print("\nStep 2: python sys info")
r = subprocess.run(["python", "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"], cwd=repo, capture_output=True, text=True)
print(f"Exit: {r.returncode}")
print(f"Output: {r.stdout}")
if r.stderr: print(f"Error: {r.stderr}")

print("\nDone!")
