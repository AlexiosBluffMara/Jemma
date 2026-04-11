#!/usr/bin/env python3
"""
Direct workflow execution script - runs all 5 steps and generates report
"""
import subprocess
import sys
import os
import re
from pathlib import Path

def main():
    repo_cwd = Path(r'D:\JemmaRepo\Jemma')
    report_path = repo_cwd / 'workflow_report.txt'
    
    # Storage for results
    results = []
    step_data = {}
    
    # Helper to run subprocess commands
    def run_command(cmd_list, step_num, step_name):
        try:
            result = subprocess.run(
                cmd_list,
                cwd=str(repo_cwd),
                capture_output=True,
                text=True,
                shell=False,
                timeout=600  # 10 minutes per command
            )
            return {
                'step': step_num,
                'name': step_name,
                'command': ' '.join(cmd_list),
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'step': step_num,
                'name': step_name,
                'command': ' '.join(cmd_list),
                'stdout': '',
                'stderr': 'Command timed out after 600 seconds',
                'returncode': -1
            }
        except Exception as e:
            return {
                'step': step_num,
                'name': step_name,
                'command': ' '.join(cmd_list),
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    print("=" * 80)
    print("WORKFLOW EXECUTION - 5 STEP PROCESS")
    print("=" * 80)
    print()
    
    # Step 1: python --version
    print("[1/7] Running: python --version")
    step1 = run_command(['python', '--version'], 1, 'python --version')
    results.append(step1)
    step_data['step1'] = step1
    print(f"  ✓ Exit code: {step1['returncode']}")
    
    # Step 2: python -c (get interpreter info)
    print("[2/7] Running: python -c (interpreter info)")
    step2 = run_command(
        ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
        2,
        'Python interpreter info'
    )
    results.append(step2)
    step_data['step2'] = step2
    print(f"  ✓ Exit code: {step2['returncode']}")
    
    # Step 3a: pip list (before install)
    print("[3/7] Running: python -m pip list (before install)")
    step3a = run_command(['python', '-m', 'pip', 'list'], 3, 'pip list (before install)')
    results.append(step3a)
    step_data['step3a'] = step3a
    
    # Filter for relevant packages
    filtered_3a = []
    if step3a['stdout']:
        for line in step3a['stdout'].split('\n'):
            if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
                filtered_3a.append(line)
    step_data['step3a_filtered'] = filtered_3a
    print(f"  ✓ Exit code: {step3a['returncode']}, matching packages: {len(filtered_3a)}")
    
    # Step 4: pip install -e .
    print("[4/7] Running: python -m pip install -e . (THIS MAY TAKE A WHILE)")
    step4 = run_command(['python', '-m', 'pip', 'install', '-e', '.'], 4, 'pip install -e .')
    results.append(step4)
    step_data['step4'] = step4
    print(f"  ✓ Exit code: {step4['returncode']}")
    
    # Step 4 supplemental: pip list (after install)
    print("[5/7] Running: python -m pip list (after install - supplemental)")
    step4_supp = run_command(['python', '-m', 'pip', 'list'], 4, 'pip list (supplemental after install)')
    results.append(step4_supp)
    step_data['step4_supp'] = step4_supp
    
    # Filter for relevant packages
    filtered_4_supp = []
    if step4_supp['stdout']:
        for line in step4_supp['stdout'].split('\n'):
            if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
                filtered_4_supp.append(line)
    step_data['step4_supp_filtered'] = filtered_4_supp
    print(f"  ✓ Exit code: {step4_supp['returncode']}, matching packages: {len(filtered_4_supp)}")
    
    # Step 5: unittest discover
    print("[6/7] Running: python -m unittest discover -s tests -p test_*.py -v")
    step5 = run_command(
        ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
        5,
        'unittest discover'
    )
    results.append(step5)
    step_data['step5'] = step5
    print(f"  ✓ Exit code: {step5['returncode']}")
    
    # Parse test results
    test_lines = step5['stdout'].split('\n') + step5['stderr'].split('\n')
    test_summary = {
        'total': 0,
        'passes': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'failed_test_files': set()
    }
    
    for line in test_lines:
        line_lower = line.lower()
        if 'ran' in line_lower and 'test' in line_lower:
            match = re.search(r'ran\s+(\d+)', line_lower)
            if match:
                test_summary['total'] = int(match.group(1))
        if 'FAILED' in line or 'ERROR' in line:
            if '(' in line and ')' in line:
                test_name = line.split('(')[1].split(')')[0] if '(' in line else ''
                if test_name:
                    test_summary['failed_test_files'].add(test_name)
    
    # Count ok/fail in output
    for line in test_lines:
        if line.strip().startswith('ok') or ' ok' in line:
            test_summary['passes'] += 1
        elif 'FAIL' in line:
            test_summary['failures'] += 1
        elif 'ERROR' in line:
            test_summary['errors'] += 1
        elif 'skipped' in line.lower():
            test_summary['skipped'] += 1
    
    print("[7/7] Generating report...")
    
    # Generate report
    report_lines = []
    report_lines.append('=' * 80)
    report_lines.append('WORKFLOW EXECUTION REPORT')
    report_lines.append('=' * 80)
    report_lines.append('')
    
    # Report each step
    for step_result in results:
        report_lines.append(f"STEP {step_result['step']}: {step_result['name']}")
        report_lines.append('-' * 80)
        report_lines.append(f"Command: {step_result['command']}")
        report_lines.append(f"Exit Code: {step_result['returncode']}")
        report_lines.append('')
        report_lines.append('STDOUT:')
        report_lines.append(step_result['stdout'] if step_result['stdout'] else '(empty)')
        report_lines.append('')
        report_lines.append('STDERR:')
        report_lines.append(step_result['stderr'] if step_result['stderr'] else '(empty)')
        report_lines.append('')
        report_lines.append('')
    
    # Summary section
    report_lines.append('=' * 80)
    report_lines.append('SUMMARY')
    report_lines.append('=' * 80)
    report_lines.append('')
    
    report_lines.append('Active Interpreter (from Step 2):')
    report_lines.append(step2['stdout'])
    report_lines.append('')
    
    report_lines.append('Filtered Package Snapshots (fastapi, discord, uvicorn):')
    report_lines.append('')
    report_lines.append('BEFORE INSTALL (Step 3):')
    if step_data['step3a_filtered']:
        for line in step_data['step3a_filtered']:
            report_lines.append(line)
    else:
        report_lines.append('(no matching packages found)')
    report_lines.append('')
    
    report_lines.append('AFTER INSTALL - SUPPLEMENTAL (Step 4 Supplemental):')
    if step_data['step4_supp_filtered']:
        for line in step_data['step4_supp_filtered']:
            report_lines.append(line)
    else:
        report_lines.append('(no matching packages found)')
    report_lines.append('')
    
    report_lines.append('Step Exit Codes:')
    for i in range(1, 6):
        if i == 4:
            continue
        key = f'step{i}'
        if key in step_data:
            report_lines.append(f"  Step {i}: {step_data[key]['returncode']}")
    report_lines.append(f"  Step 4 (supplemental): {step_data['step4_supp']['returncode']}")
    report_lines.append('')
    
    report_lines.append('Test Summary (Step 5):')
    report_lines.append(f"  Total Tests: {test_summary['total']}")
    report_lines.append(f"  Passes: {test_summary['passes']}")
    report_lines.append(f"  Failures: {test_summary['failures']}")
    report_lines.append(f"  Errors: {test_summary['errors']}")
    report_lines.append(f"  Skipped: {test_summary['skipped']}")
    report_lines.append('')
    
    if test_summary['failed_test_files']:
        report_lines.append('Test Files with Failures/Errors:')
        for test_file in sorted(test_summary['failed_test_files']):
            report_lines.append(f"  {test_file}")
    else:
        report_lines.append('Test Files with Failures/Errors: (none)')
    report_lines.append('')
    
    # Write report
    report_content = '\n'.join(report_lines)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f'  ✓ Report written to: {report_path}')
    print(f'  ✓ Report size: {len(report_content)} bytes')
    print()
    print("=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
