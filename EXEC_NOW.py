exec("""
import subprocess
import os
from datetime import datetime

os.chdir(r'D:\\JemmaRepo\\Jemma')
cwd = os.getcwd()

# Before snapshot
before = {os.path.normpath(os.path.join(r,f)) for r,d,fs in os.walk('.') for f in fs}

res = {'ts': datetime.now().isoformat(), 'cwd': cwd, 'steps': []}

# 6 steps
for cmd, desc in [
    (['python', '--version'], 'python --version'),
    (['python', '-c', 'import sys; print("Executable:", sys.executable)'], 'sys check'),
    (['python', '-m', 'pip', 'list'], 'pip list'),
    (['python', '-m', 'pip', 'install', '-e', '.'], 'pip install'),
    (['python', '-m', 'pip', 'list'], 'pip list 2'),
    (['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 'unittest'),
]:
    try:
        r = subprocess.run(cmd, shell=False, cwd=cwd, capture_output=True, text=True, timeout=300)
        s = {'d': desc, 'c': ' '.join(cmd), 'x': r.returncode, 'o': r.stdout[:1500], 'e': r.stderr[:1500]}
    except Exception as ex:
        s = {'d': desc, 'c': ' '.join(cmd), 'ex': str(ex)}
    res['steps'].append(s)

# Packages
pkg = {'fastapi': None, 'discord': None, 'uvicorn': None}
for s in res['steps']:
    if 'pip list' in s.get('d', '') and 'x' in s and s['x'] == 0:
        for ln in s['o'].split('\\n'):
            for p in pkg:
                if p.lower() in ln.lower():
                    pkg[p] = ln.strip()
res['pkg'] = pkg

# Tests
for s in res['steps']:
    if 'unittest' in s.get('d', ''):
        for ln in (s.get('o', '') + s.get('e', '')).split('\\n'):
            if 'Ran' in ln:
                try:
                    res['tests'] = int(ln.split()[1])
                except: pass

after = {os.path.normpath(os.path.join(r,f)) for r,d,fs in os.walk('.') for f in fs}
nf = sorted([f for f in (after - before) if '.git' not in f])[:10]

# Report
lines = [
    '='*80,
    'JEMMA WORKFLOW EXECUTION REPORT',
    '='*80,
    f'Timestamp: {res["ts"]}',
    f'Repository: {res["cwd"]}',
    f'Method: subprocess.run(shell=False) via exec()',
    '',
]

for i, s in enumerate(res['steps'], 1):
    lines.append(f'Step {i}: {s.get("d")}')
    lines.append(f'Cmd: {s.get("c")}')
    if 'ex' in s:
        lines.append(f'Error: {s["ex"]}')
    else:
        lines.append(f'Exit: {s.get("x")} | Output: {s.get("o", "")[:300]}')

lines.append('')
lines.append('Packages: ')
for p, i in res.get('pkg', {}).items():
    lines.append(f'  {p}: {i if i else "Not found"}')

lines.append(f'Tests: {res.get("tests", 0)}')
lines.append(f'New files: {len(nf)}')

gr = subprocess.run(['git', 'status', '--short'], shell=False, cwd=cwd, capture_output=True, text=True)
lines.append('')
lines.append('Git Status:')
lines.append(gr.stdout if gr.returncode == 0 else '(unavailable)')
lines.append('='*80)

report = '\\n'.join(lines)
with open(os.path.join(cwd, 'workflow_report.txt'), 'w') as f:
    f.write(report)
print(report)
""")
