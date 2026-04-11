#!/usr/bin/env python
import subprocess
import sys
import time

# Execute RUN_NOW.py
print("Starting RUN_NOW.py execution...")
result = subprocess.run([sys.executable, 'RUN_NOW.py'], cwd=r'd:\JemmaRepo\Jemma')
print(f"Script completed with return code: {result.returncode}")

# Wait a moment for file to be written
time.sleep(2)

# Read and display the output file
from pathlib import Path
output_file = Path(r'd:\JemmaRepo\Jemma\EXECUTION_OUTPUT.txt')
if output_file.exists():
    print("\n" + "="*80)
    print("EXECUTION OUTPUT FILE CONTENTS:")
    print("="*80)
    print(output_file.read_text())
else:
    print("ERROR: Output file was not created!")
