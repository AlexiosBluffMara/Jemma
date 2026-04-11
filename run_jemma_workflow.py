#!/usr/bin/env python3
"""
Jemma Workflow Executor - Runs complete workflow with reporting
Usage: python run_jemma_workflow.py
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def run_step(step_num, step_name, command, timeout=300):
    """Execute a single step and return results"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {step_name}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(command)}")
    print(f"Timeout: {timeout}s")
    print()
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        print(f"Exit Code: {result.returncode}")
        
        # Show first part of output
        if result.stdout:
            lines = result.stdout.split('\n')
            display_lines = lines[:15]
            print("\nOutput (first 15 lines):")
            for line in display_lines:
                print(f"  {line}")
            if len(lines) > 15:
                print(f"  ... ({len(lines) - 15} more lines)")
        
        if result.stderr:
            print(f"\nErrors/Warnings (first 10 lines):")
            err_lines = result.stderr.split('\n')[:10]
            for line in err_lines:
                print(f"  {line}")
        
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'command': command,
            'step_num': step_num,
            'step_name': step_name
        }
    
    except subprocess.TimeoutExpired as e:
        print(f"ERROR: Command timed out after {timeout} seconds")
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': f'TIMEOUT after {timeout}s',
            'command': command,
            'step_num': step_num,
            'step_name': step_name
        }
    
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e),
            'command': command,
            'step_num': step_num,
            'step_name': step_name
        }

def main():
    # Setup
    repo_path = r"D:\JemmaRepo\Jemma"
    report_path = os.path.join(repo_path, "workflow_report.txt")
    
    os.chdir(repo_path)
    
    print("\n" + "="*80)
    print("JEMMA WORKFLOW EXECUTOR")
    print("="*80)
    print(f"Repository: {repo_path}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Report: {report_path}")
    
    # Define workflow steps
    steps = [
        (1, "Python Version", ["python", "--version"], 30),
        (2, "Interpreter Info", ["python", "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"], 30),
        (3, "Pip List (Before Install)", ["python", "-m", "pip", "list"], 60),
        (4, "Install Jemma Dependencies", ["python", "-m", "pip", "install", "-e", "."], 600),
        (5, "Pip List (After Install)", ["python", "-m", "pip", "list"], 60),
        (6, "Run Unit Tests", ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], 600),
    ]
    
    # Execute all steps
    results = []
    for step_num, step_name, command, timeout in steps:
        result = run_step(step_num, step_name, command, timeout)
        results.append(result)
        
        # If a critical step fails, optionally stop
        if step_num in [1, 2] and not result['success']:
            print("\n⚠ Critical step failed. Continuing anyway...")
    
    # Generate report
    print("\n" + "="*80)
    print("GENERATING REPORT")
    print("="*80)
    
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("JEMMA WORKFLOW EXECUTION REPORT")
    report_lines.append("="*80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Repository: {repo_path}")
    report_lines.append("")
    
    # Detailed results
    for result in results:
        report_lines.append(f"\n{'-'*80}")
        report_lines.append(f"STEP {result['step_num']}: {result['step_name']}")
        report_lines.append(f"{'-'*80}")
        report_lines.append(f"Command: {' '.join(result['command'])}")
        report_lines.append(f"Exit Code: {result['exit_code']}")
        report_lines.append(f"Success: {result['success']}")
        report_lines.append("")
        
        if result['stdout']:
            report_lines.append("STDOUT:")
            report_lines.append(result['stdout'])
            report_lines.append("")
        
        if result['stderr']:
            report_lines.append("STDERR:")
            report_lines.append(result['stderr'])
            report_lines.append("")
    
    # Summary
    report_lines.append(f"\n{'='*80}")
    report_lines.append("EXECUTION SUMMARY")
    report_lines.append(f"{'='*80}")
    report_lines.append("")
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    report_lines.append(f"Total Steps: {total}")
    report_lines.append(f"Successful: {successful}")
    report_lines.append(f"Failed: {total - successful}")
    report_lines.append("")
    
    report_lines.append("Step Results:")
    for result in results:
        status = "✓ PASS" if result['success'] else "✗ FAIL"
        report_lines.append(f"  {status} - Step {result['step_num']}: {result['step_name']} (exit={result['exit_code']})")
    
    report_lines.append("")
    report_lines.append("="*80)
    report_lines.append(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("="*80)
    
    # Write report
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✓ Report written: {report_path}")
    
    # Summary to console
    print(f"\n{'='*80}")
    print("WORKFLOW COMPLETE")
    print(f"{'='*80}")
    print(f"Total Steps: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"\nDetailed report: {report_path}")
    
    return 0 if successful == total else 1

if __name__ == "__main__":
    sys.exit(main())
