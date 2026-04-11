import subprocess
import os
import winreg

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

# Disk info
print("=" * 60)
print("DISK C: (fsutil volume diskfree C:)")
print("=" * 60)
print(run_cmd('fsutil volume diskfree C:'))

print("\n" + "=" * 60)
print("DISK D: (fsutil volume diskfree D:)")
print("=" * 60)
print(run_cmd('fsutil volume diskfree D:'))

# Tools paths
print("\n" + "=" * 60)
print("JAVA PATH (where java)")
print("=" * 60)
print(run_cmd('where java'))

print("\n" + "=" * 60)
print("ADB PATH (where adb)")
print("=" * 60)
print(run_cmd('where adb'))

print("\n" + "=" * 60)
print("GRADLE (where gradle)")
print("=" * 60)
print(run_cmd('where gradle'))

print("\n" + "=" * 60)
print("GRADLEW (where gradlew)")
print("=" * 60)
print(run_cmd('where gradlew'))

print("\n" + "=" * 60)
print("EMULATOR (where emulator)")
print("=" * 60)
print(run_cmd('where emulator'))

print("\n" + "=" * 60)
print("TAILSCALE (where tailscale)")
print("=" * 60)
print(run_cmd('where tailscale'))

print("\n" + "=" * 60)
print("SPEEDTEST (where speedtest)")
print("=" * 60)
print(run_cmd('where speedtest'))

# Env vars
print("\n" + "=" * 60)
print("KEY ENVIRONMENT VARIABLES")
print("=" * 60)
for key in ['JAVA_HOME', 'ANDROID_HOME', 'ANDROID_SDK_ROOT', 'GRADLE_HOME', 'PATH', 'PATHEXT']:
    val = os.environ.get(key, 'NOT SET')
    if key == 'PATH':
        val = val[:200] + '...' if len(val) > 200 else val
    print(f"{key}={val}")

# Check Java registry
print("\n" + "=" * 60)
print("REGISTRY JAVA (HKLM\\SOFTWARE\\JavaSoft)")
print("=" * 60)
try:
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JavaSoft")
    for i in range(100):
        try:
            subkey_name, _, _ = winreg.EnumKey(key, i)
            print(f"  Subkey: {subkey_name}")
            subkey = winreg.OpenKey(key, subkey_name)
            for j in range(100):
                try:
                    val_name, val_data, val_type = winreg.EnumValue(subkey, j)
                    print(f"    {val_name}={val_data}")
                except OSError:
                    break
        except OSError:
            break
except FileNotFoundError:
    print("  KEY NOT FOUND")
except Exception as e:
    print(f"  ERROR: {e}")
