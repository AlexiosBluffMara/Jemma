#!/usr/bin/env python3
"""Execute system facts collection batch file"""
import subprocess
import sys
import os

os.chdir('d:\\JemmaRepo\\Jemma')

# Execute the batch file
result = subprocess.run(
    ['cmd.exe', '/c', 'COLLECT_FACTS.bat'],
    capture_output=True,
    text=True,
    timeout=60
)

print("STDOUT:")
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

print(f"\nReturn Code: {result.returncode}")
