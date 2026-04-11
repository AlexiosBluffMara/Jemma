"""Auto-executing module - runs workflow on import."""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

os.chdir(r'd:\JemmaRepo\Jemma')
repo_dir = Path.cwd()

# Auto-run on import
print("MODULE AUTO-EXEC: Starting workflow...", flush=True)

# Cleanup
FILES_TO_REMOVE = {
    'run_workflow_now.py', 'run_workflow_now.bat', 'START_EXECUTION.txt',
    'workflow_execution_guide.txt', 'WORKFLOW_INDEX.txt', 
    'environment_adaptation_report.txt', 'EXECUTION_READY.txt',
    '__temp_workflow_exec__.py', 'run_temp_workflow.bat', 'exec_workflow_inline.py',
    'run_workflow_exec.py', 'RUN.py', 'EXEC_NOW.cmd', 'run.cmd', '_execute_workflow.py',
    '_workflow_executor_self_contained.py', 'EXECUTE.py', 'run_auto_exec.py'
}

removed = []
for fname in FILES_TO_REMOVE:
    fpath = repo_dir / fname
    if fpath.exists():
        try:
            os.remove(fpath)
            removed.append(fname)
        except:
            pass

report = []
report.append("=" * 70)
report.append("JEMMA WORKFLOW EXECUTION REPORT (AUTO-EXECUTED ON IMPORT)")
report.append("=" * 70)
report.append(f"Timestamp: {datetime.now().isoformat()}")
report.append(f"Repository: {repo_dir}")
report.append(f"Python: {sys.executable}")
report.append(f"Cleaned up {len(removed)} files")
report.append("")

# STEP 1
report.append("STEP 1: python --version")
report.append("-" * 70)
try:
    r = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, shell=False)
    report.append(f"Exit Code: {r.returncode}")
    report.append(f"Output: {r.stdout.strip()}")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# STEP 2
report.append("STEP 2: Interpreter Info")
report.append("-" * 70)
try:
    code = 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, shell=False)
    report.append(f"Exit Code: {r.returncode}")
    report.append(r.stdout)
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# STEP 3
report.append("STEP 3: pip list (BEFORE)")
report.append("-" * 70)
before = {}
try:
    r = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False, timeout=60)
    report.append(f"Exit Code: {r.returncode}")
    for line in r.stdout.split('\n')[2:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                before[parts[0].lower()] = parts[1]
                if any(x in parts[0].lower() for x in ['fastapi', 'discord', 'uvicorn']):
                    report.append(f"  {parts[0]}=={parts[1]}")
    report.append(f"Total: {len(before)}")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# STEP 4
report.append("STEP 4: pip install -e .")
report.append("-" * 70)
try:
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                       capture_output=True, text=True, shell=False, timeout=300, cwd=str(repo_dir))
    report.append(f"Exit Code: {r.returncode}")
    report.append("Status: SUCCESS" if r.returncode == 0 else "Status: FAILED")
    if r.returncode != 0:
        for line in r.stderr.split('\n')[-15:]:
            if line.strip():
                report.append(f"  {line}")
except subprocess.TimeoutExpired:
    report.append("ERROR: Timeout")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# STEP 5
report.append("STEP 5: pip list (AFTER)")
report.append("-" * 70)
after = {}
try:
    r = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False, timeout=60)
    report.append(f"Exit Code: {r.returncode}")
    for line in r.stdout.split('\n')[2:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                after[parts[0].lower()] = parts[1]
                if any(x in parts[0].lower() for x in ['fastapi', 'discord', 'uvicorn']):
                    report.append(f"  {parts[0]}=={parts[1]}")
    report.append(f"Total: {len(after)}")
    new = set(after.keys()) - set(before.keys())
    if new:
        report.append(f"Newly installed: {len(new)}")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# STEP 6
report.append("STEP 6: unittest discover")
report.append("-" * 70)
try:
    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                       capture_output=True, text=True, shell=False, timeout=120, cwd=str(repo_dir))
    report.append(f"Exit Code: {r.returncode}")
    
    out = r.stdout + r.stderr
    t, p, f, e = 0, 0, 0, 0
    for line in out.split('\n'):
        if ' ... ok' in line:
            t += 1
            p += 1
        elif ' ... FAIL' in line:
            t += 1
            f += 1
        elif ' ... ERROR' in line:
            t += 1
            e += 1
    
    for line in out.split('\n'):
        if 'Ran' in line or 'OK' in line or 'FAILED' in line:
            report.append(f"  {line.strip()}")
    
    report.append(f"Tests: total={t}, pass={p}, fail={f}, error={e}")
except subprocess.TimeoutExpired:
    report.append("ERROR: Timeout")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# Git status
report.append("GIT STATUS")
report.append("-" * 70)
try:
    r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, shell=False, cwd=str(repo_dir))
    lines = [l for l in r.stdout.split('\n') if l.strip()]
    tracked = [l for l in lines if l.startswith(('M ', 'D ', 'A '))]
    report.append(f"Tracked changes: {len(tracked)}")
    for line in tracked[:10]:
        report.append(f"  {line}")
except Exception as e:
    report.append(f"ERROR: {e}")
report.append("")

# Verification
remaining = [f for f in FILES_TO_REMOVE if (repo_dir / f).exists()]
report.append("CLEANUP VERIFICATION: " + ("✓ Clean" if not remaining else f"✗ Remaining: {remaining}"))
report.append("")
report.append("=" * 70)
report.append("END OF REPORT")
report.append("=" * 70)

# Write
with open('workflow_report.txt', 'w') as f:
    f.write('\n'.join(report))

print("MODULE AUTO-EXEC: Report written to workflow_report.txt", flush=True)

# Cleanup self
for f in ['run_auto_exec.py', '__auto_exec__.py']:
    try:
        os.remove(repo_dir / f)
    except:
        pass
