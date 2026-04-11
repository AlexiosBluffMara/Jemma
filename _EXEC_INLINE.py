import subprocess
import os
import sys
from datetime import datetime

# Change to repo directory
os.chdir(r'D:\JemmaRepo\Jemma')
cwd = os.getcwd()

# Snapshot filesystem
def snap():
    s = set()
    for r, d, f in os.walk('.'):
        for fn in f:
            s.add(os.path.normpath(os.path.join(r, fn)))
    return s

before = snap()

# Results dict
res = {'ts': datetime.now().isoformat(), 'cwd': cwd, 'steps': []}

# 6 subprocess.run steps
cmds = [
    (['python', '--version'], 'python --version'),
    (['python', '-c', 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'], 'python -c version'),
    (['python', '-m', 'pip', 'list'], 'pip list'),
    (['python', '-m', 'pip', 'install', '-e', '.'], 'pip install'),
    (['python', '-m', 'pip', 'list'], 'pip list after'),
    (['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 'unittest'),
]

for cmd, desc in cmds:
    try:
        r = subprocess.run(cmd, shell=False, cwd=cwd, capture_output=True, text=True, timeout=300)
        res['steps'].append({'d': desc, 'c': ' '.join(cmd), 'x': r.returncode, 'o': r.stdout[:1500], 'e': r.stderr[:1500]})
    except Exception as ex:
        res['steps'].append({'d': desc, 'c': ' '.join(cmd), 'err': str(ex)})

# Parse packages
pkg = {'fastapi': None, 'discord': None, 'uvicorn': None}
for s in res['steps']:
    if 'pip list' in s.get('d', '') and 'x' in s and s['x'] == 0:
        for ln in s['o'].split('\n'):
            for p in pkg:
                if p.lower() in ln.lower():
                    pkg[p] = ln.strip()
res['pkg'] = pkg

# Parse unittest
tests = 0
for s in res['steps']:
    if 'unittest' in s.get('d', ''):
        for ln in (s.get('o', '') + s.get('e', '')).split('\n'):
            if 'Ran' in ln and 'test' in ln:
                try:
                    tests = int(ln.split()[1])
                except:
                    pass
res['tests'] = tests

after = snap()
nf = sorted([f for f in (after - before) if '.\\_minimal' not in f and '.git' not in f])

# Report
lines = [
    '=' * 80,
    'JEMMA WORKFLOW EXECUTION REPORT',
    '=' * 80,
    f'Timestamp: {res["ts"]}',
    f'Repository: {res["cwd"]}',
    f'Execution Method: subprocess.run(shell=False) in python -c inline code',
    f'Note: pwsh.exe unavailable; executed as python code snippet',
    '',
    'STEP RESULTS:',
    '-' * 80,
]

for i, s in enumerate(res['steps'], 1):
    lines.append(f'\nStep {i}: {s.get("d")}')
    lines.append(f'Command: {s.get("c")}')
    if 'err' in s:
        lines.append(f'Exception: {s["err"]}')
    else:
        lines.append(f'Exit Code: {s.get("x")}')
        if s.get('o'):
            lines.append(f'Output: {s["o"][:800]}')
        if s.get('e'):
            lines.append(f'Error: {s["e"][:800]}')

lines.append('')
lines.append('PARSED PACKAGES (fastapi/discord/uvicorn):')
lines.append('-' * 80)
for p, i in res['pkg'].items():
    lines.append(f'{p}: {i if i else "Not found"}')

lines.append('')
lines.append('UNITTEST SUMMARY:')
lines.append('-' * 80)
lines.append(f'Tests discovered/run: {res["tests"]}')

lines.append('')
lines.append('FILESYSTEM CHANGES:')
lines.append('-' * 80)
lines.append(f'New files created: {len(nf)}')
if nf:
    for f in nf[:5]:
        lines.append(f'  {f}')

lines.append('')
lines.append('FINAL GIT STATUS:')
lines.append('-' * 80)
gr = subprocess.run(['git', 'status', '--short'], shell=False, cwd=cwd, capture_output=True, text=True)
lines.append(gr.stdout if gr.returncode == 0 else '(git status unavailable)')

lines.append('')
lines.append('=' * 80)

report = '\n'.join(lines)
with open(os.path.join(cwd, 'workflow_report.txt'), 'w') as f:
    f.write(report)

print(report)
sys.exit(0)
