import subprocess
import os

os.chdir(r"D:\JemmaRepo\Jemma")

# Just test if python works
result = subprocess.run(["python", "--version"], capture_output=True, text=True)
print("Test command result:")
print(f"Exit code: {result.returncode}")
print(f"Output: {result.stdout}")
print(f"Error: {result.stderr}")
