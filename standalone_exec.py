#!/usr/bin/env python3
import subprocess
import json
import sys
import os

# This script runs independently using only standard Python
def run_commands():
    results = {
        "routes_attempted": ["standalone_python_subprocess"],
        "commands": {},
        "prior_known_failed_routes": [
            "powershell-tool failed before execution because pwsh missing",
            "pylance-run-code-snippet/python-subprocess timed out"
        ]
    }
    
    # Command 1
    print("Running command 1...")
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=10)
        results["commands"]["1_python_version"] = {
            "exit_code": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }
        print("Command 1 complete")
    except Exception as e:
        results["commands"]["1_python_version"] = {"error": str(e)}
        print(f"Command 1 error: {e}")
    
    # Command 2
    print("Running command 2...")
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 'import torch, unsloth, datasets, trl; print("all ok")'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=60)
        results["commands"]["2_import_check"] = {
            "exit_code": proc.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }
        print("Command 2 complete")
    except subprocess.TimeoutExpired:
        proc.kill()
        results["commands"]["2_import_check"] = {"error": "timeout"}
        print("Command 2 timeout")
    except Exception as e:
        results["commands"]["2_import_check"] = {"error": str(e)}
        print(f"Command 2 error: {e}")
    
    # Command 3
    print("Running command 3 (this may take several minutes)...")
    try:
        proc = subprocess.Popen(
            [r'd:\unsloth\studio\.venv\Scripts\python.exe', r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py', r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=r'd:\JemmaRepo\Jemma'
        )
        stdout, _ = proc.communicate(timeout=900)
        results["commands"]["3_notebook_execution"] = {
            "exit_code": proc.returncode,
            "stdout_length": len(stdout),
            "stdout_preview": stdout[:2000] if len(stdout) > 2000 else stdout,
            "stderr": None
        }
        print(f"Command 3 complete, exit code: {proc.returncode}")
        
        # Check for report if failed
        if proc.returncode != 0:
            report_path = r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json'
            if os.path.exists(report_path):
                try:
                    with open(report_path) as f:
                        report = json.load(f)
                    results["notebook_run_report"] = report
                    print("Found notebook_run_report.json")
                except Exception as e:
                    results["notebook_run_report_error"] = str(e)
    except subprocess.TimeoutExpired:
        proc.kill()
        results["commands"]["3_notebook_execution"] = {"error": "timeout_after_900s"}
        print("Command 3 timeout")
    except Exception as e:
        results["commands"]["3_notebook_execution"] = {"error": str(e)}
        print(f"Command 3 error: {e}")
    
    return results

if __name__ == "__main__":
    results = run_commands()
    print("\n" + "="*80)
    print(json.dumps(results, indent=2))
