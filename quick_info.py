import subprocess
import os

os.chdir('d:\\JemmaRepo\\Jemma')

commands = [
    ('cmd.exe /d /c "wmic cpu get Name /value"', 'CPU Info'),
    ('cmd.exe /d /c "fsutil volume diskfree c:"', 'C: Drive Space'),
    ('cmd.exe /d /c "fsutil volume diskfree d:"', 'D: Drive Space'),
]

for cmd, desc in commands:
    print(f"\n>>> {desc}")
    print(f">>> {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Exit: {r.returncode}")
    print(r.stdout)
    if r.stderr:
        print(f"STDERR: {r.stderr}")
