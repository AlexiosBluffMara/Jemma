#!/usr/bin/env python3
import subprocess, os, sys, json
from datetime import datetime

os.chdir(r'D:\JemmaRepo\Jemma')
cwd = os.getcwd()
print(f"Working in: {cwd}")

# Snapshot before
before = {os.path.normpath(os.path.join(r,f)) for r,d,fs in os.walk('.') for f in fs}

res = {'ts': datetime.now().isoformat(), 'cwd': cwd, 'steps': [], 'note': 'pwsh unavailable - direct Python execution via subprocess.run()'}

# 6 steps
cmds = [
    (['python', '--version'], 'python --version'),
    (['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'], 'sys check'),
    (['python', '-m', 'pip', 'list'], 'pip list'),
    (['python', '-m', 'pip', 'install', '-e', '.'], 'pip install -e .'),
    (['python', '-m', 'pip', 'list'], 'pip list after'),
    (['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 'unittest'),
]

for cmd, desc in cmds:
    print(f"\n>>> Executing: {desc}")
    try:
        r = subprocess.run(cmd, shell=False, cwd=cwd, capture_output=True, text=True, timeout=300)
        step = {'desc': desc, 'cmd': ' '.join(cmd), 'code': r.returncode, 'ok': r.returncode == 0}
        if r.stdout: step['out'] = r.stdout[:2000]
        if r.stderr: step['err'] = r.stderr[:2000]
        res['steps'].append(step)
        print(f"Exit code: {r.returncode}")
    except subprocess.TimeoutExpired:
        res['steps'].append({'desc': desc, 'cmd': ' '.join(cmd), 'error': 'TIMEOUT'})
        print("TIMEOUT")
    except Exception as e:
        res['steps'].append({'desc': desc, 'cmd': ' '.join(cmd), 'error': str(e)})
        print(f"ERROR: {e}")

# Parse packages
pkgs = {'fastapi': None, 'discord': None, 'uvicorn': None}
for s in res['steps']:
    if 'pip list' in s.get('desc', '') and s.get('ok'):
        for line in s.get('out', '').split('\n'):
            for pkg in pkgs:
                if pkg.lower() in line.lower():
                    pkgs[pkg] = line.strip()
res['packages'] = pkgs

# Parse tests
for s in res['steps']:
    if 'unittest' in s.get('desc', ''):
        out = s.get('out', '') + s.get('err', '')
        for line in out.split('\n'):
            if 'Ran' in line:
                try:
                    res['tests_ran'] = int(line.split()[1])
                except: pass
if 'tests_ran' not in res: res['tests_ran'] = 0

# Filesystem after
after = {os.path.normpath(os.path.join(r,f)) for r,d,fs in os.walk('.') for f in fs}
new = sorted([f for f in (after - before) if '.git' not in f])
res['new_files'] = new[:10]

# Report
lines = [
    '='*80,
    'JEMMA WORKFLOW EXECUTION REPORT',
    '='*80,
    f'Timestamp: {res["ts"]}',
    f'Repository: {res["cwd"]}',
    f'Execution Method: subprocess.run(shell=False, cwd=...) in Python',
    f'Note: {res["note"]}',
    '',
    'STEP RESULTS:',
    '-'*80,
]

for i, s in enumerate(res['steps'], 1):
    lines.append(f'\nStep {i}: {s.get("desc")}')
    lines.append(f'Command: {s.get("cmd")}')
    if 'error' in s:
        lines.append(f'Error: {s["error"]}')
    else:
        lines.append(f'Exit Code: {s.get("code")}')
        if s.get('out'): lines.append(f'Output:\n{s["out"][:500]}')
        if s.get('err'): lines.append(f'Errors:\n{s["err"][:500]}')

lines.append('')
lines.append('PARSED PACKAGES:')
lines.append('-'*80)
for p, v in res['packages'].items():
    lines.append(f'{p}: {v if v else "Not found"}')

lines.append('')
lines.append('UNITTEST SUMMARY:')
lines.append('-'*80)
lines.append(f'Tests Run: {res.get("tests_ran", 0)}')

lines.append('')
lines.append('FILESYSTEM:')
lines.append('-'*80)
lines.append(f'New files: {len(new)}')
for f in res['new_files'][:5]:
    lines.append(f'  {f}')

lines.append('')
lines.append('GIT STATUS:')
lines.append('-'*80)
gr = subprocess.run(['git', 'status', '--short'], shell=False, cwd=cwd, capture_output=True, text=True)
lines.append(gr.stdout if gr.returncode == 0 else '(unavailable)')

lines.append('')
lines.append('='*80)

report = '\n'.join(lines)
with open(os.path.join(cwd, 'workflow_report.txt'), 'w') as f:
    f.write(report)

print('\n' + report)
print(f'\nReport saved to: {os.path.join(cwd, "workflow_report.txt")}')
