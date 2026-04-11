#!/usr/bin/env python3
import subprocess
import sys

def run_command(cmd_string, description, fallback_cmd=None):
    """Run a command and capture stdout, stderr, and exit code"""
    print(f"\n{'='*70}")
    print(f"COMMAND: {description}")
    print(f"Executing: {cmd_string}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd_string,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"Exit Code: {result.returncode}")
        print("\n--- STDOUT ---")
        print(result.stdout if result.stdout else "(empty)")
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
        print("--- END ---")
        
        # If failed and fallback exists, try it
        if result.returncode != 0 and fallback_cmd:
            print(f"\n[Fallback attempt]")
            print(f"Executing: {fallback_cmd}")
            result = subprocess.run(
                fallback_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            print(f"Exit Code: {result.returncode}")
            print("\n--- STDOUT ---")
            print(result.stdout if result.stdout else "(empty)")
            if result.stderr:
                print("\n--- STDERR ---")
                print(result.stderr)
            print("--- END ---")
            
    except subprocess.TimeoutExpired:
        print(f"ERROR: Command timed out after 30 seconds")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "="*70)
print("WINDOWS SYSTEM INFORMATION COLLECTION")
print("="*70)

# Command 1: CPU Information
run_command(
    'cmd.exe /d /c "wmic cpu get Name /value"',
    "1. CPU Information (wmic)",
    'cmd.exe /d /c "reg query HKLM\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0 /v ProcessorNameString"'
)

# Command 2: C: Drive free space
run_command(
    'cmd.exe /d /c "fsutil volume diskfree c:"',
    "2. C: Drive Free Space"
)

# Command 3: D: Drive free space
run_command(
    'cmd.exe /d /c "fsutil volume diskfree d:"',
    "3. D: Drive Free Space"
)

# Command 4: Network interfaces
run_command(
    'cmd.exe /d /c "netsh interface show interface"',
    "4. Network Interfaces"
)

# Command 5: Active NICs with speed
run_command(
    'cmd.exe /d /c "wmic nic where NetConnectionStatus=2 get Name,NetConnectionID,Speed /format:list"',
    "5. Active NICs with Speed (wmic)",
    'powershell.exe -NoProfile -Command "Get-NetAdapter | Where-Object Status -eq \'Up\' | Format-Table -Auto Name,InterfaceDescription,Status,LinkSpeed"'
)

# Command 6: Video Controller
run_command(
    'cmd.exe /d /c "wmic path win32_VideoController get Name /value"',
    "6. Video Controller (wmic)",
    'powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
)

print("\n" + "="*70)
print("COLLECTION COMPLETE")
print("="*70)
