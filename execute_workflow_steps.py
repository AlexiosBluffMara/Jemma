#!/usr/bin/env python3
"""Execute complete workflow with all required steps."""

import subprocess
import os
import sys
from pathlib import Path

repo_path = r"D:\JemmaRepo\Jemma"
report_path = os.path.join(repo_path, "workflow_report.txt")

# Define commands in exact order
commands = [
    ("Step 1: python --version", ["python", "--version"]),
    ("Step 2: python sys.executable and version", ["python", "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"]),
    ("Step 3: pip list (full)", ["python", "-m", "pip", "list"]),
    ("Step 4: pip install -e .", ["python", "-m", "pip", "install", "-e", "."]),
    ("Supplemental: pip list after install", ["python", "-m", "pip", "list"]),
    ("Step 5: unittest discover", ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]),
]

# Store results
results = []
step3_output = None
step4_exit = None
supplemental_output = None
step5_output = None
step5_stderr = None

print("Executing workflow commands...")
print("=" * 80)

for step_name, cmd in commands:
    print(f"\n{step_name}")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, shell=False)
    
    print(f"Exit Code: {result.returncode}")
    
    if result.stdout:
        print(f"STDOUT (first 500 chars):\n{result.stdout[:500]}")
    if result.stderr:
        print(f"STDERR (first 300 chars):\n{result.stderr[:300]}")
    
    # Store for report
    step_info = {
        "name": step_name,
        "command": cmd,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }
    results.append(step_info)
    
    # Capture specific outputs for filtering
    if "Step 3" in step_name:
        step3_output = result.stdout
    if "Step 4" in step_name:
        step4_exit = result.returncode
    if "Supplemental" in step_name:
        supplemental_output = result.stdout
    if "Step 5" in step_name:
        step5_output = result.stdout
        step5_stderr = result.stderr

print("\n" + "=" * 80)
print("Processing output for report...")

# Filter pip list for relevant packages
def filter_pip_packages(pip_output, packages_to_find=["fastapi", "discord", "uvicorn"]):
    lines = pip_output.split('\n') if pip_output else []
    filtered = []
    for line in lines:
        for pkg in packages_to_find:
            if pkg.lower() in line.lower():
                filtered.append(line)
                break
    return filtered

pre_packages = filter_pip_packages(step3_output) if step3_output else []
post_packages = filter_pip_packages(supplemental_output) if supplemental_output else []

# Extract test summary from step 5
def extract_test_summary(output, stderr):
    lines = (output + "\n" + stderr).split('\n') if (output or stderr) else []
    test_files_with_issues = {}
    test_count = 0
    passes = 0
    failures = 0
    errors_count = 0
    skipped = 0
    
    # Parse unittest output
    for line in lines:
        if " ... " in line:  # Test result line
            test_count += 1
            if "ok" in line:
                passes += 1
            elif "FAIL" in line:
                failures += 1
            elif "ERROR" in line:
                errors_count += 1
            elif "skipped" in line:
                skipped += 1
        elif line.startswith("FAIL:") or line.startswith("ERROR:"):
            test_files_with_issues[line] = True
    
    return {
        "total": test_count,
        "passes": passes,
        "failures": failures,
        "errors": errors_count,
        "skipped": skipped,
        "problem_files": list(test_files_with_issues.keys())
    }

test_summary = extract_test_summary(step5_output, step5_stderr)

# Generate report
report_lines = []
report_lines.append("=" * 80)
report_lines.append("JEMMA WORKFLOW EXECUTION REPORT")
report_lines.append("=" * 80)
report_lines.append("")

# Step-by-step results
for i, step in enumerate(results, 1):
    report_lines.append(f"\n{chr(0x2500) * 80}")
    report_lines.append(f"STEP {i}: {step['name']}")
    report_lines.append(f"{chr(0x2500) * 80}")
    report_lines.append(f"Command: {' '.join(step['command'])}")
    report_lines.append(f"Exit Code: {step['exit_code']}")
    report_lines.append("")
    
    if step['stdout']:
        report_lines.append("STDOUT:")
        report_lines.append(step['stdout'])
        report_lines.append("")
    
    if step['stderr']:
        report_lines.append("STDERR:")
        report_lines.append(step['stderr'])
        report_lines.append("")

