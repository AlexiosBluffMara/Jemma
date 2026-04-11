#!/usr/bin/env python3
"""
Execute the three required commands and capture output.
This script runs independently and captures all output.
"""
import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import traceback

def log(msg):
    """Print and flush immediately."""
    print(msg, flush=True)

def run_cmd(cmd_list, description, timeout=60):
    """Execute command and return result."""
    log(f"\n{'='*80}")
    log(f"EXECUTING: {description}")
    log(f"{'='*80}")
    log(f"Command: {' '.join(cmd_list)}\n")
    
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=r"d:\JemmaRepo\Jemma"
        )
        
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        
        log(output)
        log(f"\nReturn Code: {result.returncode}\n")
        
        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "output": output[:10000],  # First 10000 chars
            "output_len": len(output)
        }
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: Command exceeded {timeout} seconds\n")
        return {
            "success": False,
            "error": f"TIMEOUT after {timeout} seconds"
        }
    except Exception as e:
        log(f"EXCEPTION: {e}\n{traceback.format_exc()}\n")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

def main():
    log(f"{"="*80}")
    log(f"NOTEBOOK EXECUTION RUNNER")
    log(f"{"="*80}")
    log(f"Start Time: {datetime.now().isoformat()}\n")
    
    py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
    notebook = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
    runner = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
    
    results = {
        "start_time": datetime.now().isoformat(),
        "python_exe": py_exe,
        "notebook": notebook,
        "commands": {}
    }
    
    # COMMAND 1: Python Version
    log("PHASE 1: Python Version Check")
    results["commands"]["cmd1"] = run_cmd(
        [py_exe, "--version"],
        "Check Python Version",
        timeout=30
    )
    
    # COMMAND 2: Dependency Check
    log("PHASE 2: Dependency Check")
    results["commands"]["cmd2"] = run_cmd(
        [py_exe, "-c", "import torch, unsloth, datasets, trl; print('all ok')"],
        "Check torch, unsloth, datasets, trl imports",
        timeout=60
    )
    
    # COMMAND 3: Notebook Execution
    log("PHASE 3: Notebook Execution")
    log("WARNING: This may take 10-60+ minutes. Please be patient...\n")
    results["commands"]["cmd3"] = run_cmd(
        [py_exe, runner, notebook],
        "Execute Notebook Cells",
        timeout=4000  # Up to ~67 minutes
    )
    
    # Check for notebook run report
    report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
    if report_path.exists():
        log(f"\n{'='*80}")
        log("NOTEBOOK RUN REPORT FOUND")
        log(f"{'='*80}\n")
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)
            log(json.dumps(report, indent=2))
            results["notebook_report"] = report
        except Exception as e:
            log(f"Could not parse report: {e}")
    
    # Summary
    log(f"\n{'='*80}")
    log("EXECUTION SUMMARY")
    log(f"{'='*80}")
    for cmd_name, cmd_result in results["commands"].items():
        if "success" in cmd_result:
            status = "✓ PASSED" if cmd_result["success"] else "✗ FAILED"
            log(f"{cmd_name}: {status} (RC={cmd_result.get('return_code', 'N/A')})")
        else:
            log(f"{cmd_name}: ERROR - {cmd_result.get('error', 'Unknown')}")
    
    log(f"End Time: {datetime.now().isoformat()}\n")
    
    # Save results to JSON
    results["end_time"] = datetime.now().isoformat()
    results_file = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\execution_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(results, indent=2))
    log(f"Results saved to: {results_file}\n")
    
    return 0 if all(r.get("success", False) for r in results["commands"].values() if "success" in r) else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        print(traceback.format_exc())
        sys.exit(2)
