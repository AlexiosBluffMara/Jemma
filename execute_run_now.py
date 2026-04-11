#!/usr/bin/env python
import subprocess
import sys

# Run the RUN_NOW.py script
result = subprocess.run([sys.executable, r'd:\JemmaRepo\Jemma\RUN_NOW.py'], 
                       capture_output=False, text=True)
sys.exit(result.returncode)
