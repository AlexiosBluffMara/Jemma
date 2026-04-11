#!/usr/bin/env python3
import subprocess
import sys

# Run the exec_workflow.py script
result = subprocess.run([sys.executable, 'exec_workflow.py'], cwd=r'D:\JemmaRepo\Jemma')
sys.exit(result.returncode)
