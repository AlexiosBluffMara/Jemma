#!/usr/bin/env python3
import subprocess
import sys

print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")

# Test 1: Simple command
print("\n=== Test 1: wmic cpu get name ===")
result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True, timeout=5)
print(result.stdout)

# Test 2: RAM
print("=== Test 2: wmic os get TotalVisibleMemorySize ===")
result = subprocess.run(['wmic', 'os', 'get', 'TotalVisibleMemorySize'], capture_output=True, text=True, timeout=5)
print(result.stdout)

# Test 3: GPU
print("=== Test 3: wmic path win32_videocontroller get name ===")
result = subprocess.run(['wmic', 'path', 'win32_videocontroller', 'get', 'name'], capture_output=True, text=True, timeout=5)
print(result.stdout)

# Test 4: Disk
print("=== Test 4: wmic logicaldisk get name,size,freespace ===")
result = subprocess.run(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], capture_output=True, text=True, timeout=5)
print(result.stdout)

print("All basic tests completed successfully!")
