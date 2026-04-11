#!/usr/bin/env python3
"""
Complete workflow executor.
This script:
1. Cleans up extra files from previous attempts
2. Executes the 6-step workflow
3. Captures all required information
4. Writes workflow_report.txt
5. Cleans up only this script at the end (workflow_report.txt remains)
"""

if __name__ == '__main__':
    import os
    import sys
    import subprocess
    from pathlib import Path
    from datetime import datetime

    os.chdir(r'd:\JemmaRepo\Jemma')
    repo_dir = Path.cwd()

    # Files to clean from previous attempts
    FILES_TO_REMOVE = {
        'run_workflow_now.py', 'run_workflow_now.bat', 'START_EXECUTION.txt',
        'workflow_execution_guide.txt', 'WORKFLOW_INDEX.txt', 
        'environment_adaptation_report.txt', 'EXECUTION_READY.txt',
        '__temp_workflow_exec__.py', 'run_temp_workflow.bat', 'exec_workflow_inline.py',
        'run_workflow_exec.py'
    }

    report = []
    report.append('=' * 60)
    report.append('WORKFLOW EXECUTION REPORT')
    report.append('=' * 60)
    report.append(f'Timestamp: {datetime.now().isoformat()}')
    report.append(f'Working Directory: {repo_dir}')
    report.append('')

    # PHASE 1: CLEANUP
    report.append('PHASE 1: CLEANUP')
    report.append('-' * 60)
    removed_count = 0
    for fname in FILES_TO_REMOVE:
        fpath = repo_dir / fname
        if fpath.exists():
            try:
                os.remove(fpath)
                removed_count += 1
                report.append(f'  ✓ Removed: {fname}')
            except Exception as e:
                report.append(f'  ✗ Error removing {fname}: {e}')

    report.append(f'Total files removed: {removed_count}')
    report.append('')

    # PHASE 2: WORKFLOW EXECUTION
    report.append('PHASE 2: WORKFLOW EXECUTION')
    report.append('-' * 60)

    # STEP 1
    report.append('')
    report.append('STEP 1: python --version')
    report.append('Command: python --version')
    try:
        result = subprocess.run([sys.executable, '--version'], 
                               capture_output=True, text=True, shell=False,
                               timeout=30)
        report.append(f'Exit Code: {result.returncode}')
        report.append(f'Output: {result.stdout.strip()}')
        if result.stderr.strip():
            report.append(f'Stderr: {result.stderr.strip()}')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # STEP 2
    report.append('')
    report.append('STEP 2: Interpreter Information')
    report.append('Command: python -c "import sys; print(...)"')
    try:
        code = 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'
        result = subprocess.run([sys.executable, '-c', code], 
                               capture_output=True, text=True, shell=False,
                               timeout=30)
        report.append(f'Exit Code: {result.returncode}')
        lines = result.stdout.strip().split('\n')
        for line in lines:
            report.append(f'Output: {line}')
        if result.stderr.strip():
            report.append(f'Stderr: {result.stderr}')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # STEP 3
    report.append('')
    report.append('STEP 3: pip list (BEFORE install)')
    report.append('Command: python -m pip list')
    packages_before = {}
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                               capture_output=True, text=True, shell=False,
                               timeout=60)
        report.append(f'Exit Code: {result.returncode}')
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            header_found = False
            for line in lines:
                if line.strip().startswith('Package'):
                    header_found = True
                    continue
                if header_found and line.strip() and not line.startswith('-'):
                    parts = line.split()
                    if len(parts) >= 2:
                        pkg_name = parts[0].lower()
                        pkg_version = parts[1]
                        packages_before[pkg_name] = pkg_version
                        # Report fastapi, discord, uvicorn
                        if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                            report.append(f'  {pkg_name}=={pkg_version}')
            report.append(f'Total packages before: {len(packages_before)}')
            report.append(f'Notable packages: fastapi={packages_before.get("fastapi", "NOT FOUND")}, discord={packages_before.get("discord", "NOT FOUND")}, uvicorn={packages_before.get("uvicorn", "NOT FOUND")}')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # STEP 4
    report.append('')
    report.append('STEP 4: pip install -e .')
    report.append('Command: python -m pip install -e .')
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                               capture_output=True, text=True, shell=False,
                               timeout=300, cwd=str(repo_dir))
        report.append(f'Exit Code: {result.returncode}')
        if result.returncode == 0:
            report.append('Status: Installation SUCCEEDED')
        else:
            report.append('Status: Installation FAILED')
            # Show error details
            stderr_lines = result.stderr.split('\n')
            report.append('Last 30 stderr lines:')
            for line in stderr_lines[-30:]:
                if line.strip():
                    report.append(f'  {line}')
    except subprocess.TimeoutExpired:
        report.append('ERROR: pip install timed out (>300s)')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # STEP 5
    report.append('')
    report.append('STEP 5: pip list (AFTER install)')
    report.append('Command: python -m pip list')
    packages_after = {}
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                               capture_output=True, text=True, shell=False,
                               timeout=60)
        report.append(f'Exit Code: {result.returncode}')
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            header_found = False
            for line in lines:
                if line.strip().startswith('Package'):
                    header_found = True
                    continue
                if header_found and line.strip() and not line.startswith('-'):
                    parts = line.split()
                    if len(parts) >= 2:
                        pkg_name = parts[0].lower()
                        pkg_version = parts[1]
                        packages_after[pkg_name] = pkg_version
                        # Report fastapi, discord, uvicorn
                        if any(x in pkg_name for x in ['fastapi', 'discord', 'uvicorn']):
                            report.append(f'  {pkg_name}=={pkg_version}')
            report.append(f'Total packages after: {len(packages_after)}')
            report.append(f'Notable packages: fastapi={packages_after.get("fastapi", "NOT FOUND")}, discord={packages_after.get("discord", "NOT FOUND")}, uvicorn={packages_after.get("uvicorn", "NOT FOUND")}')
            # New packages
            new_packages = set(packages_after.keys()) - set(packages_before.keys())
            if new_packages:
                report.append(f'New packages installed: {len(new_packages)}')
                for pkg in sorted(new_packages)[:10]:
                    report.append(f'  + {pkg}=={packages_after[pkg]}')
                if len(new_packages) > 10:
                    report.append(f'  ... and {len(new_packages) - 10} more')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # STEP 6
    report.append('')
    report.append('STEP 6: python -m unittest discover -s tests -p test_*.py -v')
    report.append('Command: python -m unittest discover -s tests -p test_*.py -v')
    test_summary = {'total': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    problem_tests = []
    try:
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', 
                                '-s', 'tests', '-p', 'test_*.py', '-v'],
                               capture_output=True, text=True, shell=False,
                               timeout=120, cwd=str(repo_dir))
        report.append(f'Exit Code: {result.returncode}')
        
        # Parse output
        output = result.stdout + result.stderr
        lines = output.split('\n')
        
        # Count results
        for line in lines:
            if ' ... ok' in line:
                test_summary['total'] += 1
                test_summary['passed'] += 1
            elif ' ... FAIL' in line:
                test_summary['total'] += 1
                test_summary['failed'] += 1
                problem_tests.append(line.split(' ')[0])
            elif ' ... ERROR' in line:
                test_summary['total'] += 1
                test_summary['errors'] += 1
                problem_tests.append(line.split(' ')[0])
            elif ' ... skipped' in line:
                test_summary['total'] += 1
                test_summary['skipped'] += 1
        
        # Extract summary
        for line in lines:
            if line.strip().startswith('Ran') or 'OK' in line or 'FAILED' in line:
                report.append(f'Summary: {line.strip()}')
        
        report.append(f'Parsed Test Results:')
        report.append(f'  Total tests: {test_summary["total"]}')
        report.append(f'  Passed: {test_summary["passed"]}')
        report.append(f'  Failed: {test_summary["failed"]}')
        report.append(f'  Errors: {test_summary["errors"]}')
        report.append(f'  Skipped: {test_summary["skipped"]}')
        
        if problem_tests:
            report.append(f'Problem tests: {list(set(problem_tests))}')
            
    except subprocess.TimeoutExpired:
        report.append('ERROR: Tests timed out (>120s)')
    except Exception as e:
        report.append(f'ERROR: {e}')

    # PHASE 3: GIT STATUS
    report.append('')
    report.append('PHASE 3: GIT STATUS & ARTIFACTS')
    report.append('-' * 60)
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               capture_output=True, text=True, shell=False,
                               cwd=str(repo_dir))
        if result.returncode == 0:
            lines = [l for l in result.stdout.split('\n') if l.strip()]
            tracked = [l for l in lines if l.startswith(('M ', 'D ', 'A '))]
            untracked = [l for l in lines if l.startswith('??')]
            
            report.append(f'Modified/tracked files: {len(tracked)}')
            for line in tracked:
                report.append(f'  {line}')
            report.append(f'Untracked files: {len(untracked)}')
    except Exception as e:
        report.append(f'ERROR git status: {e}')

    # PHASE 4: CLEANUP VERIFICATION
    report.append('')
    report.append('PHASE 4: CLEANUP VERIFICATION')
    report.append('-' * 60)
    remaining = []
    for fname in FILES_TO_REMOVE:
        if (repo_dir / fname).exists():
            remaining.append(fname)
    
    if remaining:
        report.append(f'ERROR: Extra files still exist: {remaining}')
    else:
        report.append('SUCCESS: All extra files removed')
    
    # Verify only workflow_report.txt is modified
    report.append('')
    report.append('Expected final state:')
    report.append('  - workflow_report.txt: MODIFIED (this report)')
    report.append('  - _execute_workflow.py: WILL BE DELETED')
    report.append('  - All other previous scripts: DELETED')
    report.append('')
    report.append('=' * 60)
    report.append('END OF REPORT')
    report.append('=' * 60)

    # Write report
    report_text = '\n'.join(report)
    report_path = repo_dir / 'workflow_report.txt'
    with open(report_path, 'w') as f:
        f.write(report_text)

    print(report_text)
    print(f'\n✓ Report written to {report_path}')
    
    # Clean up this script and temp files
    print('\nCleaning up temporary files...')
    temp_files = [
        '_execute_workflow.py',
        '__temp_workflow_exec__.py',
        'run_temp_workflow.bat',
        'exec_workflow_inline.py',
        'run_workflow_exec.py'
    ]
    for fname in temp_files:
        fpath = repo_dir / fname
        if fpath.exists():
            try:
                os.remove(fpath)
                print(f'  ✓ Removed: {fname}')
            except:
                pass
