import subprocess
import json
import os
import sys

os.chdir("d:\\JemmaRepo\\Jemma")

results = {}

# Command 1
try:
    p1 = subprocess.Popen(
        'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe --version"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        cwd="d:\\JemmaRepo\\Jemma"
    )
    stdout1, stderr1 = p1.communicate()
    exit1 = p1.returncode
except Exception as e:
    stdout1, stderr1, exit1 = "", str(e), -1

results["cmd1"] = {
    "stdout": stdout1.strip(),
    "stderr": stderr1.strip(),
    "exit_code": exit1
}

# Command 2
try:
    p2 = subprocess.Popen(
        'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe -c \\"import torch, unsloth, datasets, trl; print(\'all ok\')\\"" ',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        cwd="d:\\JemmaRepo\\Jemma"
    )
    stdout2, stderr2 = p2.communicate()
    exit2 = p2.returncode
except Exception as e:
    stdout2, stderr2, exit2 = "", str(e), -1

results["cmd2"] = {
    "stdout": stdout2.strip(),
    "stderr": stderr2.strip(),
    "exit_code": exit2
}

# Command 3 - wait for it to complete
try:
    p3 = subprocess.Popen(
        'cmd /c "d:\\unsloth\\studio\\.venv\\Scripts\\python.exe d:\\JemmaRepo\\Jemma\\toolbox\\run_notebook_cells.py d:\\JemmaRepo\\Jemma\\gemma4-31b-unsloth-local-5090.ipynb 2>&1"',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        cwd="d:\\JemmaRepo\\Jemma"
    )
    stdout3, stderr3 = p3.communicate()
    exit3 = p3.returncode
except Exception as e:
    stdout3, stderr3, exit3 = "", str(e), -1

results["cmd3"] = {
    "stdout": stdout3.strip(),
    "stderr": stderr3.strip(),
    "exit_code": exit3
}

# If command 3 failed, try to read the report
if exit3 != 0:
    try:
        with open("d:\\JemmaRepo\\Jemma\\state\\notebook-smoke\\notebook_run_report.json", "r") as f:
            report = json.load(f)
            results["cmd3_report"] = report
    except:
        pass

print(json.dumps(results, indent=2))
