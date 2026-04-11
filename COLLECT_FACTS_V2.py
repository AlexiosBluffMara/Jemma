#!/usr/bin/env python3
"""
Collect machine facts and write to file for examination.
Can be run directly with: python COLLECT_FACTS_V2.py
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

output_file = Path("d:/JemmaRepo/Jemma/MACHINE_FACTS_OUTPUT.txt")

def write_section(title):
    """Write a section header"""
    line = "=" * 80
    return f"\n{line}\n{title}\n{line}\n"

def run_cmd(cmd_list, timeout=15, description=""):
    """Execute command and return formatted output"""
    output = ""
    if description:
        output += f"\nCommand: {' '.join(cmd_list)}\n"
        output += "-" * 60 + "\n"
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )
        output += result.stdout
        if result.stderr and result.returncode != 0:
            output += f"STDERR: {result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except FileNotFoundError:
        return f"[COMMAND NOT FOUND: {cmd_list[0]}]"
    except Exception as e:
        return f"[ERROR: {e}]"

# Start collection
all_output = ""
all_output += f"\n\nMACHINE FACTS COLLECTION\nDate: {datetime.now()}\nPython: {sys.executable}\nVersion: {sys.version}\n"

# CPU
all_output += write_section("1. CPU MARKETING NAME")
all_output += run_cmd(['wmic', 'cpu', 'get', 'name'], description="CPU Name")

all_output += write_section("2. CPU DETAILS")
all_output += run_cmd(['wmic', 'cpu', 'get', 'name,manufacturer,numberofcores,numberoflogicalprocessors,maxclockspeed'], description="Full CPU details")

# RAM
all_output += write_section("3. TOTAL SYSTEM RAM")
all_output += run_cmd(['wmic', 'os', 'get', 'TotalVisibleMemorySize'], description="RAM in KB")

# GPU
all_output += write_section("4. GPU INFORMATION")
all_output += run_cmd(['wmic', 'path', 'win32_videocontroller', 'get', 'name,driverversion,description'], description="GPU details")

# DISKS
all_output += write_section("5. FIXED DISKS - Size and Free Space")
all_output += run_cmd(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], description="All disks")

# Network
all_output += write_section("6. NETWORK INTERFACES (netsh)")
all_output += run_cmd(['netsh', 'interface', 'ipv4', 'show', 'interfaces'], description="Network interfaces")

all_output += write_section("7. NETWORK ADAPTER SPEEDS (wmic)")
all_output += run_cmd(['wmic', 'nic', 'get', 'name,speed,status,netconnectionstatus'], description="NIC speeds in bps")

all_output += write_section("8. FULL NETWORK CONFIGURATION (ipconfig /all)")
all_output += run_cmd(['ipconfig', '/all'], description="ipconfig detailed", timeout=20)

# Software/Tools
all_output += write_section("9. JAVA")
all_output += run_cmd(['where', 'java'], description="Find java")
all_output += run_cmd(['java', '-version'], description="Java version")

all_output += write_section("10. ADB (Android Debug Bridge)")
all_output += run_cmd(['where', 'adb'], description="Find adb")
all_output += run_cmd(['adb', 'version'], description="ADB version")

all_output += write_section("11. ANDROID EMULATOR")
all_output += run_cmd(['where', 'emulator'], description="Find emulator")

all_output += write_section("12. ANDROID STUDIO")
all_output += run_cmd(['where', 'studio.exe'], description="Find studio.exe")

all_output += write_section("13. TAILSCALE")
all_output += run_cmd(['where', 'tailscale'], description="Find tailscale")
all_output += run_cmd(['tailscale', 'version'], description="Tailscale version")

all_output += write_section("14. GRADLE")
all_output += run_cmd(['where', 'gradle'], description="Find gradle")
all_output += run_cmd(['gradle', '--version'], description="Gradle version")

all_output += write_section("15. SPEEDTEST")
all_output += run_cmd(['where', 'speedtest'], description="Find speedtest")
all_output += run_cmd(['speedtest', '--version'], description="Speedtest version")

all_output += write_section("16. NVIDIA GPU (nvidia-smi)")
all_output += run_cmd(['where', 'nvidia-smi'], description="Find nvidia-smi")
all_output += run_cmd(['nvidia-smi'], description="nvidia-smi output")

# Write to file
try:
    with open(output_file, 'w') as f:
        f.write(all_output)
    print(f"Success! Facts written to: {output_file}")
    print(f"File size: {output_file.stat().st_size} bytes")
    print("\nFirst 2000 characters:")
    print(all_output[:2000])
except Exception as e:
    print(f"Error writing file: {e}")
    print("Output would have been:")
    print(all_output[:1000])
