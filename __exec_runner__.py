import subprocess
import json
import os

def main():
    os.chdir("d:\\JemmaRepo\\Jemma")
    results = {}
    
    # Cmd 1: Python version
    cmd1_str = 'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe --version"'
    try:
        p = subprocess.run(cmd1_str, capture_output=True, text=True, shell=True)
        results["cmd1"] = {
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "exit_code": p.returncode
        }
    except Exception as e:
        results["cmd1"] = {"stdout": "", "stderr": str(e), "exit_code": -1}
    
    # Cmd 2: Import test
    cmd2_str = 'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe -c \\"import torch, unsloth, datasets, trl; print(\'all ok\')\\"" '
    try:
        p = subprocess.run(cmd2_str, capture_output=True, text=True, shell=True)
        results["cmd2"] = {
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "exit_code": p.returncode
        }
    except Exception as e:
        results["cmd2"] = {"stdout": "", "stderr": str(e), "exit_code": -1}
    
    # Cmd 3: Notebook execution
    cmd3_str = 'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe d:\\JemmaRepo\\Jemma\\toolbox\\run_notebook_cells.py d:\\JemmaRepo\\Jemma\\gemma4-31b-unsloth-local-5090.ipynb 2>&1"'
    try:
        p = subprocess.run(cmd3_str, capture_output=True, text=True, shell=True, timeout=3600)
        results["cmd3"] = {
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "exit_code": p.returncode
        }
    except Exception as e:
        results["cmd3"] = {"stdout": "", "stderr": str(e), "exit_code": -1}
    
    # If cmd3 failed, read the report
    if results["cmd3"]["exit_code"] != 0:
        try:
            with open("d:\\JemmaRepo\\Jemma\\state\\notebook-smoke\\notebook_run_report.json") as f:
                results["cmd3_report"] = json.load(f)
        except:
            pass
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
