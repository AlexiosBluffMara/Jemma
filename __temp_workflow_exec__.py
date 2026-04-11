#!/usr/bin/env python3
"""Inline workflow executor - will be deleted after execution."""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Files to remove (from previous attempts)
FILES_TO_REMOVE = {
    'run_workflow_now.py', 'run_workflow_now.bat', 'START_EXECUTION.txt',
    'workflow_execution_guide.txt', 'WORKFLOW_INDEX.txt', 
    'environment_adaptation_report.txt', 'EXECUTION_READY.txt'
}

repo_dir = Path(r'D:\JemmaRepo\Jemma')
os.chdir(repo_dir)

report = []
report.append('=== WORKFLOW EXECUTION REPORT ===')
report.append(f'Timestamp: {datetime.now().isoformat()}')
report.append('')

# CLEANUP PHASE
report.append('=== CLEANUP PHASE ===')
removed = []
for fname in FILES_TO_REMOVE:
    fpath = repo_dir / fname
    if fpath.exists():
        try:
            os.remove(fpath)
            removed.append(fname)
            report.append(f'REMOVED: {fname}')
        except Exception as e:
            report.append(f'ERROR removing {fname}: {e}')

report.append(f'Total removed: {len(removed)}')
report.append('')

# STEP 1: python --version
report.append('=== STEP 1: python --version ===')
try:
    result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, cwd=repo_dir, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    report.append(f'Output: {result.stdout.strip()}')
    report.append(f'Stderr: {result.stderr.strip()}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# STEP 2: python -c 'import sys; print(...)'
report.append('=== STEP 2: Interpreter Info ===')
try:
    code = 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=repo_dir, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    report.append(f'Output:\n{result.stdout}')
    if result.stderr:
        report.append(f'Stderr: {result.stderr}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# STEP 3: python -m pip list
report.append('=== STEP 3: python -m pip list (BEFORE) ===')
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, cwd=repo_dir, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    
    # Parse package list - filter for fastapi, discord, uvicorn
    packages_before = []
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for line in lines[2:]:  # Skip header lines
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    pkg_name = parts[0].lower()
                    pkg_version = parts[1]
                    packages_before.append((pkg_name, pkg_version))
                    if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                        report.append(f'  {pkg_name}=={pkg_version}')
    report.append(f'Total packages before: {len(packages_before)}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# STEP 4: python -m pip install -e .
report.append('=== STEP 4: python -m pip install -e . ===')
install_exit_code = None
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], capture_output=True, text=True, cwd=repo_dir, shell=False, timeout=300)
    install_exit_code = result.returncode
    report.append(f'Exit Code: {result.returncode}')
    if result.returncode != 0:
        report.append(f'Stderr (last 1000 chars):\n{result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr}')
    else:
        report.append('Installation succeeded')
except subprocess.TimeoutExpired:
    report.append('ERROR: Installation timed out (>300s)')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# STEP 5: python -m pip list (after install)
report.append('=== STEP 5: python -m pip list (AFTER) ===')
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, cwd=repo_dir, shell=False)
    report.append(f'Exit Code: {result.returncode}')
    
    packages_after = []
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for line in lines[2:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    pkg_name = parts[0].lower()
                    pkg_version = parts[1]
                    packages_after.append((pkg_name, pkg_version))
                    if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                        report.append(f'  {pkg_name}=={pkg_version}')
    report.append(f'Total packages after: {len(packages_after)}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# STEP 6: python -m unittest discover -s tests -p test_*.py -v
report.append('=== STEP 6: python -m unittest discover ===')
tests_summary = {'total': 0, 'passes': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
problem_files = []
try:
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 
                           capture_output=True, text=True, cwd=repo_dir, shell=False, timeout=120)
    report.append(f'Exit Code: {result.returncode}')
    
    # Parse test output
    output = result.stdout + result.stderr
    lines = output.split('\n')
    
    test_lines = []
    for line in lines:
        if ' ... ok' in line or ' ... FAIL' in line or ' ... ERROR' in line or ' ... skipped' in line:
            tests_summary['total'] += 1
            test_lines.append(line.strip())
            if ' ... ok' in line:
                tests_summary['passes'] += 1
            elif ' ... FAIL' in line:
                tests_summary['failures'] += 1
                problem_files.append(line.split(' ')[0])
            elif ' ... ERROR' in line:
                tests_summary['errors'] += 1
                problem_files.append(line.split(' ')[0])
            elif ' ... skipped' in line:
                tests_summary['skipped'] += 1
    
    # Look for summary line
    for line in lines:
        if 'FAILED' in line or 'ERROR' in line or 'Ran' in line:
            report.append(f'  {line.strip()}')
    
    report.append(f'Test Summary: total={tests_summary["total"]}, passed={tests_summary["passes"]}, failed={tests_summary["failures"]}, errors={tests_summary["errors"]}, skipped={tests_summary["skipped"]}')
    if problem_files:
        report.append(f'Problem test files: {list(set(problem_files))}')
    if test_lines:
        report.append(f'Sample test results (first 5):')
        for line in test_lines[:5]:
            report.append(f'  {line}')
        
except subprocess.TimeoutExpired:
    report.append('ERROR: Tests timed out (>120s)')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# Git status
report.append('=== GIT STATUS BEFORE CLEANUP ===')
try:
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, cwd=repo_dir, shell=False)
    if result.returncode == 0:
        status_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        # Filter to only show changed files, not untracked
        modified_only = [l for l in status_lines if l.startswith(('M', 'D', 'A'))]
        report.append(f'Total modified/added/deleted tracked files: {len(modified_only)}')
        for line in modified_only[:10]:
            report.append(f'  {line}')
        if len(modified_only) > 10:
            report.append(f'  ... and {len(modified_only) - 10} more')
    else:
        report.append(f'ERROR: {result.stderr}')
except Exception as e:
    report.append(f'ERROR: {e}')
report.append('')

# Final verification - check for extra files
report.append('=== CLEANUP VERIFICATION ===')
remaining = []
for fname in FILES_TO_REMOVE:
    if (repo_dir / fname).exists():
        remaining.append(fname)

if remaining:
    report.append(f'ERROR: Files still present after cleanup: {remaining}')
else:
    report.append('SUCCESS: All extra files cleaned up')

report.append('')
report.append('=== END OF REPORT ===')

# Write report
report_text = '\n'.join(report)
print(report_text)

with open(repo_dir / 'workflow_report.txt', 'w') as f:
    f.write(report_text)

print('\nReport written to workflow_report.txt')
print('This temp script will now be deleted.')
sys.exit(0)
