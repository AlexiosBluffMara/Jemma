"""Launch the Unsloth training pipeline with the construction cracks dataset.

This script sets up environment variables and runs the notebook cell runner.
Output is written to state/training_output.log and results to state/training_result.json.
"""
import subprocess, os, sys, json, time
from pathlib import Path

REPO = Path(r"D:\JemmaRepo\Jemma")
VENV_PYTHON = r"D:\unsloth\studio\.venv\Scripts\python.exe"
LOG_FILE = REPO / "state" / "training_output.log"
RESULT_FILE = REPO / "state" / "training_result.json"

# Ensure state dir exists
(REPO / "state").mkdir(exist_ok=True)

env = os.environ.copy()
env.update({
    "JEMMA_DATA_DIR": str(REPO),
    "JEMMA_WORKSPACE_DIR": str(REPO),
    "JEMMA_MODEL_NAME": "unsloth/gemma-4-E4B-it",
    "JEMMA_MAX_SEQ_LENGTH": "4096",
    "JEMMA_BATCH_SIZE": "2",
    "JEMMA_GRAD_ACC": "4",
    "JEMMA_LR": "2e-4",
    "JEMMA_EPOCHS": "3",
    "JEMMA_MAX_STEPS": os.environ.get("JEMMA_MAX_STEPS", "-1"),
    "JEMMA_WARMUP_STEPS": "5",
    "JEMMA_LOGGING_STEPS": "5",
    "JEMMA_SAVE_STEPS": "50",
    "JEMMA_SAVE_TOTAL_LIMIT": "2",
    "JEMMA_SAVE_GGUF": "1",
    "JEMMA_SAVE_MERGED_16BIT": "0",
    "JEMMA_NOTEBOOK_PYTHON": VENV_PYTHON,
    "JEMMA_NOTEBOOK_TIMEOUT_S": "7200",
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    "TOKENIZERS_PARALLELISM": "false",
    "JEMMA_LOAD_IN_4BIT": "1",
    "JEMMA_FULL_FINETUNING": "0",
    "JEMMA_LORA_R": "8",
    "JEMMA_LORA_ALPHA": "16",
    "JEMMA_GEN_MAX_NEW_TOKENS": "256",
    "JEMMA_SMOKE_TEST_ROWS": "75",
})

print(f"=== Jemma Training Pipeline ===")
print(f"Python: {VENV_PYTHON}")
print(f"Model: {env['JEMMA_MODEL_NAME']}")
print(f"Dataset: {REPO / 'datasets' / 'second-brain-train.jsonl'}")
print(f"Max steps: {env['JEMMA_MAX_STEPS']}")
print(f"Log: {LOG_FILE}")
print()

start = time.time()

with open(LOG_FILE, "w", encoding="utf-8") as log:
    log.write(f"Training started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log.write(f"Model: {env['JEMMA_MODEL_NAME']}\n")
    log.write(f"Max steps: {env['JEMMA_MAX_STEPS']}\n\n")
    log.flush()

    proc = subprocess.Popen(
        [VENV_PYTHON, str(REPO / "toolbox" / "run_notebook_cells.py"),
         str(REPO / "gemma4-31b-unsloth-local-5090.ipynb")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(REPO),
        text=True,
        bufsize=1,
    )

    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        log.write(line)
        log.flush()

    proc.wait()

elapsed = time.time() - start

result = {
    "exit_code": proc.returncode,
    "elapsed_seconds": elapsed,
    "elapsed_minutes": elapsed / 60,
    "max_steps": env["JEMMA_MAX_STEPS"],
    "model": env["JEMMA_MODEL_NAME"],
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
}

# Check for the notebook report
report_file = REPO / "state" / "notebook-smoke" / "notebook_run_report.json"
if report_file.exists():
    with open(report_file) as f:
        result["notebook_report"] = json.load(f)

with open(RESULT_FILE, "w") as f:
    json.dump(result, f, indent=2)

print(f"\n=== Pipeline finished in {elapsed:.0f}s ({elapsed/60:.1f}m) ===")
print(f"Exit code: {proc.returncode}")
print(f"Result: {RESULT_FILE}")

sys.exit(proc.returncode)
