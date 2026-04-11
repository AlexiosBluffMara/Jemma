#!/usr/bin/env python3
"""Gather local machine facts by executing Windows commands"""
import subprocess
import sys

def run_cmd(cmd, description):
    """Run a command and return output"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print("STDERR:", result.stderr)
        return result.stdout + (result.stderr if result.returncode != 0 else "")
    except Exception as e:
        print(f"ERROR: {e}")
        return ""

print("\n" + "="*80)
print("LOCAL MACHINE FACTS COLLECTION")
print("="*80)

# (1) CPU
run_cmd(['wmic', 'cpu', 'get', 'name,manufacturer,maxclockspeed,numberofcores,numberoflogicalprocessors'], 
        "(1) CPU INFORMATION")

# (2) Disk C:
run_cmd(['fsutil', 'volume', 'diskfree', 'C:'], 
        "(2) DISK C: SPACE")

# (3) Disk D:
run_cmd(['fsutil', 'volume', 'diskfree', 'D:'], 
        "(3) DISK D: SPACE")

# (4) All Disks Summary
run_cmd(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], 
        "(4) ALL DISKS SUMMARY")

# (5) GPU
run_cmd(['wmic', 'path', 'win32_videocontroller', 'get', 'name,driverversion,description'], 
        "(5) GPU INFORMATION")

# (6) Network adapters with speed
run_cmd(['netsh', 'interface', 'ipv4', 'show', 'interfaces'], 
        "(6) NETWORK INTERFACES")

# (7) Network adapter speeds
run_cmd(['wmic', 'nic', 'get', 'name,speed,status'], 
        "(7) NETWORK ADAPTER SPEEDS (bps)")

# (8) ipconfig all
run_cmd(['ipconfig', '/all'], 
        "(8) IPCONFIG /ALL - Network Configuration Details")

# (9) nvidia-smi if available
try:
    run_cmd(['nvidia-smi'], 
            "(9) NVIDIA GPU DETAILS (nvidia-smi)")
except:
    pass

print("\n" + "="*80)
print("COLLECTION COMPLETE")
print("="*80)
