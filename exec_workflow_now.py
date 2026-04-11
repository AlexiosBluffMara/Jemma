#!/usr/bin/env python3
"""
Minimal inline workflow executor - executes all steps in sequence.
"""
import subprocess
import os
import sys

def run_command(cmd_list, cwd=None, timeout=300):
    """Run a command and return stdout, stderr, and exit code"""
    try:
        result = subprocess.run(
            cmd_list,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"TIMEOUT after {timeout}s", -1
    except Exception as e:
        return "", str(e), -1

def main():
    repo = r"D:\JemmaRepo\Jemma"
    os.chdir(repo)
    
    print("=" * 80)
    print("EXECUTING JEMMA WORKFLOW")
    print("=" * 80)
    
    commands = [
        ("Python Version", ["python", "--version"], 30),
        ("Interpreter Info", ["python", "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"], 30),
        ("Pip List (Before)", ["python", "-m", "pip", "list"], 60),
        ("Install Dependencies", ["python", "-m", "pip", "install", "-e", "."], 300),
        ("Pip List (After)", ["python", "-m", "pip", "list"], 60),
        ("Run Tests", ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], 300),
    ]
    
    results = []
    for name, cmd, timeout in commands:
        print(f"\n{'='*80}")
        print(f"STEP: {name}")
        print(f"Command: {' '.join(cmd)}")
        print(f"{'='*80}")
        
        stdout, stderr, code = run_command(cmd, cwd=repo, timeout=timeout)
        
        print(f"Exit Code: {code}")
        print(f"\n--- STDOUT ---")
        print(stdout[:2000] if stdout else "(empty)")
        
        if stderr:
            print(f"\n--- STDERR ---")
            print(stderr[:2000])
        
        results.append({
            "name": name,
            "cmd": cmd,
            "code": code,
            "stdout": stdout,
            "stderr": stderr
        })
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for i, r in enumerate(results, 1):
        print(f"Step {i}: {r['name']} -> Exit Code {r['code']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
