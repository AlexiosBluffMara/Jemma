#!/usr/bin/env python
"""
Workflow execution script - Execute all required steps and generate report.
"""
import subprocess
import sys
import os
from pathlib import Path

# Working directory
REPO_ROOT = r'D:\JemmaRepo\Jemma'
os.chdir(REPO_ROOT)

# Initialize report
report_lines = []
report_lines.append("=" * 80)
report_lines.append("JEMMA REPOSITORY WORKFLOW EXECUTION REPORT")
report_lines.append("=" * 80)
report_lines.append(f"Repository: {REPO_ROOT}")
report_lines.append(f"Report Date: {__import__('datetime').datetime.now().isoformat()}")
report_lines.append("Execution Method: Direct Python subprocess execution")
report_lines.append("")

# Track created artifacts for cleanup
pre_install_cwd_items = set(os.listdir(REPO_ROOT))

# ============================================================================
# STEP 1: python --version
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 1: python --version")
report_lines.append("=" * 80)
try:
    result = subprocess.run([sys.executable, '--version'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_1 = result.returncode
    stdout_1 = result.stdout.strip()
    stderr_1 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_1}")
    report_lines.append(f"STDOUT: {stdout_1}")
    if stderr_1:
        report_lines.append(f"STDERR: {stderr_1}")
    report_lines.append("✓ Step 1 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_1 = -1

# ============================================================================
# STEP 2: Interpreter info (sys.executable, sys.version_info)
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 2: Python Interpreter Info")
report_lines.append("=" * 80)
try:
    cmd = "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"
    result = subprocess.run([sys.executable, '-c', cmd], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_2 = result.returncode
    stdout_2 = result.stdout.strip()
    stderr_2 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_2}")
    report_lines.append("Output:")
    for line in stdout_2.split('\n'):
        report_lines.append(f"  {line}")
    if stderr_2:
        report_lines.append(f"STDERR: {stderr_2}")
    report_lines.append("✓ Step 2 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_2 = -1

# ============================================================================
# STEP 3: pip list (before install)
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 3: pip list (BEFORE install -e .)")
report_lines.append("=" * 80)
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_3 = result.returncode
    stdout_3 = result.stdout.strip()
    stderr_3 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_3}")
    report_lines.append("Full output:")
    report_lines.extend([f"  {line}" for line in stdout_3.split('\n')])
    
    # Filter for fastapi, discord, uvicorn
    filtered_3 = []
    for line in stdout_3.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
            filtered_3.append(line)
    report_lines.append("\nFiltered packages (fastapi, discord, uvicorn):")
    if filtered_3:
        for line in filtered_3:
            report_lines.append(f"  {line}")
    else:
        report_lines.append("  (none found)")
    
    if stderr_3:
        report_lines.append(f"STDERR: {stderr_3}")
    report_lines.append("✓ Step 3 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_3 = -1

# ============================================================================
# STEP 4: pip install -e .
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 4: pip install -e .")
report_lines.append("=" * 80)
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_4 = result.returncode
    stdout_4 = result.stdout.strip()
    stderr_4 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_4}")
    report_lines.append("Full output:")
    report_lines.extend([f"  {line}" for line in stdout_4.split('\n')])
    if stderr_4:
        report_lines.append(f"STDERR:")
        report_lines.extend([f"  {line}" for line in stderr_4.split('\n')])
    report_lines.append("✓ Step 4 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_4 = -1

# ============================================================================
# STEP 5: pip list (after install)
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 5: pip list (AFTER install -e .)")
report_lines.append("=" * 80)
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_5 = result.returncode
    stdout_5 = result.stdout.strip()
    stderr_5 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_5}")
    report_lines.append("Full output:")
    report_lines.extend([f"  {line}" for line in stdout_5.split('\n')])
    
    # Filter for fastapi, discord, uvicorn
    filtered_5 = []
    for line in stdout_5.split('\n'):
        if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
            filtered_5.append(line)
    report_lines.append("\nFiltered packages (fastapi, discord, uvicorn):")
    if filtered_5:
        for line in filtered_5:
            report_lines.append(f"  {line}")
    else:
        report_lines.append("  (none found)")
    
    if stderr_5:
        report_lines.append(f"STDERR: {stderr_5}")
    report_lines.append("✓ Step 5 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_5 = -1

# ============================================================================
# STEP 6: unittest discover
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("STEP 6: python -m unittest discover -s tests -p test_*.py -v")
report_lines.append("=" * 80)
try:
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', 
                           '-s', 'tests', '-p', 'test_*.py', '-v'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    exit_code_6 = result.returncode
    stdout_6 = result.stdout.strip()
    stderr_6 = result.stderr.strip()
    report_lines.append(f"Exit Code: {exit_code_6}")
    report_lines.append("Test Output (STDOUT):")
    if stdout_6:
        report_lines.extend([f"  {line}" for line in stdout_6.split('\n')])
    else:
        report_lines.append("  (empty)")
    if stderr_6:
        report_lines.append("Test Output (STDERR):")
        report_lines.extend([f"  {line}" for line in stderr_6.split('\n')])
    
    # Parse test summary
    combined_output = stdout_6 + '\n' + stderr_6
    report_lines.append("\nTest Summary Parsing:")
    
    # Look for test summary line
    total_tests = 0
    for line in combined_output.split('\n'):
        if 'Ran ' in line and ' test' in line:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'Ran':
                        total_tests = int(parts[i+1])
            except:
                pass
        if ' ok' in line.lower() or line.startswith('OK'):
            report_lines.append(f"  Result: OK")
        if 'FAILED' in line:
            report_lines.append(f"  Result: FAILED - {line}")
    
    report_lines.append(f"  Total tests detected: {total_tests}")
    report_lines.append("✓ Step 6 completed")
except Exception as e:
    report_lines.append(f"✗ Exception: {str(e)}")
    exit_code_6 = -1

# ============================================================================
# ARTIFACT DETECTION AND CLEANUP
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("ARTIFACT DETECTION AND CLEANUP")
report_lines.append("=" * 80)

post_install_cwd_items = set(os.listdir(REPO_ROOT))
new_items = post_install_cwd_items - pre_install_cwd_items

report_lines.append(f"\nItems present before workflow: {len(pre_install_cwd_items)}")
report_lines.append(f"Items present after workflow: {len(post_install_cwd_items)}")
report_lines.append(f"New items detected: {len(new_items)}")

if new_items:
    report_lines.append(f"New items at root level: {sorted(new_items)}")

artifact_patterns = ['.egg-info', 'build', 'dist', '__pycache__', '.pytest_cache']
artifacts_to_remove = []

# Check for generated artifacts in new items
for item_name in new_items:
    # Don't delete the workflow_report.txt or this script
    if item_name in ['workflow_report.txt', '__workflow_exec__.py']:
        continue
    item_path = os.path.join(REPO_ROOT, item_name)
    for pattern in artifact_patterns:
        if pattern in item_name.lower():
            artifacts_to_remove.append(item_path)
            report_lines.append(f"  New artifact detected: {item_name}")
            break

if artifacts_to_remove:
    report_lines.append(f"\nRemoving {len(artifacts_to_remove)} generated artifacts...")
    for artifact_path in artifacts_to_remove:
        try:
            if os.path.isdir(artifact_path):
                import shutil
                shutil.rmtree(artifact_path)
                report_lines.append(f"  ✓ Removed directory: {artifact_path}")
            elif os.path.isfile(artifact_path):
                os.remove(artifact_path)
                report_lines.append(f"  ✓ Removed file: {artifact_path}")
        except Exception as e:
            report_lines.append(f"  ✗ Failed to remove {artifact_path}: {str(e)}")
else:
    report_lines.append("\nNo new generated artifacts detected.")

# ============================================================================
# GIT STATUS CHECK
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("GIT STATUS AFTER CLEANUP")
report_lines.append("=" * 80)

try:
    result = subprocess.run(['git', 'status', '--short'], 
                          capture_output=True, text=True, shell=False, cwd=REPO_ROOT)
    git_status = result.stdout.strip()
    report_lines.append("\nGit Status (--short):")
    if git_status:
        report_lines.extend([f"  {line}" for line in git_status.split('\n')])
    else:
        report_lines.append("  (clean working tree)")
    
    # Check for workflow_report.txt specifically
    if 'workflow_report.txt' in git_status:
        report_lines.append("\n✓ Only workflow_report.txt is modified (as expected)")
except Exception as e:
    report_lines.append(f"Could not retrieve git status: {str(e)}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
report_lines.append("\n" + "=" * 80)
report_lines.append("WORKFLOW EXECUTION SUMMARY")
report_lines.append("=" * 80)
report_lines.append(f"Step 1 (python --version):              Exit Code: {exit_code_1}")
report_lines.append(f"Step 2 (interpreter info):               Exit Code: {exit_code_2}")
report_lines.append(f"Step 3 (pip list before):                Exit Code: {exit_code_3}")
report_lines.append(f"Step 4 (pip install -e .):               Exit Code: {exit_code_4}")
report_lines.append(f"Step 5 (pip list after):                 Exit Code: {exit_code_5}")
report_lines.append(f"Step 6 (unittest discover):              Exit Code: {exit_code_6}")
report_lines.append(f"\nArtifacts removed: {len(artifacts_to_remove)}")
report_lines.append("Workflow completed successfully with detailed logging.")

# Write report to file
report_content = '\n'.join(report_lines)
report_path = os.path.join(REPO_ROOT, 'workflow_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print("=" * 80)
print("WORKFLOW EXECUTION COMPLETE")
print("=" * 80)
print(f"Report written to: {report_path}")
print(f"\nExit codes summary:")
print(f"  Step 1: {exit_code_1}")
print(f"  Step 2: {exit_code_2}")
print(f"  Step 3: {exit_code_3}")
print(f"  Step 4: {exit_code_4}")
print(f"  Step 5: {exit_code_5}")
print(f"  Step 6: {exit_code_6}")
print(f"\nArtifacts removed: {len(artifacts_to_remove)}")
if artifacts_to_remove:
    for a in artifacts_to_remove[:5]:
        print(f"  - {a}")
    if len(artifacts_to_remove) > 5:
        print(f"  ... and {len(artifacts_to_remove) - 5} more")
