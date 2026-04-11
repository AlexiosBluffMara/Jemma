#!/usr/bin/env python
"""Quick executor for workflow script"""
import subprocess
import sys
import os

os.chdir(r'D:\JemmaRepo\Jemma')

# Run the workflow script and capture output
try:
    result = subprocess.run(
        [sys.executable, '__workflow_exec__.py'],
        capture_output=False,
        text=True,
        timeout=600  # 10 minute timeout
    )
    sys.exit(result.returncode)
except subprocess.TimeoutExpired:
    print("ERROR: Script execution timed out after 10 minutes")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
