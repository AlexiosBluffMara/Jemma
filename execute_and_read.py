#!/usr/bin/env python
"""Execute RUN_NOW.py and read the output file."""
import subprocess
import sys
import time
from pathlib import Path

# Execute RUN_NOW.py
print("Starting RUN_NOW.py execution...")
result = subprocess.run(
    [sys.executable, 'RUN_NOW.py'],
    cwd=r'd:\JemmaRepo\Jemma',
    capture_output=False,
    text=True
)

print(f"Script completed with return code: {result.returncode}")

# Wait a moment for file to be written
time.sleep(2)

# Read the output file
output_path = Path(r'd:\JemmaRepo\Jemma\EXECUTION_OUTPUT.txt')
if output_path.exists():
    print("\n" + "="*80)
    print("EXECUTION_OUTPUT.txt CONTENTS:")
    print("="*80 + "\n")
    print(output_path.read_text())
else:
    print("ERROR: EXECUTION_OUTPUT.txt not found!")
