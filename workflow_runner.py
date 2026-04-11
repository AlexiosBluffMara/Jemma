#!/usr/bin/env python3
"""
Comprehensive workflow runner for Jemma repository.
Executes: python version check, pip operations, and unit tests.
Captures all output, parses results, and generates JSON report.
"""

import json
import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple

def run_command(cmd: List[str], cwd: str) -> Tuple[str, str, int]:
    """Execute command and return stdout, stderr, exit_code."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=False)
    return result.stdout, result.stderr, result.returncode

def parse_pip_list(output: str, filters: List[str]) -> List[Dict[str, str]]:
    """Parse pip list output and filter by package names."""
    lines = output.split('\n')
    results = []
    for line in lines:
        for package_name in filters:
            if package_name.lower() in line.lower():
                results.append(line.strip())
                break
    return results

def parse_unittest_output(output: str) -> Dict[str, int]:
    """Parse unittest output to extract test summary."""
    summary = {
        'total': 0,
        'passes': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0
    }
    
    lines = output.split('\n')
    for line in lines:
        # Look for test count lines
        if 'Ran' in line and 'test' in line:
            parts = line.split()
            try:
                summary['total'] = int(parts[1])
            except (IndexError, ValueError):
                pass
        
        # Look for result summary line
        if line.startswith('FAILED') or line.startswith('OK'):
            # Parse failures/errors from stderr output
            if 'FAILED' in line:
                # Extract (failures=X, errors=Y) pattern
                if 'failures=' in line:
                    try:
                        failures = int(line.split('failures=')[1].split()[0].rstrip(','))
                        summary['failures'] = failures
                    except (IndexError, ValueError):
                        pass
                if 'errors=' in line:
                    try:
                        errors = int(line.split('errors=')[1].split()[0].rstrip(','))
                        summary['errors'] = errors
                    except (IndexError, ValueError):
                        pass
            elif 'OK' in line and 'skipped' in line:
                try:
                    skipped = int(line.split('skipped=')[1].split()[0].rstrip(')'))
                    summary['skipped'] = skipped
                    summary['passes'] = summary['total'] - skipped
                except (IndexError, ValueError):
                    pass
    
    # If we have total and no passes yet, calculate it
    if summary['total'] > 0 and summary['passes'] == 0:
        summary['passes'] = summary['total'] - summary['failures'] - summary['errors'] - summary['skipped']
    
    return summary

def find_test_files_with_issues(output: str) -> List[str]:
    """Extract test file names that have failures or errors."""
    problem_files = set()
    lines = output.split('\n')
    
    for line in lines:
        # Look for FAIL and ERROR lines which show file paths
        if 'FAIL:' in line or 'ERROR:' in line:
            # Extract test file reference
            parts = line.split()
            for part in parts:
                if '.py' in part or 'test_' in part:
                    problem_files.add(part)
    
    return sorted(list(problem_files))

def cleanup_generated_files(root_dir: str) -> List[str]:
    """
    Clean up .egg-info, __pycache__, .pyc files.
    Returns list of files that were not cleaned up.
    """
    not_cleaned = []
    
    patterns = [
        ('**/*.egg-info', 'directory'),
        ('**/__pycache__', 'directory'),
        ('**/*.pyc', 'file'),
    ]
    
    for pattern, file_type in patterns:
        for path in Path(root_dir).glob(pattern):
            try:
                if file_type == 'directory':
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except Exception as e:
                not_cleaned.append(str(path))
    
    return not_cleaned

def find_created_modified_files(root_dir: str, initial_state: set) -> List[str]:
    """Find files created or modified during workflow."""
    current_state = set()
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            path = Path(root) / file
            # Skip certain directories
            if '.git' in str(path) or '__pycache__' in str(path):
                continue
            current_state.add(str(path))
    
    return sorted(list(current_state - initial_state))

def snapshot_repo_state(root_dir: str) -> set:
    """Snapshot current repo state."""
    state = set()
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            path = Path(root) / file
            if '.git' not in str(path) and '__pycache__' not in str(path):
                state.add(str(path))
    return state

def main():
    cwd = r"D:\JemmaRepo\Jemma"
    os.chdir(cwd)
    
    # Take initial snapshot
    initial_state = snapshot_repo_state(cwd)
    
    result = {
        'report_path': r"D:\JemmaRepo\Jemma\workflow_report.txt",
        'interpreter_path': '',
        'interpreter_version': '',
        'pre_packages': [],
        'post_packages': [],
        'step_exit_codes': {},
        'supplemental_exit_code': None,
        'test_summary': {},
        'problem_test_files': [],
        'commands': {},
        'repo_state_unchanged': True,
        'remaining_created_or_modified_files': []
    }
    
    package_filters = ['fastapi', 'discord', 'uvicorn']
    
    # Step 1: python --version
    print("[Step 1] Running: python --version")
    stdout, stderr, exit_code = run_command(['python', '--version'], cwd)
    result['commands']['step1'] = {
        'command': 'python --version',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['step_exit_codes']['step1'] = exit_code
    print(f"  Exit code: {exit_code}")
    
    # Step 2: python -c "import sys; ..."
    print("[Step 2] Running: python -c (sys info)")
    cmd = ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)']
    stdout, stderr, exit_code = run_command(cmd, cwd)
    result['commands']['step2'] = {
        'command': 'python -c "import sys; print(\'Executable:\', sys.executable); print(\'Version:\', sys.version_info)"',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['step_exit_codes']['step2'] = exit_code
    
    # Extract interpreter info from step 2
    for line in stdout.split('\n'):
        if 'Executable:' in line:
            result['interpreter_path'] = line.split('Executable:')[1].strip()
        elif 'Version:' in line:
            result['interpreter_version'] = line.split('Version:')[1].strip()
    print(f"  Exit code: {exit_code}")
    print(f"  Interpreter: {result['interpreter_path']}")
    
    # Step 3: python -m pip list (pre)
    print("[Step 3] Running: python -m pip list (pre)")
    stdout, stderr, exit_code = run_command(['python', '-m', 'pip', 'list'], cwd)
    result['commands']['step3'] = {
        'command': 'python -m pip list',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['step_exit_codes']['step3'] = exit_code
    result['pre_packages'] = parse_pip_list(stdout, package_filters)
    print(f"  Exit code: {exit_code}")
    print(f"  Found {len(result['pre_packages'])} pre-install packages")
    
    # Step 4: python -m pip install -e .
    print("[Step 4] Running: python -m pip install -e .")
    stdout, stderr, exit_code = run_command(['python', '-m', 'pip', 'install', '-e', '.'], cwd)
    result['commands']['step4'] = {
        'command': 'python -m pip install -e .',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['step_exit_codes']['step4'] = exit_code
    print(f"  Exit code: {exit_code}")
    
    # Supplemental: python -m pip list (post)
    print("[Supplemental] Running: python -m pip list (post)")
    stdout, stderr, exit_code = run_command(['python', '-m', 'pip', 'list'], cwd)
    result['commands']['supplemental'] = {
        'command': 'python -m pip list',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['supplemental_exit_code'] = exit_code
    result['post_packages'] = parse_pip_list(stdout, package_filters)
    print(f"  Exit code: {exit_code}")
    print(f"  Found {len(result['post_packages'])} post-install packages")
    
    # Step 5: python -m unittest discover
    print("[Step 5] Running: python -m unittest discover -s tests -p test_*.py -v")
    stdout, stderr, exit_code = run_command(
        ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
        cwd
    )
    # Combine stdout and stderr for parsing (unittest writes to stderr)
    combined_output = stdout + '\n' + stderr
    result['commands']['step5'] = {
        'command': 'python -m unittest discover -s tests -p test_*.py -v',
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code
    }
    result['step_exit_codes']['step5'] = exit_code
    result['test_summary'] = parse_unittest_output(combined_output)
    result['problem_test_files'] = find_test_files_with_issues(combined_output)
    print(f"  Exit code: {exit_code}")
    print(f"  Test summary: {result['test_summary']}")
    
    # Cleanup
    print("[Cleanup] Removing generated files...")
    not_cleaned = cleanup_generated_files(cwd)
    
    # Check repo state
    final_state = snapshot_repo_state(cwd)
    new_or_modified = list(final_state - initial_state)
    
    result['remaining_created_or_modified_files'] = new_or_modified
    result['repo_state_unchanged'] = len(new_or_modified) == 0
    
    print(f"  Files not cleaned up: {len(not_cleaned)}")
    print(f"  New/modified files remaining: {len(new_or_modified)}")
    
    # Output JSON result
    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    json_output = json.dumps(result, indent=2)
    print(json_output)
    
    return result

if __name__ == '__main__':
    main()
