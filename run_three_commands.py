#!/usr/bin/env python
import subprocess
import json
import os
import sys

def run_commands():
    results = {}
    
    # Command 1
    print("=" * 80)
    print("COMMAND 1: Check Python version")
    print("=" * 80)
    cmd1 = r'd:\unsloth\studio\.venv\Scripts\python.exe --version'
    try:
        result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Command: {cmd1}")
        print(f"Return code: {result1.returncode}")
        print(f"Stdout: {result1.stdout}")
        print(f"Stderr: {result1.stderr}")
        results['cmd1'] = {
            'command': cmd1,
            'returncode': result1.returncode,
            'stdout': result1.stdout,
            'stderr': result1.stderr
        }
    except Exception as e:
        print(f"Error: {e}")
        results['cmd1'] = {'error': str(e)}
    
    # Command 2
    print("\n" + "=" * 80)
    print("COMMAND 2: Check imports")
    print("=" * 80)
    cmd2 = r'd:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print(\'all ok\')"'
    try:
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True, timeout=60)
        print(f"Command: {cmd2}")
        print(f"Return code: {result2.returncode}")
        print(f"Stdout: {result2.stdout}")
        print(f"Stderr: {result2.stderr}")
        results['cmd2'] = {
            'command': cmd2,
            'returncode': result2.returncode,
            'stdout': result2.stdout,
            'stderr': result2.stderr
        }
    except Exception as e:
        print(f"Error: {e}")
        results['cmd2'] = {'error': str(e)}
    
    # Command 3
    print("\n" + "=" * 80)
    print("COMMAND 3: Run notebook cells (long-running...)")
    print("=" * 80)
    cmd3 = r'd:\unsloth\studio\.venv\Scripts\python.exe d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'
    try:
        result3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True, timeout=3600)
        print(f"Command: {cmd3}")
        print(f"Return code: {result3.returncode}")
        print(f"Stdout length: {len(result3.stdout)} chars")
        print(f"Stdout (first 3000 chars):\n{result3.stdout[:3000]}")
        if len(result3.stdout) > 3000:
            print(f"\n... (truncated, total {len(result3.stdout)} chars) ...\n")
            print(f"Stdout (last 1000 chars):\n{result3.stdout[-1000:]}")
        print(f"Stderr length: {len(result3.stderr)} chars")
        print(f"Stderr (first 3000 chars):\n{result3.stderr[:3000]}")
        if len(result3.stderr) > 3000:
            print(f"\n... (truncated, total {len(result3.stderr)} chars) ...\n")
            print(f"Stderr (last 1000 chars):\n{result3.stderr[-1000:]}")
        results['cmd3'] = {
            'command': cmd3,
            'returncode': result3.returncode,
            'stdout_length': len(result3.stdout),
            'stdout_first_3000': result3.stdout[:3000],
            'stdout_last_1000': result3.stdout[-1000:] if len(result3.stdout) > 3000 else '',
            'stderr_length': len(result3.stderr),
            'stderr_first_3000': result3.stderr[:3000],
            'stderr_last_1000': result3.stderr[-1000:] if len(result3.stderr) > 3000 else ''
        }
    except subprocess.TimeoutExpired:
        print(f"Command timed out after 3600 seconds")
        results['cmd3'] = {'error': 'Timeout after 3600 seconds'}
    except Exception as e:
        print(f"Error: {e}")
        results['cmd3'] = {'error': str(e)}
    
    # If command 3 failed, check report
    if 'cmd3' in results and results['cmd3'].get('returncode', -1) != 0:
        print("\n" + "=" * 80)
        print("COMMAND 3 FAILED - Checking report file")
        print("=" * 80)
        report_path = r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json'
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    report = json.load(f)
                print(f"Report found at {report_path}:")
                print(json.dumps(report, indent=2)[:2000])
                results['report'] = report
            except Exception as e:
                print(f"Error reading report: {e}")
                results['report_error'] = str(e)
        else:
            print(f"Report file not found at {report_path}")
    
    return results

if __name__ == '__main__':
    results = run_commands()
