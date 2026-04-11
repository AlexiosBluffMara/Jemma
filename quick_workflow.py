#!/usr/bin/env python3
"""Quick workflow executor with immediate output"""
import subprocess
import sys
import os
from pathlib import Path

repo = Path(r'D:\JemmaRepo\Jemma')
report = repo / 'workflow_report.txt'

def run_step(num, name, cmd):
    print(f"\n[STEP {num}] {name}")
    print(f"  Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=600)
        print(f"  Exit: {result.returncode}")
        if result.stdout:
            print(f"  Stdout: {result.stdout[:200]}")
        if result.stderr:
            print(f"  Stderr: {result.stderr[:200]}")
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

# Execute steps
results = {}
results[1] = run_step(1, "python --version", ['python', '--version'])
results[2] = run_step(2, "Python interpreter info", ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'])
results[3] = run_step(3, "pip list (before)", ['python', '-m', 'pip', 'list'])
results[4] = run_step(4, "pip install -e .", ['python', '-m', 'pip', 'install', '-e', '.'])
results[4.5] = run_step(5, "pip list (after)", ['python', '-m', 'pip', 'list'])
results[5] = run_step(6, "unittest discover", ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'])

# Write full report
lines = ['WORKFLOW REPORT\n']
for key in [1, 2, 3, 4, 4.5, 5]:
    r = results[key]
    if r:
        lines.append(f"\nSTEP {key}:")
        lines.append(f"  Exit: {r.returncode}")
        lines.append(f"  Stdout:\n{r.stdout}\n")
        lines.append(f"  Stderr:\n{r.stderr}\n")

with open(report, 'w') as f:
    f.write('\n'.join(lines))

print(f"\n✓ Report written to: {report}")
