#!/usr/bin/env python3
"""Direct notebook execution with full output capture."""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def main():
    py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
    notebook_path = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
    run_script = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
    report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "py_exe": py_exe,
        "commands": []
    }
    
    # Command 1: Python version
    print("="*80)
    print(f"COMMAND 1: {py_exe} --version")
    print("="*80)
    try:
        r = subprocess.run([py_exe, '--version'], capture_output=True, text=True, timeout=30)
        cmd1_output = r.stdout + r.stderr
        print(cmd1_output)
        results["commands"].append({
            "cmd": 1,
            "desc": "Python version",
            "rc": r.returncode,
            "output": cmd1_output[:5000]
        })
    except Exception as e:
        print(f"ERROR: {e}")
        results["commands"].append({
            "cmd": 1,
            "desc": "Python version",
            "error": str(e)
        })
    
    # Command 2: Dependencies
    print("\n" + "="*80)
    print(f"COMMAND 2: {py_exe} -c 'import torch, unsloth, datasets, trl; print(\"all ok\")'")
    print("="*80)
    try:
        r = subprocess.run([py_exe, '-c', 'import torch, unsloth, datasets, trl; print("all ok")'], 
                          capture_output=True, text=True, timeout=60)
        cmd2_output = r.stdout + r.stderr
        print(cmd2_output)
        results["commands"].append({
            "cmd": 2,
            "desc": "Dependencies check",
            "rc": r.returncode,
            "output": cmd2_output[:5000]
        })
    except Exception as e:
        print(f"ERROR: {e}")
        results["commands"].append({
            "cmd": 2,
            "desc": "Dependencies check",
            "error": str(e)
        })
    
    # Command 3: Notebook execution
    print("\n" + "="*80)
    print(f"COMMAND 3: {py_exe} {run_script} {notebook_path}")
    print("(This may take 10-60+ minutes)")
    print("="*80)
    try:
        r = subprocess.run([py_exe, run_script, notebook_path], 
                          capture_output=True, text=True, timeout=3900)
        cmd3_output = r.stdout + r.stderr
        print(cmd3_output[-5000:] if len(cmd3_output) > 5000 else cmd3_output)  # Print last 5000 chars
        results["commands"].append({
            "cmd": 3,
            "desc": "Notebook execution",
            "rc": r.returncode,
            "output_tail": cmd3_output[-2000:] if len(cmd3_output) > 2000 else cmd3_output,
            "output_full_length": len(cmd3_output)
        })
    except subprocess.TimeoutExpired:
        print("TIMEOUT: Notebook execution exceeded 65 minutes")
        results["commands"].append({
            "cmd": 3,
            "desc": "Notebook execution",
            "error": "TIMEOUT"
        })
    except Exception as e:
        print(f"ERROR: {e}")
        results["commands"].append({
            "cmd": 3,
            "desc": "Notebook execution",
            "error": str(e)
        })
    
    # Try to read the report if it exists
    if report_path.exists():
        print("\n" + "="*80)
        print("NOTEBOOK RUN REPORT FOUND:")
        print("="*80)
        report_content = report_path.read_text()
        print(report_content[:3000])
        results["notebook_report"] = json.loads(report_content)
    
    print("\n" + "="*80)
    print("EXECUTION SUMMARY:")
    print("="*80)
    print(f"Total commands: {len(results['commands'])}")
    for cmd in results["commands"]:
        status = f"RC={cmd.get('rc', 'N/A')}" if 'rc' in cmd else cmd.get('error', 'ERROR')
        print(f"  Command {cmd['cmd']}: {cmd['desc']} - {status}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
