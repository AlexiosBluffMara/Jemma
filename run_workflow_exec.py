#!/usr/bin/env python3
"""Direct workflow executor."""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json

os.chdir(r'd:\JemmaRepo\Jemma')
repo_dir = Path(r'd:\JemmaRepo\Jemma')

# FILES TO CLEANUP
FILES_TO_REMOVE = {
    'run_workflow_now.py', 'run_workflow_now.bat', 'START_EXECUTION.txt',
    'workflow_execution_guide.txt', 'WORKFLOW_INDEX.txt', 
    'environment_adaptation_report.txt', 'EXECUTION_READY.txt'
}

report = []
report.append('=== WORKFLOW EXECUTION REPORT ===')
report.append(f'Timestamp: {datetime.now().isoformat()}')
report.append(f'Python: {sys.executable}')
report.append(f'Version: {sys.version_info}')
report.append('')

# === CLEANUP PHASE ===
report.append('=== CLEANUP PHASE ===')
removed_count = 0
for fname in FILES_TO_REMOVE:
    fpath = repo_dir / fname
    if fpath.exists():
        try:
            os.remove(fpath)
            removed_count += 1
            report.append(f'REMOVED: {fname}')
        except Exception as e:
            report.append(f'ERROR removing {fname}: {e}')

report.append(f'Total removed: {removed_count}')
report.append('')

# === STEP 1: python --version ===
report.append('=== STEP 1: python --version ===')
try:
    result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    report.append(f'Output: {result.stdout.strip()}')
    if result.stderr.strip():
        report.append(f'Stderr: {result.stderr.strip()}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === STEP 2: Interpreter Info ===
report.append('=== STEP 2: Interpreter Info ===')
try:
    code = 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    report.append(f'Output:\n{result.stdout}')
    if result.stderr.strip():
        report.append(f'Stderr: {result.stderr}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === STEP 3: pip list BEFORE ===
report.append('=== STEP 3: pip list (BEFORE install) ===')
packages_before = {}
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for line in lines[2:]:  # Skip header
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    pkg_name = parts[0].lower()
                    pkg_version = parts[1]
                    packages_before[pkg_name] = pkg_version
                    if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                        report.append(f'  {pkg_name}=={pkg_version}')
        report.append(f'Total packages: {len(packages_before)}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === STEP 4: pip install -e . ===
report.append('=== STEP 4: pip install -e . ===')
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                           capture_output=True, text=True, shell=False, timeout=300, cwd=str(repo_dir))
    report.append(f'Exit Code: {result.returncode}')
    if result.returncode == 0:
        report.append('Installation succeeded')
    else:
        # Show last part of stderr
        stderr_lines = result.stderr.split('\n')
        report.append('Last 20 lines of stderr:')
        for line in stderr_lines[-20:]:
            if line.strip():
                report.append(f'  {line}')
except subprocess.TimeoutExpired:
    report.append('ERROR: pip install timed out (>300s)')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === STEP 5: pip list AFTER ===
report.append('=== STEP 5: pip list (AFTER install) ===')
packages_after = {}
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for line in lines[2:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    pkg_name = parts[0].lower()
                    pkg_version = parts[1]
                    packages_after[pkg_name] = pkg_version
                    if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                        report.append(f'  {pkg_name}=={pkg_version}')
        report.append(f'Total packages: {len(packages_after)}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === STEP 6: unittest discover ===
report.append('=== STEP 6: unittest discover -s tests -p test_*.py -v ===')
test_summary = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
try:
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                           capture_output=True, text=True, shell=False, timeout=120, cwd=str(repo_dir))
    report.append(f'Exit Code: {result.returncode}')
    
    # Combine stdout and stderr
    output = result.stdout + '\n' + result.stderr
    lines = output.split('\n')
    
    # Count test results
    for line in lines:
        stripped = line.strip()
        if ' ... ok' in line:
            test_summary['total'] += 1
            test_summary['passed'] += 1
        elif ' ... FAIL' in line:
            test_summary['total'] += 1
            test_summary['failed'] += 1
        elif ' ... ERROR' in line:
            test_summary['total'] += 1
            test_summary['errors'] += 1
        elif ' ... skipped' in line:
            test_summary['total'] += 1
            test_summary['skipped'] += 1
    
    # Extract summary line
    for line in lines:
        if 'Ran' in line or 'FAILED' in line or 'OK' in line:
            report.append(f'  {line.strip()}')
    
    report.append(f'Parsed Summary: total={test_summary["total"]}, passed={test_summary["passed"]}, failed={test_summary["failed"]}, errors={test_summary["errors"]}, skipped={test_summary["skipped"]}')
        
except subprocess.TimeoutExpired:
    report.append('ERROR: Tests timed out (>120s)')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === GIT STATUS ===
report.append('=== GIT STATUS ===')
try:
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, shell=False, cwd=str(repo_dir))
    if result.returncode == 0:
        lines = [l for l in result.stdout.split('\n') if l.strip()]
        # Separate tracked changes from untracked
        tracked_changes = [l for l in lines if l.startswith(('M ', 'D ', 'A '))]
        untracked = [l for l in lines if l.startswith('??')]
        
        report.append(f'Tracked changes: {len(tracked_changes)}')
        for line in tracked_changes:
            report.append(f'  {line}')
        report.append(f'Untracked files: {len(untracked)}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# === FINAL VERIFICATION ===
report.append('=== CLEANUP VERIFICATION ===')
remaining = []
for fname in FILES_TO_REMOVE:
    if (repo_dir / fname).exists():
        remaining.append(fname)

if remaining:
    report.append(f'ERROR: Extra files still remain: {remaining}')
else:
    report.append('SUCCESS: All extra files removed')

# Check only workflow_report.txt modified
report.append('')
report.append('=== MODIFICATION CHECK ===')
report.append('Allowed modified file: workflow_report.txt')
report.append(f'Script files created: __temp_workflow_exec__.py, run_temp_workflow.bat, exec_workflow_inline.py, run_workflow_exec.py')
report.append('')
report.append('=== END REPORT ===')

# Write report
report_text = '\n'.join(report)
with open('workflow_report.txt', 'w') as f:
    f.write(report_text)

print(report_text)
print('\n✓ Report written to workflow_report.txt')
