"""Training API endpoints.

These endpoints provide a web-based interface to monitor and control
Unsloth QLoRA / LoRA fine-tuning. The actual training runs in a
subprocess via the notebook or a dedicated script; these endpoints
expose the status and allow start/stop control.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["training"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TrainingRequestBody(BaseModel):
    base_model: str = "gemma4:latest"
    dataset_path: str = "datasets/prompts/safety-benchmark.jsonl"
    method: Literal["qlora", "lora"] = "qlora"
    max_steps: int = Field(default=200, ge=1)
    learning_rate: float = Field(default=2e-4, gt=0)
    lora_rank: int = Field(default=32, ge=1)
    lora_alpha: int = Field(default=8, ge=1)
    batch_size: int = Field(default=2, ge=1)
    max_seq_length: int = Field(default=8192, ge=128)
    output_name: str = "jemma-safety-e4b"


class TrainingStatusResponse(BaseModel):
    active: bool
    job_id: str | None = None
    model: str = ""
    method: str = ""
    current_step: int = 0
    total_steps: int = 0
    loss: float | None = None
    learning_rate: float | None = None
    elapsed_s: float | None = None
    eta_s: float | None = None
    logs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-process training state (singleton)
# ---------------------------------------------------------------------------

@dataclass
class _TrainingState:
    active: bool = False
    job_id: str | None = None
    model: str = ""
    method: str = ""
    current_step: int = 0
    total_steps: int = 0
    loss: float | None = None
    learning_rate: float | None = None
    start_time: float | None = None
    logs: list[str] = field(default_factory=list)
    process: subprocess.Popen[str] | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


_state = _TrainingState()
_MAX_LOG_LINES = 500


def _to_response() -> TrainingStatusResponse:
    elapsed = time.time() - _state.start_time if _state.start_time else None
    eta = None
    if elapsed and _state.current_step > 0 and _state.total_steps > 0:
        remaining = _state.total_steps - _state.current_step
        eta = (elapsed / _state.current_step) * remaining
    return TrainingStatusResponse(
        active=_state.active,
        job_id=_state.job_id,
        model=_state.model,
        method=_state.method,
        current_step=_state.current_step,
        total_steps=_state.total_steps,
        loss=_state.loss,
        learning_rate=_state.learning_rate,
        elapsed_s=round(elapsed, 1) if elapsed else None,
        eta_s=round(eta, 1) if eta else None,
        logs=_state.logs[-_MAX_LOG_LINES:],
    )


def _run_training(config: dict[str, Any], repo_root: Path) -> None:
    """Background thread that runs the training script as a subprocess."""
    import uuid

    with _state.lock:
        _state.active = True
        _state.job_id = f"train-{uuid.uuid4().hex[:8]}"
        _state.model = config["base_model"]
        _state.method = config["method"]
        _state.current_step = 0
        _state.total_steps = config["max_steps"]
        _state.loss = None
        _state.learning_rate = None
        _state.start_time = time.time()
        _state.logs = [f"[{_state.job_id}] Starting {config['method']} training on {config['base_model']}"]

    # Build the training command as a Python script invocation
    script = repo_root / "scripts" / "run_training.py"
    if not script.exists():
        # If the dedicated script doesn't exist, log and exit
        with _state.lock:
            _state.logs.append(f"Training script not found at {script}")
            _state.logs.append("Use the Unsloth notebook for interactive training:")
            _state.logs.append("  gemma4-31b-unsloth-local-5090.ipynb")
            _state.active = False
        return

    cmd = [
        sys.executable, str(script),
        "--base-model", config["base_model"],
        "--dataset", config["dataset_path"],
        "--method", config["method"],
        "--max-steps", str(config["max_steps"]),
        "--lr", str(config["learning_rate"]),
        "--lora-rank", str(config["lora_rank"]),
        "--lora-alpha", str(config["lora_alpha"]),
        "--batch-size", str(config["batch_size"]),
        "--max-seq-length", str(config["max_seq_length"]),
        "--output-name", config["output_name"],
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(repo_root),
            bufsize=1,
        )
        with _state.lock:
            _state.process = proc

        for line in iter(proc.stdout.readline, ""):  # type: ignore[union-attr]
            line = line.rstrip()
            if not line:
                continue
            with _state.lock:
                _state.logs.append(line)
                # Try to parse structured output: {"step": N, "loss": X, "lr": Y}
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        if "step" in data:
                            _state.current_step = data["step"]
                        if "loss" in data:
                            _state.loss = data["loss"]
                        if "lr" in data:
                            _state.learning_rate = data["lr"]
                    except json.JSONDecodeError:
                        pass

        proc.wait()
        with _state.lock:
            exit_code = proc.returncode
            _state.logs.append(f"Training finished with exit code {exit_code}")
            _state.active = False
            _state.process = None

    except Exception as exc:
        with _state.lock:
            _state.logs.append(f"Training error: {exc}")
            _state.active = False
            _state.process = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/training/status", response_model=TrainingStatusResponse)
def training_status() -> TrainingStatusResponse:
    return _to_response()


@router.post("/training/start")
def training_start(request: Request, body: TrainingRequestBody) -> dict[str, str]:
    if _state.active:
        raise HTTPException(status_code=409, detail="Training already in progress")

    repo_root = Path(request.app.state.config.repo_root) if hasattr(request.app.state.config, "repo_root") else Path(__file__).resolve().parents[4]

    config = body.model_dump()
    thread = threading.Thread(target=_run_training, args=(config, repo_root), daemon=True)
    thread.start()

    # Wait briefly so the job_id is set
    time.sleep(0.3)
    return {"job_id": _state.job_id or "starting"}


@router.post("/training/stop")
def training_stop() -> dict[str, bool]:
    with _state.lock:
        if _state.process and _state.active:
            _state.process.terminate()
            _state.logs.append("Training stop requested")
            _state.active = False
            return {"stopped": True}
    return {"stopped": False}
