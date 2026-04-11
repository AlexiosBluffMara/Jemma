#!/usr/bin/env python3
"""Run the three required commands and report results"""
import subprocess
import sys
import time

def run_command(cmd_str, description):
    """Run a command and report results"""
    print("\n" + "=" * 80)
    print(f"{description}")
    print("=" * 80)
    print(f"COMMAND: cmd /c \"{cmd_str}\"")
    print("-" * 80)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd_str, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=600  # 10 minutes for long-running command
        )
        elapsed = time.time() - start_time
        
        print(f"Return code: {result.returncode}")
        print(f"Elapsed time: {elapsed:.2f} seconds")
        
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")
        
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after 600 seconds")
        return -1, "", "TIMEOUT"
    except Exception as e:
        print(f"ERROR: {e}")
        return -2, "", str(e)

# Command 1: Check Python version
python_exe = r'd:\unsloth\studio\.venv\Scripts\python.exe'
cmd1 = f'{python_exe} --version'
rc1, out1, err1 = run_command(cmd1, "COMMAND 1: Python Version Check")

# Command 2: Check imports
cmd2 = f'{python_exe} -c "import torch, unsloth, datasets, trl; print(\'all ok\')"'
rc2, out2, err2 = run_command(cmd2, "COMMAND 2: Import Check")

# Command 3: Run notebook
cmd3 = f'{python_exe} d:\\JemmaRepo\\Jemma\\toolbox\\run_notebook_cells.py d:\\JemmaRepo\\Jemma\\gemma4-31b-unsloth-local-5090.ipynb'
rc3, out3, err3 = run_command(cmd3, "COMMAND 3: Run Notebook")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Command 1 return code: {rc1}")
print(f"Command 2 return code: {rc2}")
print(f"Command 3 return code: {rc3}")

# If command 3 failed, check the report file
if rc3 != 0:
    print("\n" + "=" * 80)
    print("CHECKING NOTEBOOK RUN REPORT (Command 3 failed)")
    print("=" * 80)
    try:
        import json
        report_path = r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json'
        with open(report_path, 'r') as f:
            report = json.load(f)
        print(json.dumps(report, indent=2))
    except FileNotFoundError:
        print(f"Report file not found at {report_path}")
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from {report_path}")
    except Exception as e:
        print(f"Error reading report: {e}")

sys.exit(0)
