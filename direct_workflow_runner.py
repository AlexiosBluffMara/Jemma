#!/usr/bin/env python3
"""
Direct runner for exec_workflow.py with extended timeout
"""
import subprocess
import sys
import os

os.chdir(r'D:\JemmaRepo\Jemma')

# Run the workflow
print("Executing exec_workflow.py...")
print("=" * 80)

result = subprocess.run(
    [sys.executable, 'exec_workflow.py'],
    timeout=1200,  # 20 minutes
    text=True
)

print("=" * 80)
print(f"Workflow completed with return code: {result.returncode}")
print("\nChecking if workflow_report.txt was created...")

if os.path.exists('workflow_report.txt'):
    print("\n✓ workflow_report.txt found! Contents:\n")
    with open('workflow_report.txt', 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print("\n✗ workflow_report.txt not found")

sys.exit(result.returncode)
