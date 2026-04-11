#!/usr/bin/env python3
"""
Gather exact machine facts using Windows commands.
Works in environments where PowerShell 6+ is unavailable.
Uses subprocess to run WMIC, fsutil, netsh, and other native Windows commands.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_cmd(cmd_list, timeout=15):
    """Execute command and return output safely"""
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )
        return result.stdout + (result.stderr if result.returncode != 0 else "")
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except FileNotFoundError:
        return "[COMMAND NOT FOUND]"
    except Exception as e:
        return f"[ERROR: {e}]"

def extract_value(output, pattern_text):
    """Extract clean value from command output"""
    lines = [l.strip() for l in output.split('\n') if l.strip()]
    # Skip header lines and return first non-empty value
    for line in lines[1:]:
        if line:
            return line
    return "N/A"

def format_bytes(b):
    """Convert bytes to readable format"""
    try:
        b = int(b)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024:
                return f"{b:.2f} {unit}"
            b /= 1024
        return f"{b:.2f} PB"
    except:
        return "N/A"

print("=" * 80)
print("GATHERING EXACT MACHINE FACTS - WINDOWS NATIVE COMMANDS")
print("=" * 80)
print(f"Working Directory: {os.getcwd()}")
print(f"Python: {sys.executable}")

results = {}

# ========== (1) CPU MARKETING NAME ==========
print("\n[1/12] CPU Marketing Name...")
cpu_output = run_cmd(['wmic', 'cpu', 'get', 'name'], timeout=10)
cpu_name = extract_value(cpu_output, "Name")
print(f"  CPU: {cpu_name}")
results['cpu_name'] = cpu_name

# ========== (2) TOTAL RAM ==========
print("\n[2/12] Total RAM...")
ram_output = run_cmd(['wmic', 'os', 'get', 'TotalVisibleMemorySize'], timeout=10)
try:
    ram_kb = int(extract_value(ram_output, "TotalVisibleMemorySize").strip())
    ram_gb = ram_kb / (1024 * 1024)
    ram_str = f"{ram_gb:.2f} GB"
except:
    ram_str = "N/A"
print(f"  Total RAM: {ram_str}")
results['total_ram'] = ram_str

# ========== (3) DISK INFORMATION ==========
print("\n[3/12] Fixed Disk Information...")
disk_output = run_cmd(['wmic', 'logicaldisk', 'get', 'name,size,freespace'], timeout=10)
print("  Disk Summary:")
disks = {}
for line in disk_output.split('\n'):
    parts = line.split()
    if len(parts) >= 3 and parts[0] not in ['Name', '']:
        try:
            drive = parts[0]
            free_bytes = int(parts[1])
            size_bytes = int(parts[2])
            free_gb = size_bytes / (1024**3)
            avail_gb = free_bytes / (1024**3)
            disks[drive] = f"{free_gb:.2f} GB total, {avail_gb:.2f} GB free"
            print(f"    {drive}: {disks[drive]}")
        except:
            pass
results['disks'] = disks

# ========== (4) GPU INFORMATION ==========
print("\n[4/12] GPU Information...")
gpu_output = run_cmd(['wmic', 'path', 'win32_videocontroller', 'get', 'name,driverversion'], timeout=10)
gpu_names = []
for line in gpu_output.split('\n'):
    line = line.strip()
    if line and line != 'Name' and 'DriverVersion' not in line and line:
        parts = line.split()
        if parts[0] not in ['', 'Name']:
            gpu_names.append(parts[0])
gpu_str = ', '.join(gpu_names) if gpu_names else "N/A"
print(f"  GPU(s): {gpu_str}")
results['gpus'] = gpu_str

# Try nvidia-smi for additional GPU info
print("\n[5/12] NVIDIA GPU Details (nvidia-smi)...")
nvidia_output = run_cmd(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'], timeout=10)
if '[COMMAND NOT FOUND]' not in nvidia_output and '[ERROR' not in nvidia_output:
    print(f"  nvidia-smi output:\n{nvidia_output.strip()}")
    results['nvidia_details'] = nvidia_output.strip()
else:
    print("  nvidia-smi: Not available or not in PATH")
    results['nvidia_details'] = "Not available"

# ========== (6) NETWORK ADAPTERS ==========
print("\n[6/12] Active Network Adapters...")
netsh_output = run_cmd(['netsh', 'interface', 'ipv4', 'show', 'interfaces'], timeout=10)
print("  Network Interfaces:")
print(netsh_output.strip())
results['network_interfaces'] = netsh_output

# ========== (7) NETWORK ADAPTER SPEEDS ==========
print("\n[7/12] Network Adapter Speeds...")
nic_output = run_cmd(['wmic', 'nic', 'get', 'name,speed,status'], timeout=10)
print("  NIC Info (Speed in bps):")
adapters = {}
for line in nic_output.split('\n'):
    line = line.strip()
    if line and line != 'Name  Speed   Status':
        parts = line.split()
        if len(parts) >= 2 and parts[0] not in ['Name', '']:
            try:
                adapter_name = parts[0]
                speed_bps = int(parts[1])
                if speed_bps > 0:
                    speed_gbps = speed_bps / 1_000_000_000
                    adapters[adapter_name] = f"{speed_gbps:.2f} Gbps"
                    print(f"    {adapter_name}: {adapters[adapter_name]}")
                else:
                    print(f"    {adapter_name}: No speed (disconnected)")
            except:
                pass
results['network_speeds'] = adapters

# ========== (8) IPCONFIG /ALL ==========
print("\n[8/12] Full Network Configuration (ipconfig /all)...")
ipconfig_output = run_cmd(['ipconfig', '/all'], timeout=15)
results['ipconfig'] = ipconfig_output
# Print summary
print("  (Full output stored in results)")

# ========== (9) JAVA PATH & VERSION ==========
print("\n[9/12] Java Installation...")
java_path = run_cmd(['where', 'java'], timeout=5)
java_path = java_path.strip()
java_version = "N/A"
if java_path and '[' not in java_path:
    print(f"  Java Path: {java_path}")
    version_output = run_cmd(['java', '-version'], timeout=5)
    java_version = extract_value(version_output, "version")
    print(f"  Java Version: {java_version}")
else:
    print(f"  Java: Not found in PATH")
results['java_path'] = java_path if java_path else "Not found"
results['java_version'] = java_version

# ========== (10) ANDROID STUDIO / ADB / EMULATOR ==========
print("\n[10/12] Android Tools...")
adb_path = run_cmd(['where', 'adb'], timeout=5).strip()
if adb_path and '[' not in adb_path:
    print(f"  ADB Path: {adb_path}")
    adb_version = run_cmd(['adb', 'version'], timeout=5)
    print(f"  ADB Version: {extract_value(adb_version, 'version')}")
    results['adb_path'] = adb_path
    results['adb_version'] = adb_version[:100]
else:
    print(f"  ADB: Not found in PATH")
    results['adb_path'] = "Not found"

# Try to find Android Studio
as_path = run_cmd(['where', 'studio.exe'], timeout=5).strip()
if as_path and '[' not in as_path:
    print(f"  Android Studio: {as_path}")
    results['android_studio_path'] = as_path
else:
    print(f"  Android Studio: Not found in standard PATH")
    # Check common installation paths
    common_paths = [
        r"C:\Program Files\Android\Android Studio\bin\studio.exe",
        r"C:\Program Files (x86)\Android\Android Studio\bin\studio.exe"
    ]
    for path in common_paths:
        if Path(path).exists():
            print(f"  Android Studio (found at): {path}")
            results['android_studio_path'] = path
            break
    else:
        results['android_studio_path'] = "Not found"

# ========== (11) TAILSCALE ==========
print("\n[11/12] Tailscale...")
tailscale_path = run_cmd(['where', 'tailscale'], timeout=5).strip()
if tailscale_path and '[' not in tailscale_path:
    print(f"  Tailscale Path: {tailscale_path}")
    tailscale_version = run_cmd(['tailscale', 'version'], timeout=5)
    print(f"  Tailscale Version: {tailscale_version[:100]}")
    results['tailscale_path'] = tailscale_path
    results['tailscale_version'] = tailscale_version[:100]
else:
    print(f"  Tailscale: Not found in PATH")
    results['tailscale_path'] = "Not found"

# ========== (12) GRADLE & SPEEDTEST ==========
print("\n[12/12] Gradle & Speedtest...")
gradle_path = run_cmd(['where', 'gradle'], timeout=5).strip()
if gradle_path and '[' not in gradle_path:
    print(f"  Gradle Path: {gradle_path}")
    gradle_version = run_cmd(['gradle', '--version'], timeout=10)
    print(f"  Gradle Version: {extract_value(gradle_version, 'Gradle')}")
    results['gradle_path'] = gradle_path
    results['gradle_version'] = gradle_version[:100]
else:
    print(f"  Gradle: Not found in PATH")
    results['gradle_path'] = "Not found"

speedtest_path = run_cmd(['where', 'speedtest'], timeout=5).strip()
if speedtest_path and '[' not in speedtest_path:
    print(f"  Speedtest Path: {speedtest_path}")
    results['speedtest_path'] = speedtest_path
else:
    print(f"  Speedtest: Not found in PATH")
    results['speedtest_path'] = "Not found"

# ========== SUMMARY ==========
print("\n" + "=" * 80)
print("SUMMARY - EXACT MACHINE VALUES")
print("=" * 80)
print(f"CPU:              {results.get('cpu_name', 'N/A')}")
print(f"Total RAM:        {results.get('total_ram', 'N/A')}")
print(f"GPU(s):           {results.get('gpus', 'N/A')}")
print(f"\nNetwork Adapters:")
for adapter, speed in results.get('network_speeds', {}).items():
    print(f"  {adapter}: {speed}")
print(f"\nFixed Disks:")
for drive, info in results.get('disks', {}).items():
    print(f"  {drive}: {info}")
print(f"\nSoftware/Tools:")
print(f"  Java:          {results.get('java_path', 'Not found')}")
print(f"  ADB:           {results.get('adb_path', 'Not found')}")
print(f"  Android Studio: {results.get('android_studio_path', 'Not found')}")
print(f"  Tailscale:     {results.get('tailscale_path', 'Not found')}")
print(f"  Gradle:        {results.get('gradle_path', 'Not found')}")
print(f"  Speedtest:     {results.get('speedtest_path', 'Not found')}")
print("=" * 80)
