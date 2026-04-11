import subprocess
import sys

# Just run the Python workflow executor
result = subprocess.run([sys.executable, r"D:\JemmaRepo\Jemma\run_full_workflow.py"], cwd=r"D:\JemmaRepo\Jemma")
sys.exit(result.returncode)
