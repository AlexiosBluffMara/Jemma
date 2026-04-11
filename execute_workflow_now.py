#!/usr/bin/env python3
"""
Minimal workflow runner - executes steps and captures output to JSON.
Designed for robustness with minimal dependencies.
"""

import json
import subprocess
import sys
import os
from pathlib import Path

def run_cmd(cmd_list, desc=""):
    """Run command and return output details."""
    print(f"\n>>> {desc}")
    print(f"    Command: {' '.join(cmd_list)}")
    try:
        result = subprocess.run(
            cmd_list, 
            cwd=r"D:\JemmaRepo\Jemma",
            capture_output=True, 
            text=True, 
            shell=False,
            timeout=60
        )
        print(f"    Exit Code: {result.returncode}")
        return {
            "command": " ".join(cmd_list),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd_list),
            "stdout": "",
            "stderr": "TIMEOUT",
            "exit_code": -999
        }
    except Exception as e:
        return {
            "command": " ".join(cmd_list),
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1
        }

# Main execution
print("="*80)
print("JEMMA WORKFLOW EXECUTION")
print("="*80)

os.chdir(r"D:\JemmaRepo\Jemma")

# Collect results
results = {}

# Step 1
results['step1'] = run_cmd(['python', '--version'], 'Step 1: python --version')

# Step 2
results['step2'] = run_cmd(
    ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
    'Step 2: System info'
)

# Step 3
results['step3'] = run_cmd(['python', '-m', 'pip', 'list'], 'Step 3: pip list (pre-install)')

# Step 4
results['step4'] = run_cmd(['python', '-m', 'pip', 'install', '-e', '.'], 'Step 4: pip install -e .')

# Supplemental
results['supplemental'] = run_cmd(['python', '-m', 'pip', 'list'], 'Supplemental: pip list (post-install)')

# Step 5
results['step5'] = run_cmd(
    ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
    'Step 5: unittest discover'
)

# Build report
print("\n" + "="*80)
print("PARSING RESULTS")
print("="*80)

# Extract interpreter info
interp_path = ""
interp_version = ""
for line in results['step2']['stdout'].split('\n'):
    if 'Executable:' in line:
        interp_path = line.split('Executable:')[1].strip()
    elif 'Version:' in line:
        interp_version = line.split('Version:')[1].strip()

# Parse pip packages
def get_packages(pip_output, filters):
    packages = []
    for line in pip_output.split('\n'):
        for pkg in filters:
            if pkg.lower() in line.lower():
                packages.append(line.strip())
                break
    return packages

package_filters = ['fastapi', 'discord', 'uvicorn']
pre_packages = get_packages(results['step3']['stdout'], package_filters)
post_packages = get_packages(results['supplemental']['stdout'], package_filters)

# Parse unittest summary
def parse_test_summary(stdout, stderr):
    combined = stdout + '\n' + stderr
    summary = {'total': 0, 'passes': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    
    for line in combined.split('\n'):
        if 'Ran' in line and 'test' in line:
            try:
                summary['total'] = int(line.split()[1])
            except:
                pass
        if 'FAILED' in line:
            try:
                if 'failures=' in line:
                    summary['failures'] = int(line.split('failures=')[1].split()[0].rstrip(','))
                if 'errors=' in line:
                    summary['errors'] = int(line.split('errors=')[1].split()[0].rstrip(','))
            except:
                pass
        if 'OK' in line and 'skipped=' in line:
            try:
                summary['skipped'] = int(line.split('skipped=')[1].split()[0].rstrip(')'))
            except:
                pass
    
    if summary['total'] > 0 and summary['passes'] == 0:
        summary['passes'] = summary['total'] - summary['failures'] - summary['errors'] - summary['skipped']
    
    return summary

test_summary = parse_test_summary(results['step5']['stdout'], results['step5']['stderr'])

# Compile report
report = {
    "report_path": r"D:\JemmaRepo\Jemma\workflow_report.txt",
    "interpreter_path": interp_path,
    "interpreter_version": interp_version,
    "pre_packages": pre_packages,
    "post_packages": post_packages,
    "step_exit_codes": {
        "step1": results['step1']['exit_code'],
        "step2": results['step2']['exit_code'],
        "step3": results['step3']['exit_code'],
        "step4": results['step4']['exit_code'],
        "step5": results['step5']['exit_code'],
    },
    "supplemental_exit_code": results['supplemental']['exit_code'],
    "test_summary": test_summary,
    "problem_test_files": [],  # Would need more parsing
    "commands": results,
    "repo_state_unchanged": False,
    "remaining_created_or_modified_files": []
}

print("\n" + "="*80)
print("FINAL JSON REPORT")
print("="*80)
json_output = json.dumps(report, indent=2)
print(json_output)

# Also write to file
with open(r"D:\JemmaRepo\Jemma\workflow_report.json", 'w') as f:
    f.write(json_output)
print(f"\nReport written to: D:\\JemmaRepo\\Jemma\\workflow_report.json")
