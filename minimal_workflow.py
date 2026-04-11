#!/usr/bin/env python3
"""
Minimal workflow runner - just the basic steps
"""
import subprocess
import sys
import os
from pathlib import Path

os.chdir(r'D:\JemmaRepo\Jemma')

print("=" * 80)
print("MINIMAL WORKFLOW TEST")
print("=" * 80)
print()

# Step 1: python --version
print("[1/5] Running: python --version")
result = subprocess.run(['python', '--version'], capture_output=True, text=True)
print(f"  Output: {result.stdout.strip()}")
print(f"  Exit Code: {result.returncode}")
print()

# Step 2: python -c (interpreter info)
print("[2/5] Running: python -c (interpreter info)")
result = subprocess.run(
    ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
    capture_output=True,
    text=True
)
print(f"  Output:\n{result.stdout}")
print(f"  Exit Code: {result.returncode}")
print()

# Step 3: pip list
print("[3/5] Running: python -m pip list")
result = subprocess.run(['python', '-m', 'pip', 'list'], capture_output=True, text=True, timeout=60)
print(f"  Found {len(result.stdout.split(chr(10)))} lines in pip list")
print(f"  Exit Code: {result.returncode}")
print()

# Step 4: Check for tests
print("[4/5] Checking test files")
test_dir = Path('tests')
if test_dir.exists():
    test_files = list(test_dir.glob('test_*.py'))
    print(f"  Found {len(test_files)} test files:")
    for f in test_files:
        print(f"    - {f.name}")
else:
    print("  No tests directory found")
print()

# Step 5: List project info
print("[5/5] Project info")
if Path('pyproject.toml').exists():
    print("  ✓ pyproject.toml found")
if Path('src').exists():
    print("  ✓ src directory found")
print()

print("=" * 80)
print("MINIMAL WORKFLOW COMPLETE")
print("=" * 80)
