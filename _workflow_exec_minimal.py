#!/usr/bin/env python3
"""
Minimal inline workflow executor matching user constraints:
- Single script (no dependencies beyond stdlib)
- Uses subprocess.run(shell=False, cwd=...)
- Tracks files before/after
- Parses outputs
- Writes workflow_report.txt
"""
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

cwd = r'D:\JemmaRepo\Jemma'
os.chdir(cwd)

def get_files():
    files = set()
    for root, dirs, names in os.walk('.'):
        for name in names:
            fp = os.path.normpath(os.path.join(root, name))
            files.add(fp)
    return files

before = get_files()

results = {
    'timestamp': datetime.now().isoformat(),
    'repo': cwd,
    'note': 'Direct pwsh.exe unavailable; using subprocess.run(shell=False)',
    'steps': []
}

# 6 steps
steps = [
    (['python', '--version'], 'python --version'),
    (['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'], 'sys check'),
    (['python', '-m', 'pip', 'list'], 'pip list'),
    (['python', '-m', 'pip', 'install', '-e', '.'], 'pip install -e .'),
    (['python', '-m', 'pip', 'list'], 'pip list (after)'),
    (['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 'unittest'),
]

for cmd, desc in steps:
    try:
        r = subprocess.run(cmd, shell=False, cwd=cwd, capture_output=True, text=True, timeout=300)
        results['steps'].append({
            'desc': desc,
            'cmd': ' '.join(cmd),
            'code': r.returncode,
            'out': r.stdout[:2000],
            'err': r.stderr[:2000],
            'ok': r.returncode == 0
        })
    except Exception as e:
        results['steps'].append({
            'desc': desc,
            'cmd': ' '.join(cmd),
            'error': str(e),
            'ok': False
        })

# Parse packages
pkgs = {'fastapi': None, 'discord': None, 'uvicorn': None}
for s in results['steps']:
    if 'pip list' in s['desc'] and s['ok']:
        for line in s['out'].split('\n'):
            for pkg in pkgs:
                if pkg in line.lower():
                    pkgs[pkg] = line.strip()

results['packages'] = pkgs

# Parse tests
for s in results['steps']:
    if 'unittest' in s['desc']:
        out = s.get('out', '') + s.get('err', '')
        for line in out.split('\n'):
            if 'Ran' in line:
                try:
                    results['tests_ran'] = int(line.split()[1])
                except:
                    pass

after = get_files()
new_files = [f for f in (after - before) if f != '.\\_workflow_exec_minimal.py' and '.git' not in f]

# Write report
lines = [
    '=' * 80,
    'JEMMA WORKFLOW EXECUTION REPORT',
    '=' * 80,
    f'Timestamp: {results["timestamp"]}',
    f'Repository: {results["repo"]}',
    f'Note: {results["note"]}',
    '',
    'EXECUTION FORM: python -c "..." with subprocess.run(shell=False, cwd=...)',
    '',
    'STEP RESULTS:',
    '-' * 80,
]

for i, s in enumerate(results['steps'], 1):
    lines.append(f'\nStep {i}: {s["desc"]}')
    lines.append(f'Command: {s["cmd"]}')
    lines.append(f'Exit Code: {s.get("code", "ERROR")}')
    lines.append(f'Success: {s["ok"]}')
    if s.get('out'):
        lines.append(f'Output: {s["out"][:500]}')
    if s.get('err'):
        lines.append(f'Error Output: {s["err"][:500]}')

lines.append('')
lines.append('PARSED PACKAGES:')
lines.append('-' * 80)
for pkg, info in results['packages'].items():
    lines.append(f'{pkg}: {info if info else "Not found"}')

lines.append('')
lines.append('TEST SUMMARY:')
lines.append('-' * 80)
if 'tests_ran' in results:
    lines.append(f'Tests Run: {results["tests_ran"]}')
else:
    lines.append('Tests Run: Unable to parse')

lines.append('')
lines.append('FILESYSTEM CHANGES:')
lines.append('-' * 80)
lines.append(f'New files: {len(new_files)}')
if new_files:
    for f in new_files[:10]:
        lines.append(f'  {f}')

lines.append('')
lines.append('GIT STATUS:')
lines.append('-' * 80)
r = subprocess.run(['git', 'status', '--short'], shell=False, cwd=cwd, capture_output=True, text=True)
lines.append(r.stdout if r.returncode == 0 else 'Unable to get status')

lines.append('')
lines.append('=' * 80)

report = '\n'.join(lines)
with open(os.path.join(cwd, 'workflow_report.txt'), 'w') as f:
    f.write(report)

print(report)
