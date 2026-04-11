#!/usr/bin/env python3
"""
Final workflow execution - STANDALONE
No external tool dependencies - pure Python subprocess
"""
import subprocess
import os
import sys
from pathlib import Path

# Change to repo directory
os.chdir(r'D:\JemmaRepo\Jemma')

# Simple execution
print("Executing workflow steps...")

# Step 1
result1 = subprocess.run(['python', '--version'], capture_output=True, text=True)
print(f"Step 1: {result1.returncode}, stdout={result1.stdout}, stderr={result1.stderr}")

# Step 2
result2 = subprocess.run(['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'], capture_output=True, text=True)
print(f"Step 2: {result2.returncode}, stdout={result2.stdout}, stderr={result2.stderr}")

# Step 3
result3 = subprocess.run(['python', '-m', 'pip', 'list'], capture_output=True, text=True)
print(f"Step 3: {result3.returncode}, packages listed")

# Step 4
print("Step 4: Running pip install -e . (this may take a while)...")
result4 = subprocess.run(['python', '-m', 'pip', 'install', '-e', '.'], capture_output=True, text=True, timeout=600)
print(f"Step 4: {result4.returncode}")

# Step 4 supplemental
result4s = subprocess.run(['python', '-m', 'pip', 'list'], capture_output=True, text=True)
print(f"Step 4 supplemental: {result4s.returncode}")

# Step 5
print("Step 5: Running unittest discover...")
result5 = subprocess.run(['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], capture_output=True, text=True)
print(f"Step 5: {result5.returncode}")

# Write report
report_path = Path(r'D:\JemmaRepo\Jemma\workflow_report.txt')

with open(report_path, 'w') as f:
    f.write('=' * 80 + '\n')
    f.write('WORKFLOW EXECUTION REPORT\n')
    f.write('=' * 80 + '\n\n')
    
    f.write('STEP 1: python --version\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result1.returncode}\n')
    f.write(f'STDOUT:\n{result1.stdout}\n')
    f.write(f'STDERR:\n{result1.stderr}\n\n')
    
    f.write('STEP 2: Python interpreter info\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result2.returncode}\n')
    f.write(f'STDOUT:\n{result2.stdout}\n')
    f.write(f'STDERR:\n{result2.stderr}\n\n')
    
    f.write('STEP 3: pip list (before install)\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result3.returncode}\n')
    
    # Filter packages
    packages_before = []
    for line in result3.stdout.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
            packages_before.append(line)
    
    f.write(f'Filtered Packages (fastapi, discord, uvicorn):\n')
    for pkg in packages_before:
        f.write(f'  {pkg}\n')
    f.write('\n')
    
    f.write('STEP 4: pip install -e .\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result4.returncode}\n')
    f.write(f'STDOUT (first 2000 chars):\n{result4.stdout[:2000]}\n')
    f.write(f'STDERR (first 2000 chars):\n{result4.stderr[:2000]}\n\n')
    
    f.write('STEP 4 SUPPLEMENTAL: pip list (after install)\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result4s.returncode}\n')
    
    # Filter packages after
    packages_after = []
    for line in result4s.stdout.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
            packages_after.append(line)
    
    f.write(f'Filtered Packages (fastapi, discord, uvicorn):\n')
    for pkg in packages_after:
        f.write(f'  {pkg}\n')
    f.write('\n')
    
    f.write('STEP 5: unittest discover\n')
    f.write('-' * 80 + '\n')
    f.write(f'Exit Code: {result5.returncode}\n')
    f.write(f'STDOUT:\n{result5.stdout}\n')
    f.write(f'STDERR:\n{result5.stderr}\n\n')
    
    # Summary
    f.write('=' * 80 + '\n')
    f.write('SUMMARY\n')
    f.write('=' * 80 + '\n\n')
    
    f.write('Active Interpreter (from Step 2):\n')
    f.write(result2.stdout)
    f.write('\n\n')
    
    f.write('Package Snapshots\n')
    f.write('BEFORE INSTALL (Step 3):\n')
    for pkg in packages_before:
        f.write(f'  {pkg}\n')
    f.write('\n')
    
    f.write('AFTER INSTALL (Step 4 Supplemental):\n')
    for pkg in packages_after:
        f.write(f'  {pkg}\n')
    f.write('\n')
    
    f.write('Exit Codes:\n')
    f.write(f'  Step 1: {result1.returncode}\n')
    f.write(f'  Step 2: {result2.returncode}\n')
    f.write(f'  Step 3: {result3.returncode}\n')
    f.write(f'  Step 4: {result4.returncode}\n')
    f.write(f'  Step 4 (supplemental): {result4s.returncode}\n')
    f.write(f'  Step 5: {result5.returncode}\n')

print(f"\n✓ Report written to: {report_path}")
