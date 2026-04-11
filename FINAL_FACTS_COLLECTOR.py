#!/usr/bin/env python3
"""
Final attempt to collect machine facts.
Uses subprocess with shell=True and cmd.exe to maximize compatibility.
Writes output to a file so it can be read and displayed.
"""
import subprocess
import os
import sys
import platform
import re
from pathlib import Path

os.chdir('d:\\JemmaRepo\\Jemma')

def run_cmd(cmd_str, description="", timeout=20):
    """Run cmd with shell=True for maximum compatibility"""
    print(f"\n>>> {description}", flush=True)
    print(f">>> Command: {cmd_str}", flush=True)
    try:
        result = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        print(f">>> Exit Code: {result.returncode}", flush=True)
        output = result.stdout
        if result.stderr and result.returncode != 0:
            output += f"\nSTDERR: {result.stderr}"
        print(output, flush=True)
        return output
    except subprocess.TimeoutExpired:
        msg = f"[TIMEOUT after {timeout}s]"
        print(msg, flush=True)
        return msg
    except Exception as e:
        msg = f"[ERROR: {str(e)}]"
        print(msg, flush=True)
        return msg

# Start collecting facts
print("="*80)
print("MACHINE FACTS COLLECTION - FINAL COMPREHENSIVE")
print("="*80)
print(f"Python: {sys.executable}")
print(f"Platform: {platform.platform()}")
print(f"Working Dir: {os.getcwd()}")
print(f"Timestamp: {__import__('datetime').datetime.now()}")
print("="*80)

facts = {}

# ============= (1) CPU =============
print("\n" + "="*80)
print("SECTION 1: CPU INFORMATION")
print("="*80)

facts['cpu_wmic_name'] = run_cmd(
    'cmd.exe /d /c "wmic cpu get Name"',
    "CPU Name via WMIC"
)

facts['cpu_wmic_full'] = run_cmd(
    'cmd.exe /d /c "wmic cpu get Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed"',
    "CPU Full Details via WMIC"
)

# ============= (2) RAM =============
print("\n" + "="*80)
print("SECTION 2: RAM INFORMATION")
print("="*80)

facts['ram_wmic'] = run_cmd(
    'cmd.exe /d /c "wmic os get TotalVisibleMemorySize"',
    "Total RAM via WMIC (in KB)"
)

# ============= (3) GPU =============
print("\n" + "="*80)
print("SECTION 3: GPU INFORMATION")
print("="*80)

facts['gpu_wmic'] = run_cmd(
    'cmd.exe /d /c "wmic path win32_videocontroller get Name,DriverVersion,Description"',
    "GPU Details via WMIC"
)

facts['nvidia_smi'] = run_cmd(
    'nvidia-smi',
    "NVIDIA GPU Info via nvidia-smi"
)

# ============= (4) DISKS =============
print("\n" + "="*80)
print("SECTION 4: DISK INFORMATION")
print("="*80)

facts['disk_c_fsutil'] = run_cmd(
    'cmd.exe /d /c "fsutil volume diskfree C:"',
    "C: Drive Space via fsutil"
)

facts['disk_d_fsutil'] = run_cmd(
    'cmd.exe /d /c "fsutil volume diskfree D:"',
    "D: Drive Space via fsutil"
)

facts['disks_wmic'] = run_cmd(
    'cmd.exe /d /c "wmic logicaldisk get Name,Size,FreeSpace"',
    "All Disks via WMIC"
)

# ============= (5) NETWORK =============
print("\n" + "="*80)
print("SECTION 5: NETWORK INFORMATION")
print("="*80)

facts['netsh_interfaces'] = run_cmd(
    'cmd.exe /d /c "netsh interface ipv4 show interfaces"',
    "Network Interfaces via netsh"
)

facts['nic_wmic'] = run_cmd(
    'cmd.exe /d /c "wmic nic get Name,Speed,Status,NetConnectionStatus"',
    "NIC Details via WMIC"
)

facts['ipconfig'] = run_cmd(
    'cmd.exe /d /c "ipconfig /all"',
    "Full Network Config via ipconfig",
    timeout=25
)

# ============= (6) JAVA =============
print("\n" + "="*80)
print("SECTION 6: JAVA")
print("="*80)

facts['java_where'] = run_cmd(
    'cmd.exe /d /c "where java"',
    "Find java.exe"
)

facts['java_version'] = run_cmd(
    'cmd.exe /d /c "java -version"',
    "Java Version"
)

# ============= (7) ADB =============
print("\n" + "="*80)
print("SECTION 7: ANDROID DEBUG BRIDGE (ADB)")
print("="*80)

facts['adb_where'] = run_cmd(
    'cmd.exe /d /c "where adb"',
    "Find adb.exe"
)

facts['adb_version'] = run_cmd(
    'cmd.exe /d /c "adb version"',
    "ADB Version"
)

# ============= (8) EMULATOR =============
print("\n" + "="*80)
print("SECTION 8: ANDROID EMULATOR")
print("="*80)

facts['emulator_where'] = run_cmd(
    'cmd.exe /d /c "where emulator"',
    "Find emulator.exe"
)

# ============= (9) ANDROID STUDIO =============
print("\n" + "="*80)
print("SECTION 9: ANDROID STUDIO")
print("="*80)

facts['studio_where'] = run_cmd(
    'cmd.exe /d /c "where studio.exe"',
    "Find studio.exe"
)

