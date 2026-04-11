#!/usr/bin/env python
"""Minimal workflow executor - runs steps independently to avoid timeouts"""
import subprocess
import sys
import os
from pathlib import Path
import datetime

REPO_ROOT = r'D:\JemmaRepo\Jemma'
os.chdir(REPO_ROOT)

report_lines = []
report_lines.append("=" * 80)
report_lines.append("JEMMA REPOSITORY WORKFLOW EXECUTION REPORT")
report_lines.append("=" * 80)
report_lines.append(f"Repository: {REPO_ROOT}")
report_lines.append(f"Report Date: {datetime.datetime.now().isoformat()}")
report_lines.append("Execution Method: Minimal Python subprocess execution")
report_lines.append("")

print("Starting workflow execution...")
print(f"Python: {sys.executable}")

# STEP 1
print("\n[1/6] Running: python --version")
try:
    result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, timeout=30)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 1: python --version")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    report_lines.append(f"Output: {result.stdout.strip()}")
    print(f"✓ Exit: {result.returncode}")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# STEP 2
print("[2/6] Running: Python interpreter info")
try:
    cmd = "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"
    result = subprocess.run([sys.executable, '-c', cmd], capture_output=True, text=True, timeout=30)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 2: Python Interpreter Info")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    report_lines.append("Output:")
    for line in result.stdout.split('\n'):
        if line.strip():
            report_lines.append(f"  {line}")
    print(f"✓ Exit: {result.returncode}")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# STEP 3
print("[3/6] Running: pip list (before)")
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, timeout=60)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 3: pip list (BEFORE install -e .)")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    report_lines.append("Output (filtered for key packages):")
    for line in result.stdout.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
            report_lines.append(f"  {line}")
    print(f"✓ Exit: {result.returncode}")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# STEP 4
print("[4/6] Running: pip install -e .")
print("       (This may take 2-5 minutes...)")
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                          capture_output=True, text=True, timeout=300, cwd=REPO_ROOT)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 4: pip install -e .")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    # Just show last 20 lines to avoid huge output
    lines = result.stdout.split('\n')
    report_lines.append(f"Output (last 20 lines of {len(lines)}):")
    for line in lines[-20:]:
        if line.strip():
            report_lines.append(f"  {line}")
    print(f"✓ Exit: {result.returncode}")
except subprocess.TimeoutExpired:
    report_lines.append("✗ TIMEOUT: pip install exceeded 5 minute limit")
    print("✗ TIMEOUT")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# STEP 5
print("[5/6] Running: pip list (after)")
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, timeout=60)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 5: pip list (AFTER install -e .)")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    report_lines.append("Output (filtered for key packages):")
    for line in result.stdout.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn', 'jemma']):
            report_lines.append(f"  {line}")
    print(f"✓ Exit: {result.returncode}")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# STEP 6
print("[6/6] Running: unittest discover")
try:
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                          capture_output=True, text=True, timeout=120, cwd=REPO_ROOT)
    report_lines.append("\n" + "=" * 80)
    report_lines.append("STEP 6: unittest discover")
    report_lines.append("=" * 80)
    report_lines.append(f"Exit Code: {result.returncode}")
    combined = result.stdout + result.stderr
    report_lines.append("Test output:")
    for line in combined.split('\n'):
        if line.strip():
            report_lines.append(f"  {line}")
    print(f"✓ Exit: {result.returncode}")
except subprocess.TimeoutExpired:
    report_lines.append("✗ TIMEOUT: unittest exceeded 2 minute limit")
    print("✗ TIMEOUT")
except Exception as e:
    report_lines.append(f"✗ Error: {e}")
    print(f"✗ Error: {e}")

# Write report
report_lines.append("\n" + "=" * 80)
report_lines.append("WORKFLOW COMPLETED")
report_lines.append("=" * 80)

report_content = '\n'.join(report_lines)
report_path = os.path.join(REPO_ROOT, 'workflow_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"\n✓ Report written to: {report_path}")
print("\nWorkflow execution complete!")
