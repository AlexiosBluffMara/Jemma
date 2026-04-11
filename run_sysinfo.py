import subprocess
import sys

# Run the batch script and capture output
result = subprocess.run(
    [r'cmd.exe', '/c', r'd:\JemmaRepo\Jemma\sysinfo_gather.bat'],
    capture_output=True,
    text=True,
    timeout=120
)

# Print both stdout and stderr
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)
print(f"Return code: {result.returncode}")
