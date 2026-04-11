#!/usr/bin/env python3
"""Execute three commands and report results."""
import subprocess
import sys
import json
from pathlib import Path

def run_command(cmd, description, timeout_sec=60):
    """Run a command and capture output."""
    print(f"\n{'='*70}")
    print(f"COMMAND: {description}")
    print(f"{'='*70}")
    print(f"Executing: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"Return code: {result.returncode}")
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Command exceeded {timeout_sec}s limit")
        return -1, "", "TIMEOUT"
    except Exception as e:
        print(f"ERROR: {e}")
        return -2, "", str(e)

def main():
    py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
    notebook_path = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
    run_script = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
    
    results = {}
    
    # Command 1: Check Python version
    print("\n" + "="*70)
    print("PHASE 1: CHECKING PYTHON VERSION")
    print("="*70)
    rc1, out1, err1 = run_command([py_exe, '--version'], "Check Python version")
    results['cmd1'] = {'rc': rc1, 'stdout': out1, 'stderr': err1}
    
    # Command 2: Check dependencies
    print("\n" + "="*70)
    print("PHASE 2: CHECKING DEPENDENCIES")
    print("="*70)
    code = "import torch, unsloth, datasets, trl; print('all ok')"
    rc2, out2, err2 = run_command([py_exe, '-c', code], "Check dependencies (torch, unsloth, datasets, trl)", timeout_sec=120)
    results['cmd2'] = {'rc': rc2, 'stdout': out2, 'stderr': err2}
    
    # Command 3: Run notebook
    print("\n" + "="*70)
    print("PHASE 3: RUNNING NOTEBOOK (may take 10-60+ minutes)")
    print("="*70)
    rc3, out3, err3 = run_command([py_exe, run_script, notebook_path], "Execute notebook cells", timeout_sec=600)
    results['cmd3'] = {'rc': rc3, 'stdout': out3, 'stderr': err3}
    
    # Save results
    results_file = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\execution_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(results, indent=2))
    
    print("\n" + "="*70)
    print("EXECUTION COMPLETE")
    print("="*70)
    print(f"Results saved to: {results_file}")
    
    # Check for failures
    if rc1 != 0:
        print(f"\n⚠️  Command 1 failed with rc={rc1}")
    if rc2 != 0:
        print(f"\n⚠️  Command 2 failed with rc={rc2}")
    if rc3 != 0:
        print(f"\n⚠️  Command 3 failed with rc={rc3}")
        # Try to read the report
        report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
        if report_path.exists():
            print(f"\n📋 Notebook run report found:")
            report = json.loads(report_path.read_text())
            print(json.dumps(report, indent=2))
    
    return max(rc1, rc2, rc3)

if __name__ == "__main__":
    sys.exit(main())
