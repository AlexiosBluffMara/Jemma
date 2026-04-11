#!/usr/bin/env python3
import subprocess, json, sys, os
os.chdir(r"D:\JemmaRepo\Jemma")
R = {}
for i, cmd in enumerate([
    ['python', '--version'],
    ['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'],
    ['python', '-m', 'pip', 'list'],
    ['python', '-m', 'pip', 'install', '-e', '.'],
    ['python', '-m', 'pip', 'list'],
    ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
], 1):
    k = f"s{i}" if i!=4 else "supp"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        R[k]={'cmd': ' '.join(cmd), 'out': r.stdout, 'err': r.stderr, 'rc': r.returncode}
        print(f"{k}: rc={r.returncode}")
    except Exception as e:
        R[k]={'cmd': ' '.join(cmd), 'out': '', 'err': str(e), 'rc': -1}
        print(f"{k}: ERROR {e}")
print(json.dumps(R, indent=2))