# Summary section
report_lines.append(f"\n{'=' * 80}")
report_lines.append("SUMMARY")
report_lines.append(f"{'=' * 80}")
report_lines.append("")

# Extract interpreter info from step 2
if len(results) > 1 and results[1]['stdout']:
    report_lines.append("PYTHON INTERPRETER (from Step 2):")
    report_lines.append(results[1]['stdout'])
    report_lines.append("")

# Package snapshots
report_lines.append("PACKAGE SNAPSHOT - BEFORE INSTALL (Step 3 - fastapi/discord/uvicorn):")
if pre_packages:
    for pkg in pre_packages:
        report_lines.append(f"  {pkg}")
else:
    report_lines.append("  (No matching packages found)")
report_lines.append("")

report_lines.append("PACKAGE SNAPSHOT - AFTER INSTALL (Supplemental - fastapi/discord/uvicorn):")
if post_packages:
    for pkg in post_packages:
        report_lines.append(f"  {pkg}")
else:
    report_lines.append("  (No matching packages found)")
report_lines.append("")

# Exit codes
report_lines.append("EXIT CODES:")
for i, step in enumerate(results, 1):
    report_lines.append(f"  Step {i}: {step['exit_code']}")
report_lines.append("")

# Test summary
report_lines.append("TEST SUMMARY (from Step 5):")
report_lines.append(f"  Total Tests: {test_summary['total']}")
report_lines.append(f"  Passes: {test_summary['passes']}")
report_lines.append(f"  Failures: {test_summary['failures']}")
report_lines.append(f"  Errors: {test_summary['errors']}")
report_lines.append(f"  Skipped: {test_summary['skipped']}")
report_lines.append("")

if test_summary['problem_files']:
    report_lines.append("TEST FILES WITH FAILURES/ERRORS:")
    for f in test_summary['problem_files']:
        report_lines.append(f"  {f}")
else:
    report_lines.append("TEST FILES WITH FAILURES/ERRORS: None")
report_lines.append("")

# Write report
with open(report_path, 'w') as f:
    f.write('\n'.join(report_lines))

print(f"\n✓ Report written to: {report_path}")

# Clean up generated files (egg-info, etc.)
print("\nCleaning up generated files...")
cleanup_count = 0
for item in Path(repo_path).glob("**/*.egg-info"):
    import shutil
    try:
        shutil.rmtree(item)
        print(f"  Removed: {item}")
        cleanup_count += 1
    except Exception as e:
        print(f"  Could not remove {item}: {e}")

for item in Path(repo_path).glob("**/__pycache__"):
    import shutil
    try:
        shutil.rmtree(item, ignore_errors=True)
        print(f"  Removed: {item}")
        cleanup_count += 1
    except:
        pass

print(f"\nCleaned up {cleanup_count} items")

# Check final repo state
print("\nVerifying repo state - checking for workflow_report.txt...")
if os.path.exists(report_path):
    print(f"  ✓ {report_path} exists")
    size = os.path.getsize(report_path)
    print(f"    Size: {size} bytes")

print("\n" + "=" * 80)
print("WORKFLOW EXECUTION COMPLETE")
print("=" * 80)
print(f"\nRESULTS SUMMARY:")
print(f"  Report Path: {report_path}")
print(f"  Interpreter: {results[1]['stdout'].split('Executable:')[1].split(chr(10))[0].strip() if len(results) > 1 and 'Executable:' in results[1]['stdout'] else 'Unknown'}")
print(f"  Pre-install packages: {len(pre_packages)} items")
print(f"  Post-install packages: {len(post_packages)} items")
print(f"  Exit codes: {[r['exit_code'] for r in results]}")
print(f"  Test Summary - Total: {test_summary['total']}, Pass: {test_summary['passes']}, Fail: {test_summary['failures']}, Errors: {test_summary['errors']}")
if test_summary['problem_files']:
    print(f"  Problem test files: {len(test_summary['problem_files'])} files")
