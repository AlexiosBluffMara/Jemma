#!/usr/bin/env python
"""
Minimal workflow execution script - Execute all required steps and generate report.
Optimized for minimal overhead and timeout avoidance.
"""
import subprocess
import sys
import os
import json
from datetime import datetime

REPO_ROOT = r'D:\JemmaRepo\Jemma'
os.chdir(REPO_ROOT)

def run_command(cmd_list, step_name):
    """Run a single command and return result."""
    try:
        result = subprocess.run(cmd_list, 
                              capture_output=True, 
                              text=True, 
                              shell=False, 
                              cwd=REPO_ROOT,
                              timeout=300)  # 5 minute timeout for pip install
        return {
            'success': True,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': f'Command timed out after 300 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e)
        }

# Track filesystem before
pre_items = set(os.listdir(REPO_ROOT))

# Execute steps
results = {}

print("Step 1: python --version")
results['step1'] = run_command([sys.executable, '--version'], 'python --version')
print(f"  Exit code: {results['step1']['exit_code']}")

print("Step 2: Interpreter info")
results['step2'] = run_command([sys.executable, '-c', 
                                 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
                                'interpreter info')
print(f"  Exit code: {results['step2']['exit_code']}")

print("Step 3: pip list (before)")
results['step3_before'] = run_command([sys.executable, '-m', 'pip', 'list'], 'pip list before')
print(f"  Exit code: {results['step3_before']['exit_code']}")

print("Step 4: pip install -e .")
results['step4'] = run_command([sys.executable, '-m', 'pip', 'install', '-e', '.'], 'pip install -e .')
print(f"  Exit code: {results['step4']['exit_code']}")

print("Step 5: pip list (after)")
results['step5_after'] = run_command([sys.executable, '-m', 'pip', 'list'], 'pip list after')
print(f"  Exit code: {results['step5_after']['exit_code']}")

print("Step 6: unittest discover")
results['step6'] = run_command([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                                'unittest discover')
print(f"  Exit code: {results['step6']['exit_code']}")

# Build report
report_lines = []
report_lines.append("=" * 80)
report_lines.append("JEMMA REPOSITORY WORKFLOW EXECUTION REPORT")
report_lines.append("=" * 80)
report_lines.append(f"Repository: {REPO_ROOT}")
report_lines.append(f"Report Date: {datetime.now().isoformat()}")
report_lines.append("")

# Step 1
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 1: python --version")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step1']['exit_code']}")
report_lines.append(f"STDOUT: {results['step1']['stdout'].strip()}")
if results['step1']['stderr'].strip():
    report_lines.append(f"STDERR: {results['step1']['stderr'].strip()}")

# Step 2
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 2: Python Interpreter Info")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step2']['exit_code']}")
report_lines.append("Output:")
for line in results['step2']['stdout'].strip().split('\n'):
    report_lines.append(f"  {line}")
if results['step2']['stderr'].strip():
    report_lines.append(f"STDERR: {results['step2']['stderr'].strip()}")

# Step 3 Before
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 3: pip list (BEFORE install -e .)")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step3_before']['exit_code']}")
report_lines.append("Full output:")
for line in results['step3_before']['stdout'].strip().split('\n'):
    report_lines.append(f"  {line}")

# Filter for dependencies
filtered_3 = []
for line in results['step3_before']['stdout'].strip().split('\n'):
    if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
        filtered_3.append(line)
report_lines.append("\nFiltered packages (fastapi, discord, uvicorn):")
if filtered_3:
    for line in filtered_3:
        report_lines.append(f"  {line}")
else:
    report_lines.append("  (none found)")

# Step 4
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 4: pip install -e .")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step4']['exit_code']}")
report_lines.append("Output (last 50 lines):")
output_lines = results['step4']['stdout'].strip().split('\n')
for line in output_lines[-50:]:
    report_lines.append(f"  {line}")
if results['step4']['stderr'].strip():
    report_lines.append(f"STDERR (last 20 lines):")
    err_lines = results['step4']['stderr'].strip().split('\n')
    for line in err_lines[-20:]:
        report_lines.append(f"  {line}")

# Step 5 After
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 5: pip list (AFTER install -e .)")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step5_after']['exit_code']}")
report_lines.append("Full output:")
for line in results['step5_after']['stdout'].strip().split('\n'):
    report_lines.append(f"  {line}")

