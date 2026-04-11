import subprocess
import sys
import os
import re
from datetime import datetime

os.chdir(r'D:\JemmaRepo\Jemma')

# Record files before execution
pre_files = set(os.listdir('.'))

# Get git status before
git_before = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)

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
print("="*80)
print("EXECUTING WORKFLOW")
print("="*80)
for i, (desc, cmd) in enumerate(steps, 1):
    print(f"\nStep {i}: {desc}")
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
            'stderr': 'Command timed out'
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

print("\n" + "="*80)
print("GENERATING REPORT")
print("="*80)

# Generate comprehensive report
report = []
report.append("="*80)
report.append("JEMMA WORKFLOW EXECUTION REPORT")
report.append("="*80)
report.append(f"Execution Date: {datetime.now().isoformat()}")
report.append(f"Repository: D:\\JemmaRepo\\Jemma")
report.append("")

# Candidate file status
report.append("CANDIDATE FILE STATUS:")
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
    exists = "EXISTS (tracked)" if os.path.exists(fname) else "MISSING"
    report.append(f"  {fname}: {exists}")
report.append("")

# Interpreter info from step 2
report.append("="*80)
report.append("INTERPRETER INFORMATION")
report.append("="*80)
report.append(f"Python executable: {sys.executable}")
report.append(f"Python version: {sys.version}")
report.append(f"Version info: {sys.version_info}")
report.append("")

# Step-by-step results
for i in range(1, 7):
    r = results.get(f'step{i}', {})
    report.append("="*80)
    report.append(f"STEP {i}: {r.get('desc', 'UNKNOWN')}")
    report.append("="*80)
    report.append(f"Exit Code: {r.get('exit_code', 'N/A')}")
    report.append("")
    
    if r.get('stdout'):
        # For steps 3 and 5 (pip list), filter for our packages
        if i in [3, 5]:
            report.append(f"Output (full list - {i} lines shown):")
            lines = r['stdout'].split('\n')
            report.append(f"  Total lines: {len([x for x in lines if x.strip()])}")
            report.append("")
            report.append("  Full pip list output:")
            for line in lines[:200]:
                report.append(f"    {line}")
            report.append("")
            report.append("  Filtered packages (fastapi/discord/uvicorn):")
            filtered = [line for line in lines if any(x in line.lower() for x in ['fastapi', 'discord', 'uvicorn'])]
            if filtered:
                for line in filtered:
                    report.append(f"    {line}")
            else:
                report.append("    (none found)")
        else:
            report.append("Output:")
            for line in r['stdout'].split('\n')[:100]:
                report.append(f"  {line}")
    
    if r.get('stderr'):
        report.append("STDERR:")
        for line in r['stderr'].split('\n')[:100]:
            report.append(f"  {line}")
    
    report.append("")

# Test summary parsing
report.append("="*80)
report.append("TEST SUMMARY")
report.append("="*80)
step6_out = results.get('step6', {}).get('stdout', '') + results.get('step6', {}).get('stderr', '')

# Parse test results
tests_run = 0
tests_ok = 0
tests_failed = 0
tests_errors = 0
tests_skipped = 0

# Look for standard test result patterns
ran_match = re.search(r'Ran (\d+) test', step6_out)
if ran_match:
    tests_run = int(ran_match.group(1))
    report.append(f"Tests run: {tests_run}")

# Look for result summary
ok_match = re.search(r'OK', step6_out)
if ok_match:
    tests_ok = tests_run
    report.append("Result: OK")
else:
    fail_match = re.search(r'FAILED.*?failures=(\d+)', step6_out)
    if fail_match:
        tests_failed = int(fail_match.group(1))
        report.append(f"Failures: {tests_failed}")
    
    error_match = re.search(r'errors=(\d+)', step6_out)
    if error_match:
        tests_errors = int(error_match.group(1))
        report.append(f"Errors: {tests_errors}")

report.append(f"Summary: {tests_run} total / {tests_ok} OK / {tests_failed} failed / {tests_errors} errors")
report.append("")

# Artifact detection and cleanup
report.append("="*80)
report.append("ARTIFACTS & CLEANUP")
report.append("="*80)
post_files = set(os.listdir('.'))
new_files = post_files - pre_files
report.append(f"Files before: {len(pre_files)}")
report.append(f"Files after: {len(post_files)}")
report.append(f"New files created: {len(new_files)}")
report.append("")

# Define artifact patterns
artifact_patterns = ['.egg-info', 'build', 'dist', '__pycache__', '.pytest_cache']
artifacts_found = []

for fname in new_files:
    if fname not in ['workflow_report.txt', '_INLINE_EXEC.py', 'ORCHESTRATION.py']:
        fpath = os.path.join('.', fname)
        for pattern in artifact_patterns:
            if pattern in fname.lower():
                artifacts_found.append(fname)
                report.append(f"Artifact detected: {fname}")
                break

# Clean up artifacts
if artifacts_found:
    report.append(f"\nRemoving {len(artifacts_found)} artifacts...")
    import shutil
    for fname in artifacts_found:
        try:
            fpath = os.path.join('.', fname)
            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
                report.append(f"  Removed directory: {fname}")
            else:
                os.remove(fpath)
                report.append(f"  Removed file: {fname}")
        except Exception as e:
            report.append(f"  Failed to remove {fname}: {e}")
else:
    report.append("No new artifacts to clean up")
report.append("")

# Final git status
report.append("="*80)
report.append("FINAL GIT STATUS")
report.append("="*80)
try:
    git_final = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    report.append("Modified/Untracked files:")
    if git_final.stdout.strip():
        for line in git_final.stdout.strip().split('\n'):
            report.append(f"  {line}")
    else:
        report.append("  (clean working tree)")
except Exception as e:
    report.append(f"  Error getting git status: {e}")
report.append("")

# Summary
report.append("="*80)
report.append("EXECUTION SUMMARY")
report.append("="*80)
for i in range(1, 7):
    r = results.get(f'step{i}', {})
    report.append(f"Step {i} ({r.get('desc', 'UNKNOWN')}): Exit code {r.get('exit_code', 'N/A')}")

report.append("")
report.append("Orchestration Command Form:")
report.append('  python -c "import subprocess; subprocess.run([sys.executable, \'SCRIPT.py\'], cwd=r\'D:\\JemmaRepo\\Jemma\')"')
report.append("")
report.append("Note: PowerShell (pwsh) is unavailable - executed via subprocess.run() with shell=False")
report.append("")

# Write report
with open('workflow_report.txt', 'w') as f:
    f.write('\n'.join(report))

print("\nReport written to: workflow_report.txt")

# Verify
print("\n" + "="*80)
print("VERIFYING RESULTS")
print("="*80)
print(f"workflow_report.txt exists: {os.path.exists('workflow_report.txt')}")
with open('workflow_report.txt', 'r') as f:
    content = f.read()
    print(f"Report size: {len(content)} bytes")
    print(f"Report lines: {len(content.split(chr(10)))}")

print("\nFinal git status:")
git_final = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(git_final.stdout)

print("\n" + "="*80)
print("WORKFLOW COMPLETE")
print("="*80)
