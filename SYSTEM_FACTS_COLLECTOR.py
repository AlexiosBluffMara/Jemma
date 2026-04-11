#!/usr/bin/env python3
"""
Collect system facts on Windows using subprocess
This uses the local Python environment to execute commands
"""
import subprocess
import sys
import os
from pathlib import Path

def run_cmd(description, cmd_list, timeout=15):
    """Execute command and return output"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd_list)}")
    print("-" * 80)
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )
        output = result.stdout
        if result.stderr and result.returncode != 0:
            output += "\nSTDERR: " + result.stderr
        print(output)
        return output
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout} seconds")
        return ""
    except FileNotFoundError as e:
        print(f"COMMAND NOT FOUND: {e}")
        return ""
    except Exception as e:
        print(f"ERROR: {e}")
        return ""

def main():
    os.chdir('d:\\JemmaRepo\\Jemma')
    
    print("\n" + "="*80)
    print("WINDOWS SYSTEM FACTS COLLECTION")
    print("="*80)
    print(f"Working Directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    print(f"Python Version: {sys.version}")
    
    results = {}
    
    # (1) CPU INFORMATION
    cpu_output = run_cmd(
        "(1) CPU INFORMATION",
        ['wmic', 'cpu', 'get', 'name,manufacturer,maxclockspeed,numberofcores,numberoflogicalprocessors']
    )
    results['cpu'] = cpu_output
    
    # (2) DISK C: SPACE
    c_disk = run_cmd(
        "(2) DISK C: SPACE",
        ['fsutil', 'volume', 'diskfree', 'C:']
    )
    results['disk_c'] = c_disk
    
    # (3) DISK D: SPACE
    d_disk = run_cmd(
        "(3) DISK D: SPACE",
        ['fsutil', 'volume', 'diskfree', 'D:']
    )
    results['disk_d'] = d_disk
    
    # (4) ALL DISKS SUMMARY
    all_disks = run_cmd(
        "(4) ALL DISKS SUMMARY",
        ['wmic', 'logicaldisk', 'get', 'name,size,freespace']
    )
    results['all_disks'] = all_disks
    
    # (5) GPU INFORMATION
    gpu = run_cmd(
        "(5) GPU INFORMATION",
        ['wmic', 'path', 'win32_videocontroller', 'get', 'name,driverversion,description']
    )
    results['gpu'] = gpu
    
    # (6) NETWORK INTERFACES
    net_if = run_cmd(
        "(6) NETWORK INTERFACES",
        ['netsh', 'interface', 'ipv4', 'show', 'interfaces']
    )
    results['network_if'] = net_if
    
    # (7) NETWORK ADAPTER SPEEDS
    net_speed = run_cmd(
        "(7) NETWORK ADAPTER SPEEDS (wmic nic)",
        ['wmic', 'nic', 'get', 'name,speed,status,netconnectionstatus']
    )
    results['network_speeds'] = net_speed
    
    # (8) IPCONFIG /ALL
    ipconfig = run_cmd(
        "(8) IPCONFIG /ALL",
        ['ipconfig', '/all'],
        timeout=20
    )
    results['ipconfig'] = ipconfig
    
    # (9) TAILSCALE CHECK
    print(f"\n{'='*80}")
    print("(9) TAILSCALE STATUS CHECK")
    print(f"{'='*80}")
    try:
        tasklist = subprocess.run(['tasklist'], capture_output=True, text=True)
        tailscale_procs = [line for line in tasklist.stdout.split('\n') if 'tailscale' in line.lower()]
        print("Tailscale processes:")
        if tailscale_procs:
            print('\n'.join(tailscale_procs))
        else:
            print("No Tailscale processes found")
        results['tailscale_procs'] = '\n'.join(tailscale_procs) if tailscale_procs else "None"
    except Exception as e:
        print(f"Error checking Tailscale: {e}")
        results['tailscale_procs'] = f"Error: {e}"
    
    # (10) NVIDIA GPU (nvidia-smi)
    nvidia = run_cmd(
        "(10) NVIDIA GPU INFORMATION (nvidia-smi)",
        ['nvidia-smi'],
        timeout=10
    )
    results['nvidia_smi'] = nvidia if nvidia else "nvidia-smi not available"
    
    print(f"\n{'='*80}")
    print("COLLECTION COMPLETE")
    print(f"{'='*80}")
    
    return results

if __name__ == '__main__':
    main()
