#!/usr/bin/env python
"""
Jemma 6-Step Workflow Executor
Executes workflow steps and generates comprehensive report
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import re

def main():
    work_dir = r'D:\JemmaRepo\Jemma'
    os.chdir(work_dir)
    
    # Initialize results tracking
    results = {
        'steps': [],
        'python_info': {},
        'packages_pre': [],
        'packages_post': [],
        'test_summary': {},
        'artifacts': [],
        'git_status': '',
    }
    
    def run_step(step_num, cmd_list, description=""):
        """Run a single step and capture output"""
        print(f'\n{"="*70}')
        print(f'STEP {step_num}: {description}')
        print(f'Command: {" ".join(str(c) for c in cmd_list)}')
        print(f'{"="*70}')
        
        try:
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                cwd=work_dir
            )
            
            print(f'Exit Code: {result.returncode}')
            
            if result.stdout:
                print(f'\nSTDOUT:\n{result.stdout}')
            if result.stderr:
                print(f'\nSTDERR:\n{result.stderr}')
                
            return {
                'step': step_num,
                'description': description,
                'command': ' '.join(str(c) for c in cmd_list),
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            print(f'Exception: {e}')
            return {
                'step': step_num,
                'description': description,
                'command': ' '.join(str(c) for c in cmd_list),
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    # Execute all 6 steps
    print(f'\nStarting Jemma Workflow Execution at {datetime.now()}')
    print(f'Working Directory: {work_dir}')
    
    # Step 1: python --version
    results['steps'].append(run_step(
        1,
        [sys.executable, '--version'],
        'Check Python version'
    ))
    
    # Step 2: python -c with sys info
    results['steps'].append(run_step(
        2,
        [sys.executable, '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
        'Python interpreter info'
    ))
    
    # Capture Python info
    results['python_info']['executable'] = sys.executable
    results['python_info']['version'] = sys.version
    results['python_info']['version_info'] = str(sys.version_info)
    
    # Step 3: pip list (before install)
    print('\nCapturing pre-install package list...')
    results['steps'].append(run_step(
        3,
        [sys.executable, '-m', 'pip', 'list'],
        'List installed packages (pre-install)'
    ))
    
    # Extract relevant packages
    step3_result = results['steps'][-1]
    if step3_result['exit_code'] == 0:
        for line in step3_result['stdout'].split('\n'):
            line = line.strip()
            if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
                if line and not line.startswith('-'):
                    results['packages_pre'].append(line)
    
    # Step 4: pip install -e .
    results['steps'].append(run_step(
        4,
        [sys.executable, '-m', 'pip', 'install', '-e', '.'],
        'Install package in editable mode'
    ))
    
    # Step 5: pip list (after install)
    print('\nCapturing post-install package list...')
    results['steps'].append(run_step(
        5,
        [sys.executable, '-m', 'pip', 'list'],
        'List installed packages (post-install)'
    ))
    
    # Extract relevant packages
    step5_result = results['steps'][-1]
    if step5_result['exit_code'] == 0:
        for line in step5_result['stdout'].split('\n'):
            line = line.strip()
            if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
                if line and not line.startswith('-'):
                    results['packages_post'].append(line)
    
    # Step 6: unittest discover
    results['steps'].append(run_step(
        6,
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
        'Run unit tests'
    ))
    
    # Parse test summary
    step6_result = results['steps'][-1]
    test_output = step6_result['stdout'] + step6_result['stderr']
    
    # Look for test summary line (Ran X tests...)
    for line in test_output.split('\n'):
        if 'Ran' in line:
            results['test_summary']['test_count_line'] = line.strip()
        if 'FAILED' in line or 'OK' in line:
            results['test_summary']['status_line'] = line.strip()
    
    # Check for created artifacts
    print('\nScanning for artifacts...')
    artifact_types = ['.egg-info', 'build', 'dist', '.pytest_cache']
    for artifact_type in artifact_types:
        if artifact_type == '.egg-info':
            matches = list(Path(work_dir).glob('*.egg-info'))
            if matches:
                results['artifacts'].append(f'{artifact_type}: {len(matches)} directories')
        elif artifact_type == '__pycache__':
            matches = list(Path(work_dir).rglob('__pycache__'))
            if matches:
                results['artifacts'].append(f'{artifact_type}: {len(matches)} directories')
        else:
            artifact_path = Path(work_dir) / artifact_type
            if artifact_path.exists():
                results['artifacts'].append(f'{artifact_type}: exists')
    
    # Get git status
    print('\nGetting git status...')
    try:
        git_result = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            cwd=work_dir
        )
        results['git_status'] = git_result.stdout
    except Exception as e:
        results['git_status'] = f'Git status failed: {e}'
    
    # Generate comprehensive report
    report = generate_report(results, work_dir)
    
    # Write report to file
    report_path = Path(work_dir) / 'workflow_report.txt'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f'\n{"="*70}')
    print(f'WORKFLOW REPORT GENERATED')
    print(f'{"="*70}')
    print(report)
    print(f'\nReport written to: {report_path}')
    print(f'Report file exists: {report_path.exists()}')
    print(f'Completed at: {datetime.now()}')

def generate_report(results, work_dir):
    """Generate comprehensive workflow report"""
    report = []
    report.append('='*70)
    report.append('JEMMA WORKFLOW EXECUTION REPORT')
    report.append('='*70)
    report.append(f'\nGenerated: {datetime.now().isoformat()}')
    report.append(f'Working Directory: {work_dir}')
    report.append('')
    
    # Exit codes
    report.append('EXIT CODES FOR ALL 6 STEPS:')
    report.append('-'*70)
    for step in results['steps']:
        report.append(f'  Step {step["step"]}: {step["exit_code"]}')
    report.append('')
    
    # Python interpreter info
    report.append('PYTHON INTERPRETER INFO:')
    report.append('-'*70)
    report.append(f'  Executable: {results["python_info"]["executable"]}')
    report.append(f'  Version: {results["python_info"]["version_info"]}')
    report.append('')
    
    # Pre-install packages
    report.append('PRE-INSTALL PACKAGES (fastapi/discord/uvicorn):')
    report.append('-'*70)
    if results['packages_pre']:
        for pkg in results['packages_pre']:
            report.append(f'  {pkg}')
    else:
        report.append('  None found')
    report.append('')
    
    # Post-install packages
    report.append('POST-INSTALL PACKAGES (fastapi/discord/uvicorn):')
    report.append('-'*70)
    if results['packages_post']:
        for pkg in results['packages_post']:
            report.append(f'  {pkg}')
    else:
        report.append('  None found')
    report.append('')
    
    # Test summary
    report.append('TEST SUMMARY:')
    report.append('-'*70)
    if results['test_summary']:
        if 'test_count_line' in results['test_summary']:
            report.append(f'  {results["test_summary"]["test_count_line"]}')
        if 'status_line' in results['test_summary']:
            report.append(f'  {results["test_summary"]["status_line"]}')
    else:
        report.append('  No test summary available')
    report.append('')
    
    # Artifacts created
    report.append('ARTIFACTS CREATED (.egg-info, build, dist, __pycache__, .pytest_cache):')
    report.append('-'*70)
    if results['artifacts']:
        for artifact in results['artifacts']:
            report.append(f'  {artifact}')
    else:
        report.append('  None found')
    report.append('')
    
    # Git status
    report.append('FINAL GIT STATUS (showing workflow_report.txt):')
    report.append('-'*70)
    if results['git_status']:
        has_workflow_report = False
        for line in results['git_status'].split('\n'):
            if 'workflow_report.txt' in line:
                report.append(f'  {line}')
                has_workflow_report = True
        if not has_workflow_report:
            report.append('  workflow_report.txt (new/untracked)')
    else:
        report.append('  Unable to retrieve git status')
    report.append('')
    
    # Command execution method
    report.append('COMMAND EXECUTION METHOD:')
    report.append('-'*70)
    report.append('  Form: python -c "..." with subprocess.run()')
    report.append('  Note: pwsh unavailable (using direct python instead)')
    report.append('')
    
    # Detailed step results
    report.append('='*70)
    report.append('DETAILED STEP RESULTS')
    report.append('='*70)
    for step in results['steps']:
        report.append(f'\nSTEP {step["step"]}: {step["description"]}')
        report.append('-'*70)
        report.append(f'Command: {step["command"]}')
        report.append(f'Exit Code: {step["exit_code"]}')
        if step["stdout"]:
            report.append(f'\nOutput (stdout):\n{step["stdout"][:1000]}')
            if len(step["stdout"]) > 1000:
                report.append('[... truncated ...]')
        if step["stderr"]:
            report.append(f'\nErrors (stderr):\n{step["stderr"][:1000]}')
            if len(step["stderr"]) > 1000:
                report.append('[... truncated ...]')
    
    report.append('\n' + '='*70)
    report.append('END OF REPORT')
    report.append('='*70)
    
    return '\n'.join(report)

if __name__ == '__main__':
    main()
