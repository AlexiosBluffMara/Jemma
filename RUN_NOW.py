import subprocess
import json
from pathlib import Path

# Execution report
output_file = Path(r'd:\JemmaRepo\Jemma\EXECUTION_OUTPUT.txt')

with open(output_file, 'w') as f:
    f.write("EXECUTION REPORT\n")
    f.write("=" * 80 + "\n\n")
    
    # Command 1
    f.write("COMMAND 1: Python Version\n")
    f.write("-" * 80 + "\n")
    try:
        r = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe', '--version'], 
                          capture_output=True, text=True, timeout=30)
        f.write(f"Return Code: {r.returncode}\n")
        f.write(f"STDOUT: {r.stdout}\n")
        f.write(f"STDERR: {r.stderr}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
    f.write("\n\n")
    
    # Command 2
    f.write("COMMAND 2: Import Check\n")
    f.write("-" * 80 + "\n")
    try:
        r = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe', '-c', 
                           'import torch, unsloth, datasets, trl; print("all ok")'],
                          capture_output=True, text=True, timeout=120)
        f.write(f"Return Code: {r.returncode}\n")
        f.write(f"STDOUT: {r.stdout}\n")
        f.write(f"STDERR: {r.stderr}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
    f.write("\n\n")
    
    # Command 3
    f.write("COMMAND 3: Notebook Execution\n")
    f.write("-" * 80 + "\n")
    try:
        r = subprocess.run([r'd:\unsloth\studio\.venv\Scripts\python.exe',
                           r'd:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py',
                           r'd:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb'],
                          capture_output=True, text=True, timeout=3600)
        f.write(f"Return Code: {r.returncode}\n")
        f.write(f"STDOUT:\n{r.stdout}\n")
        f.write(f"STDERR:\n{r.stderr}\n")
        cmd3_rc = r.returncode
    except Exception as e:
        f.write(f"Error: {e}\n")
        cmd3_rc = -1
    f.write("\n\n")
    
    # Check report if command 3 failed
    if cmd3_rc != 0:
        f.write("NOTEBOOK RUN REPORT (Command 3 failed)\n")
        f.write("-" * 80 + "\n")
        report_path = Path(r'd:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json')
        if report_path.exists():
            try:
                report_data = json.loads(report_path.read_text())
                f.write(json.dumps(report_data, indent=2))
            except:
                f.write(report_path.read_text())
        else:
            f.write("Report file not found\n")

print(f"Report written to {output_file}")
