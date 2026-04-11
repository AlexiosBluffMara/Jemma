"""Fire-and-forget launcher for the training pipeline."""
import subprocess, os, sys
from pathlib import Path

REPO = Path(r"D:\JemmaRepo\Jemma")
VENV_PYTHON = r"D:\unsloth\studio\.venv\Scripts\python.exe"

env = os.environ.copy()
# Inherit JEMMA_MAX_STEPS from environment or default to -1 (full run)
if "JEMMA_MAX_STEPS" not in env:
    env["JEMMA_MAX_STEPS"] = "-1"

log_file = REPO / "state" / "training_output.log"

with open(log_file, "w") as lf:
    proc = subprocess.Popen(
        [VENV_PYTHON, str(REPO / "state" / "launch_training.py")],
        stdout=lf,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(REPO),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )

print(f"PID={proc.pid}")
print(f"LOG={log_file}")
