#!/usr/bin/env python
"""Execute simple_runner.py and report results"""
import subprocess
import sys
import os

os.chdir(r'd:\JemmaRepo\Jemma')

# Execute simple_runner.py
try:
    result = subprocess.run(
        [sys.executable, 'simple_runner.py'], 
        capture_output=True, 
        text=True, 
        timeout=3800
    )
    
    print("=" * 80)
    print("EXECUTION COMPLETE")
    print("=" * 80)
    print(f"Return code: {result.returncode}")
    print("\n" + "=" * 80)
    print("STDOUT OUTPUT:")
    print("=" * 80)
    print(result.stdout)
    print("\n" + "=" * 80)
    print("STDERR OUTPUT:")
    print("=" * 80)
    print(result.stderr)
    
except subprocess.TimeoutExpired:
    print("ERROR: Process timed out after 3800 seconds")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
