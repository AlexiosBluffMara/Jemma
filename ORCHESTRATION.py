#!/usr/bin/env python
"""
Orchestration script: Execute 6 steps, capture all data, generate workflow_report.txt
This file will be deleted after execution - it's only used for reference to understand the workflow.
The actual execution happens inline via python -c
"""
import subprocess
import sys
import os
import re

os.chdir(r'D:\JemmaRepo\Jemma')

# Record files before execution
pre_files = set(os.listdir('.'))

# Results dictionary
results = {}
steps = [
    ('python --version', [sys.executable, '--version']),
    ('interpreter info', [sys.executable, '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)']),
    ('pip list before', [sys.executable, '-m', 'pip', 'list']),
    ('pip install -e .', [sys.executable, '-m', 'pip', 'install', '-e', '.']),
    ('pip list after', [sys.executable, '-m', 'pip', 'list']),
    ('unittest', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']),
]

# Execute all steps
for i, (desc, cmd) in enumerate(steps, 1):
    print(f"Step {i}: {desc}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=300)
        results[f'step{i}'] = {
            'desc': desc,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        print(f"  Exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        results[f'step{i}'] = {
            'desc': desc,
            'exit_code': -999,
            'stdout': '',
            'stderr': 'Timeout'
        }
        print(f"  TIMEOUT")
    except Exception as e:
        results[f'step{i}'] = {
            'desc': desc,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e)
        }
        print(f"  ERROR: {e}")

# Generate report
report = []
report.append("="*80)
report.append("JEMMA WORKFLOW EXECUTION REPORT")
report.append("="*80)
report.append("")

# Candidate file status
report.append("CANDIDATE FILE STATUS (from pre-execution check):")
candidate_files = [
    'run_workflow_now.py',
    'run_workflow_now.bat',
    'START_EXECUTION.txt',
    'workflow_execution_guide.txt',
    'WORKFLOW_INDEX.txt',
    'environment_adaptation_report.txt',
    'EXECUTION_READY.txt',
    'FINAL_WORKFLOW_EXECUTOR.py',
    'conftest.py',
    'conftest_auto_exec.py'
]
for fname in candidate_files:
    exists = "EXISTS" if os.path.exists(fname) else "MISSING"
    report.append(f"  {fname}: {exists}")
report.append("")

# Step results
for i in range(1, 7):
    r = results.get(f'step{i}', {})
    report.append("="*80)
    report.append(f"STEP {i}: {r.get('desc', 'UNKNOWN')}")
    report.append("="*80)
    report.append(f"Exit Code: {r.get('exit_code', 'N/A')}")
    report.append("")
    if r.get('stdout'):
        report.append("STDOUT:")
        for line in r['stdout'].split('\n')[:100]:  # Limit to first 100 lines
            report.append(f"  {line}")
    if r.get('stderr'):
        report.append("STDERR:")
        for line in r['stderr'].split('\n')[:50]:  # Limit to first 50 lines
            report.append(f"  {line}")
    report.append("")

# Filter packages for steps 3 and 5
for step_num in [3, 5]:
    key = f'step{step_num}'
    if key in results:
        output = results[key]['stdout']
        filtered = [line for line in output.split('\n') if any(x in line.lower() for x in ['fastapi', 'discord', 'uvicorn'])]
        report.append(f"Step {step_num} - Filtered packages (fastapi/discord/uvicorn):")
        if filtered:
            for line in filtered:
                report.append(f"  {line}")
        else:
            report.append("  (none found)")
        report.append("")

# Parse test summary
step6_stderr = results.get('step6', {}).get('stderr', '')
step6_stdout = results.get('step6', {}).get('stdout', '')
test_output = step6_stderr + '\n' + step6_stdout

report.append("TEST SUMMARY PARSING:")
# Look for test result patterns
ran_match = re.search(r'Ran (\d+) test', test_output)
if ran_match:
    report.append(f"  Tests run: {ran_match.group(1)}")
fail_match = re.search(r'FAILED.*failures=(\d+)', test_output)
if fail_match:
    report.append(f"  Failures: {fail_match.group(1)}")
error_match = re.search(r'errors=(\d+)', test_output)
if error_match:
    report.append(f"  Errors: {error_match.group(1)}")
report.append("")

# Artifact detection
report.append("ARTIFACTS:")
post_files = set(os.listdir('.'))
new_files = post_files - pre_files
report.append(f"  New files created: {len(new_files)}")
for f in sorted(new_files):
    if f not in ['workflow_report.txt', 'ORCHESTRATION.py']:
        report.append(f"    {f}")
report.append("")

# Git status
report.append("GIT STATUS:")
try:
    git_result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    git_lines = git_result.stdout.strip().split('\n')
    for line in git_lines[:20]:
        if line.strip():
            report.append(f"  {line}")
except:
    report.append("  (unable to get git status)")
report.append("")

# Summary
report.append("="*80)
report.append("EXECUTION SUMMARY")
report.append("="*80)
for i in range(1, 7):
    r = results.get(f'step{i}', {})
    report.append(f"Step {i}: Exit code {r.get('exit_code', 'N/A')} - {r.get('desc', 'UNKNOWN')}")

report.append("\nPwsh unavailable - workflow executed via subprocess.run() with shell=False")
report.append("Orchestration command form: python -c \"<inline Python code>\"")
report.append("")

# Write report
with open('workflow_report.txt', 'w') as f:
    f.write('\n'.join(report))

print("\n" + "="*80)
print("WORKFLOW COMPLETE")
print("="*80)
print(f"Report written to: workflow_report.txt")