# ============= (10) TAILSCALE =============
print("\n" + "="*80)
print("SECTION 10: TAILSCALE")
print("="*80)

facts['tailscale_where'] = run_cmd(
    'cmd.exe /d /c "where tailscale"',
    "Find tailscale.exe"
)

facts['tailscale_version'] = run_cmd(
    'cmd.exe /d /c "tailscale version"',
    "Tailscale Version"
)

facts['tailscale_tasklist'] = run_cmd(
    'cmd.exe /d /c "tasklist | findstr /i tailscale"',
    "Tailscale Processes"
)

# ============= (11) GRADLE =============
print("\n" + "="*80)
print("SECTION 11: GRADLE")
print("="*80)

facts['gradle_where'] = run_cmd(
    'cmd.exe /d /c "where gradle"',
    "Find gradle"
)

facts['gradle_version'] = run_cmd(
    'cmd.exe /d /c "gradle --version"',
    "Gradle Version"
)

# ============= (12) SPEEDTEST =============
print("\n" + "="*80)
print("SECTION 12: SPEEDTEST")
print("="*80)

facts['speedtest_where'] = run_cmd(
    'cmd.exe /d /c "where speedtest"',
    "Find speedtest"
)

facts['speedtest_version'] = run_cmd(
    'cmd.exe /d /c "speedtest --version"',
    "Speedtest Version"
)

# ============= SUMMARY =============
print("\n" + "="*80)
print("FINAL SUMMARY - MACHINE FACTS")
print("="*80)

# Create a summary
summary = []
summary.append("\n" + "="*80)
summary.append("MACHINE FACTS SUMMARY")
summary.append("="*80)

# Parse CPU
cpu_lines = [l.strip() for l in facts.get('cpu_wmic_name', 'N/A').split('\n') if l.strip() and l.strip() != 'Name']
cpu_name = cpu_lines[0] if cpu_lines else 'N/A'
summary.append(f"\nCPU: {cpu_name}")

# Parse RAM
try:
    ram_lines = [l.strip() for l in facts.get('ram_wmic', '').split('\n') if l.strip() and l.isdigit()]
    if ram_lines:
        ram_kb = int(ram_lines[0])
        ram_gb = ram_kb / (1024 * 1024)
        summary.append(f"Total RAM: {ram_gb:.2f} GB")
    else:
        summary.append("Total RAM: N/A")
except:
    summary.append("Total RAM: N/A (parse error)")

# Parse GPU
gpu_lines = [l.strip() for l in facts.get('gpu_wmic', 'N/A').split('\n') if l.strip() and l.strip() not in ['Name', 'DriverVersion', 'Description', '']]
if gpu_lines:
    gpu_list = ', '.join(gpu_lines[:3])  # Take first 3
    summary.append(f"GPU(s): {gpu_list}")
else:
    summary.append("GPU(s): N/A")

# Parse Disks
summary.append("\nDisks:")
try:
    disk_lines = facts.get('disks_wmic', '').split('\n')
    for line in disk_lines:
        if line.strip() and ':' in line and 'FreeSpace' not in line:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    drive = parts[0]
                    free_bytes = int(parts[1])
                    size_bytes = int(parts[2])
                    if size_bytes > 0:
                        size_gb = size_bytes / (1024**3)
                        free_gb = free_bytes / (1024**3)
                        summary.append(f"  {drive}: {size_gb:.2f} GB total, {free_gb:.2f} GB free")
                except:
                    pass
except:
    pass

# Parse Tools
summary.append("\nTools:")
tools = {
    'Java': facts.get('java_where', '').strip().split('\n')[0] if facts.get('java_where') else 'N/A',
    'ADB': facts.get('adb_where', '').strip().split('\n')[0] if facts.get('adb_where') else 'N/A',
    'Android Studio': facts.get('studio_where', '').strip().split('\n')[0] if facts.get('studio_where') else 'N/A',
    'Emulator': facts.get('emulator_where', '').strip().split('\n')[0] if facts.get('emulator_where') else 'N/A',
    'Tailscale': facts.get('tailscale_where', '').strip().split('\n')[0] if facts.get('tailscale_where') else 'N/A',
    'Gradle': facts.get('gradle_where', '').strip().split('\n')[0] if facts.get('gradle_where') else 'N/A',
    'Speedtest': facts.get('speedtest_where', '').strip().split('\n')[0] if facts.get('speedtest_where') else 'N/A',
}

for tool, path in tools.items():
    if '[' in path or 'not found' in path.lower():
        summary.append(f"  {tool}: NOT FOUND")
    elif path:
        summary.append(f"  {tool}: {path}")
    else:
        summary.append(f"  {tool}: N/A")

summary_str = '\n'.join(summary)
print(summary_str)

# Write everything to file
output_path = Path('d:/JemmaRepo/Jemma/MACHINE_FACTS_FINAL.txt')
try:
    with open(output_path, 'w') as f:
        f.write(summary_str)
        f.write("\n\n" + "="*80 + "\n")
        f.write("DETAILED OUTPUT BELOW\n")
        f.write("="*80 + "\n")
        for key, value in facts.items():
            f.write(f"\n{'='*80}\n{key.upper()}\n{'='*80}\n{value}\n")
    print(f"\n\n>>> SUCCESS: Full output written to {output_path}")
except Exception as e:
    print(f"\n\n>>> ERROR writing to file: {e}")

print("\n\nCOLLECTION COMPLETE.")
sys.exit(0)
