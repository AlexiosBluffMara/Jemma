#!/usr/bin/env python3
"""
JEMMA Project Workflow Execution Script
Executes the complete workflow and captures all output
"""

import subprocess
import sys
import os

# Change to repo directory
REPO_DIR = r"D:\JemmaRepo\Jemma"
os.chdir(REPO_DIR)

output_lines = []

def log_and_print(msg):
    """Log message and print to stdout"""
    print(msg)
    output_lines.append(msg)

def run_command(cmd_description, cmd_list):
    """Run a command and capture output"""
    log_and_print("")
    log_and_print("=" * 80)
    log_and_print(cmd_description)
    log_and_print("=" * 80)
    
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            shell=False
        )
        
        if result.stdout:
            log_and_print(result.stdout)
        if result.stderr:
            log_and_print("STDERR:")
            log_and_print(result.stderr)
        
        log_and_print(f"Exit Code: {result.returncode}")
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        log_and_print(f"Error executing command: {e}")
        return -1, "", str(e)

# Print header
log_and_print("=" * 80)
log_and_print("JEMMA PROJECT WORKFLOW EXECUTION")
log_and_print("=" * 80)
log_and_print(f"Working Directory: {os.getcwd()}")
log_and_print(f"Python Executable: {sys.executable}")
log_and_print("")

# Command 1: Python version
exit_code_1, stdout_1, stderr_1 = run_command(
    "COMMAND 1: python --version",
    [sys.executable, "--version"]
)

# Command 2: Python executable and version info
exit_code_2, stdout_2, stderr_2 = run_command(
    "COMMAND 2: python -c (import sys; print info)",
    [sys.executable, "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"]
)

# Command 3: pip list filtered
log_and_print("")
log_and_print("=" * 80)
log_and_print("COMMAND 3: python -m pip list | findstr /I 'fastapi discord uvicorn'")
log_and_print("=" * 80)

try:
    # Run pip list
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list"],
        capture_output=True,
        text=True
    )
    
    # Filter for the packages
    lines = result.stdout.split('\n')
    filtered_lines = [line for line in lines if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn'])]
    
    if filtered_lines:
        for line in filtered_lines:
            log_and_print(line)
    else:
        log_and_print("No matching packages found (they may not be installed yet)")
    
    exit_code_3 = result.returncode
except Exception as e:
    log_and_print(f"Error: {e}")
    exit_code_3 = -1

# Command 4: Install project
exit_code_4, stdout_4, stderr_4 = run_command(
    "COMMAND 4: python -m pip install -e .",
    [sys.executable, "-m", "pip", "install", "-e", "."]
)

# Command 5: Run tests
exit_code_5, stdout_5, stderr_5 = run_command(
    "COMMAND 5: python -m unittest discover -s tests -p test_*.py -v",
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
)

# Print summary
log_and_print("")
log_and_print("=" * 80)
log_and_print("WORKFLOW EXECUTION SUMMARY")
log_and_print("=" * 80)
log_and_print(f"Command 1 Exit Code: {exit_code_1}")
log_and_print(f"Command 2 Exit Code: {exit_code_2}")
log_and_print(f"Command 3 Exit Code: {exit_code_3}")
log_and_print(f"Command 4 Exit Code: {exit_code_4}")
log_and_print(f"Command 5 Exit Code: {exit_code_5}")
log_and_print("")
log_and_print("=" * 80)
log_and_print("END OF WORKFLOW")
log_and_print("=" * 80)

# Print all output
print("\n".join(output_lines))
