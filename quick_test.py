#!/usr/bin/env python3
import sys
import subprocess

print("Python executable:", sys.executable)
print("Python version:", sys.version)

# Try a simple command
try:
    result = subprocess.run(['whoami'], capture_output=True, text=True, timeout=5)
    print("\nwhoami output:")
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")

# Try wmic cpu get name
try:
    result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True, timeout=10)
    print("\nwmic cpu get name:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error: {e}")
