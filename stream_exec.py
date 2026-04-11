#!/usr/bin/env python
"""Execute the workflow and wait for completion"""
import subprocess
import sys
import os
import time

os.chdir(r'D:\JemmaRepo\Jemma')

print("Starting workflow execution...")
print(f"Working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print()

# Run the workflow script
proc = subprocess.Popen(
    [sys.executable, '__workflow_exec__.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1
)

# Stream output
try:
    for line in proc.stdout:
        print(line, end='')
    proc.wait()
    print(f"\nProcess exited with code: {proc.returncode}")
except KeyboardInterrupt:
    proc.terminate()
    print("Process terminated")