# Filter for dependencies
filtered_5 = []
for line in results['step5_after']['stdout'].strip().split('\n'):
    if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
        filtered_5.append(line)
report_lines.append("\nFiltered packages (fastapi, discord, uvicorn):")
if filtered_5:
    for line in filtered_5:
        report_lines.append(f"  {line}")
else:
    report_lines.append("  (none found)")

# Step 6
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 6: python -m unittest discover -s tests -p test_*.py -v")
report_lines.append("=" * 80)
report_lines.append(f"Exit Code: {results['step6']['exit_code']}")
report_lines.append("Test Output (STDOUT):")
if results['step6']['stdout'].strip():
    for line in results['step6']['stdout'].strip().split('\n'):
        report_lines.append(f"  {line}")
else:
    report_lines.append("  (empty)")
if results['step6']['stderr'].strip():
    report_lines.append("Test Output (STDERR):")
    for line in results['step6']['stderr'].strip().split('\n'):
        report_lines.append(f"  {line}")

# Artifact cleanup
report_lines.append("\n" + "=" * 80)
report_lines.append("ARTIFACT DETECTION AND CLEANUP")
report_lines.append("=" * 80)

post_items = set(os.listdir(REPO_ROOT))
new_items = post_items - pre_items

report_lines.append(f"\nItems present before workflow: {len(pre_items)}")
report_lines.append(f"Items present after workflow: {len(post_items)}")
report_lines.append(f"New items detected: {len(new_items)}")

artifact_patterns = ['.egg-info', 'build', 'dist', '__pycache__', '.pytest_cache']
artifacts_to_remove = []

for item_name in new_items:
    if item_name in ['workflow_report.txt', 'run_workflow_now.py']:
        continue
    item_path = os.path.join(REPO_ROOT, item_name)
    for pattern in artifact_patterns:
        if pattern in item_name.lower():
            artifacts_to_remove.append(item_path)
            report_lines.append(f"  Artifact detected: {item_name}")
            break

if artifacts_to_remove:
    report_lines.append(f"\nRemoving {len(artifacts_to_remove)} generated artifacts...")
    import shutil
    for artifact_path in artifacts_to_remove:
        try:
            if os.path.isdir(artifact_path):
                shutil.rmtree(artifact_path)
                report_lines.append(f"  ✓ Removed: {artifact_path}")
            elif os.path.isfile(artifact_path):
                os.remove(artifact_path)
                report_lines.append(f"  ✓ Removed: {artifact_path}")
        except Exception as e:
            report_lines.append(f"  ✗ Failed: {str(e)}")
else:
    report_lines.append("\nNo new generated artifacts detected.")

# Git status
report_lines.append("\n" + "=" * 80)
report_lines.append("GIT STATUS")
report_lines.append("=" * 80)
try:
    git_result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    git_status = git_result.stdout.strip()
    report_lines.append("\nGit Status (--short):")
    if git_status:
        for line in git_status.split('\n'):
            report_lines.append(f"  {line}")
    else:
        report_lines.append("  (clean working tree)")
except Exception as e:
    report_lines.append(f"Could not retrieve git status: {str(e)}")

# Summary
report_lines.append("\n" + "=" * 80)
report_lines.append("EXECUTION SUMMARY")
report_lines.append("=" * 80)
report_lines.append(f"Step 1 (python --version):              Exit Code: {results['step1']['exit_code']}")
report_lines.append(f"Step 2 (interpreter info):              Exit Code: {results['step2']['exit_code']}")
report_lines.append(f"Step 3 (pip list before):               Exit Code: {results['step3_before']['exit_code']}")
report_lines.append(f"Step 4 (pip install -e .):              Exit Code: {results['step4']['exit_code']}")
report_lines.append(f"Step 5 (pip list after):                Exit Code: {results['step5_after']['exit_code']}")
report_lines.append(f"Step 6 (unittest discover):             Exit Code: {results['step6']['exit_code']}")
report_lines.append(f"Artifacts removed: {len(artifacts_to_remove)}")
report_lines.append("Workflow completed.")

# Write report
report_path = os.path.join(REPO_ROOT, 'workflow_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print("\n" + "=" * 80)
print("WORKFLOW COMPLETE")
print("=" * 80)
print(f"Report written to: {report_path}")
print(f"Artifacts removed: {len(artifacts_to_remove)}")
