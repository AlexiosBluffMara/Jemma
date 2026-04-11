#!/usr/bin/env python3
"""Direct system information gathering"""
import sys
import os

# Add repo root to path
sys.path.insert(0, 'D:\\JemmaRepo\\Jemma\\src')
sys.path.insert(0, 'D:\\JemmaRepo\\Jemma')

print("\n" + "="*80)
print("SYSTEM INFORMATION - Direct Collection")
print("="*80)

# Try importing and calling the system probe
try:
    from pathlib import Path
    from jemma.benchmarks.system_probe import collect_system_probe
    
    print("\n(1) System Probe from jemma.benchmarks:")
    probe = collect_system_probe(Path('D:\\JemmaRepo\\Jemma'))
    
    for key, value in probe.items():
        print(f"\n{key}:")
        if isinstance(value, dict):
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {value}")
            
except Exception as e:
    print(f"Error loading jemma.benchmarks: {e}")
    import traceback
    traceback.print_exc()

# Direct platform info
print("\n" + "="*80)
print("(2) Platform Info (stdlib):")
print("="*80)

import platform
import shutil

print(f"\nPlatform: {platform.platform()}")
print(f"Python: {platform.python_version()}")
print(f"Processor: {platform.processor()}")
print(f"Architecture: {platform.machine()}")
print(f"CPU Count: {os.cpu_count()}")

# Environment
print("\n" + "="*80)
print("(3) Environment Variables:")
print("="*80)

for var in ['PROCESSOR_IDENTIFIER', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'COMPUTERNAME']:
    val = os.environ.get(var)
    print(f"{var}: {val if val else 'NOT SET'}")

# Disk
print("\n" + "="*80)
print("(4) Disk Space:")
print("="*80)

for drive in ['C:', 'D:']:
    try:
        total, used, free = shutil.disk_usage(drive)
        print(f"\n{drive}:")
        print(f"  Total: {total:,} bytes ({total / (1024**3):.2f} GB)")
        print(f"  Used:  {used:,} bytes ({used / (1024**3):.2f} GB)")
        print(f"  Free:  {free:,} bytes ({free / (1024**3):.2f} GB)")
    except Exception as e:
        print(f"{drive}: {e}")

# GPU via torch
print("\n" + "="*80)
print("(5) GPU via PyTorch:")
print("="*80)

try:
    import torch
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA: {torch.version.cuda}")
        props = torch.cuda.get_device_properties(0)
        print(f"Memory: {props.total_memory / (1024**3):.2f} GB")
except ImportError:
    print("PyTorch not installed")
except Exception as e:
    print(f"Error: {e}")

# Try nvidia-smi directly
print("\n" + "="*80)
print("(6) Running nvidia-smi:")
print("="*80)

import subprocess
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
    print(result.stdout)
except Exception as e:
    print(f"nvidia-smi error: {e}")

# Try wmic commands
print("\n" + "="*80)
print("(7) Running WMI commands:")
print("="*80)

commands = [
    (['wmic', 'cpu', 'get', 'name'], "CPU"),
    (['wmic', 'path', 'win32_videocontroller', 'get', 'name'], "GPU"),
]

for cmd, desc in commands:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        print(f"\n{desc}:")
        print(result.stdout if result.stdout else result.stderr)
    except Exception as e:
        print(f"{desc} error: {e}")

print("\n" + "="*80)
print("END")
print("="*80)
