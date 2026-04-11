from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


def build_env_defaults(repo_root: Path) -> dict[str, str]:
    smoke_root = repo_root / "state" / "notebook-smoke"
    return {
        "JEMMA_WORKSPACE_DIR": str(repo_root),
        "JEMMA_DATA_DIR": str(smoke_root),
        "JEMMA_MODEL_NAME": "unsloth/gemma-4-E2B-it",
        "JEMMA_MAX_SEQ_LENGTH": "512",
        "JEMMA_SMOKE_TEST_ROWS": "8",
        "JEMMA_BATCH_SIZE": "1",
        "JEMMA_GRAD_ACC": "1",
        "JEMMA_EPOCHS": "1",
        "JEMMA_MAX_STEPS": "1",
        "JEMMA_WARMUP_STEPS": "0",
        "JEMMA_LOGGING_STEPS": "1",
        "JEMMA_SAVE_STEPS": "1000",
        "JEMMA_SAVE_TOTAL_LIMIT": "1",
        "JEMMA_GEN_MAX_NEW_TOKENS": "64",
        "JEMMA_SAVE_MERGED_16BIT": "0",
        "JEMMA_SAVE_GGUF": "0",
        "JEMMA_LORA_ALPHA": "8",
        "JEMMA_PUSH_TO_HUB": "0",
    }


def build_notebook_paths(repo_root: Path) -> dict[str, Path]:
    smoke_root = repo_root / "state" / "notebook-smoke"
    return {
        "repo_root": repo_root,
        "notebook": repo_root / "gemma4-31b-unsloth-local-5090.ipynb",
        "runner": repo_root / "toolbox" / "run_notebook_cells.py",
        "report_path": smoke_root / "notebook_run_report.json",
        "results_path": smoke_root / "notebook_execution_results.json",
        "smoke_dataset": smoke_root / "datasets" / "second-brain-train.jsonl",
    }


def _candidate_python_paths(repo_root: Path, preferred: str | os.PathLike[str] | None = None) -> list[Path]:
    candidates: list[Path | None] = [
        Path(preferred).expanduser() if preferred else None,
        Path(value).expanduser() if (value := os.environ.get("JEMMA_NOTEBOOK_PYTHON")) else None,
        Path(value).expanduser() if (value := os.environ.get("JEMMA_PYTHON_EXE")) else None,
        Path(r"d:\unsloth\studio\.venv\Scripts\python.exe"),
        repo_root / ".venv" / "Scripts" / "python.exe",
        repo_root / ".venv" / "bin" / "python",
        Path(sys.executable).resolve(),
    ]
    resolved: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)
    return resolved


def resolve_python_executable(repo_root: Path, preferred: str | os.PathLike[str] | None = None) -> Path | None:
    for candidate in _candidate_python_paths(repo_root, preferred):
        if candidate.is_file():
            return candidate
    return None


def resolve_dataset_path(repo_root: Path) -> Path:
    data_dir = Path(
        os.environ.get("JEMMA_DATA_DIR", build_env_defaults(repo_root)["JEMMA_DATA_DIR"])
    ).expanduser()
    return data_dir / "datasets" / "second-brain-train.jsonl"


def validate_dataset_file(dataset_path: Path) -> dict[str, Any]:
    rows = 0
    shapes = {"messages": 0, "conversations": 0, "prompt_response": 0}
    for line_number, raw_line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        rows += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{dataset_path} line {line_number} is not valid JSON: {exc.msg}") from exc

        if isinstance(record.get("messages"), list):
            if len(record["messages"]) < 2:
                raise ValueError(f"{dataset_path} line {line_number} must contain at least 2 message turns")
            shapes["messages"] += 1
            continue
        if isinstance(record.get("conversations"), list):
            if len(record["conversations"]) < 2:
                raise ValueError(f"{dataset_path} line {line_number} must contain at least 2 conversation turns")
            shapes["conversations"] += 1
            continue
        if "prompt" in record and "response" in record:
            shapes["prompt_response"] += 1
            continue
        raise ValueError(
            f"{dataset_path} line {line_number} must contain messages, conversations, or prompt/response fields"
        )

    if rows == 0:
        raise ValueError(f"{dataset_path} is empty")

    return {
        "path": str(dataset_path),
        "rows": rows,
        "shapes": shapes,
    }


def collect_preflight(repo_root: Path, python_executable: Path | None) -> dict[str, Any]:
    paths = build_notebook_paths(repo_root)
    dataset_path = resolve_dataset_path(repo_root)
    free_disk_gb = round(shutil.disk_usage(repo_root).free / 1024**3, 2)
    dataset_summary: dict[str, Any] | None = None
    dataset_error: str | None = None
    if dataset_path.exists():
        try:
            dataset_summary = validate_dataset_file(dataset_path)
        except ValueError as exc:
            dataset_error = str(exc)
    return {
        "python_executable": str(python_executable) if python_executable else None,
        "python_candidates": [str(item) for item in _candidate_python_paths(repo_root)],
        "notebook_exists": paths["notebook"].exists(),
        "runner_exists": paths["runner"].exists(),
        "dataset_path": str(dataset_path),
        "dataset_exists": dataset_path.exists(),
        "dataset_summary": dataset_summary,
        "dataset_error": dataset_error,
        "free_disk_gb": free_disk_gb,
        "hf_token_present": bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")),
    }


def _find_first_matching_file(path_value: Any, patterns: tuple[str, ...]) -> str | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if path.is_file():
        return str(path)
    if not path.exists():
        return None
    for pattern in patterns:
        matches = sorted(path.glob(pattern))
        if matches:
            return str(matches[0])
    return None


def build_deployment_manifest(shared_globals: dict[str, Any]) -> dict[str, Any]:
    export_dir = Path(shared_globals.get("EXPORT_DIR", Path.cwd()))
    artifact_slug = str(shared_globals.get("ARTIFACT_SLUG", "jemma-export"))
    exports = {
        "adapter_dir": str(shared_globals.get("adapter_dir")) if shared_globals.get("adapter_dir") else None,
        "merged_dir": str(shared_globals.get("merged_dir")) if shared_globals.get("merged_dir") else None,
        "gguf_dir": str(shared_globals.get("gguf_dir")) if shared_globals.get("gguf_dir") else None,
    }
    exports["gguf_file"] = _find_first_matching_file(shared_globals.get("gguf_dir"), ("*.gguf", "**/*.gguf"))
    exports["merged_model_file"] = _find_first_matching_file(
        shared_globals.get("merged_dir"),
        ("*.safetensors", "model*.bin", "**/*.safetensors", "**/model*.bin"),
    )

    return {
        "artifact_slug": artifact_slug,
        "model_name": shared_globals.get("MODEL_NAME"),
        "max_seq_length": shared_globals.get("MAX_SEQ_LENGTH"),
        "load_in_4bit": shared_globals.get("LOAD_IN_4BIT"),
        "full_finetuning": shared_globals.get("FULL_FINETUNING"),
        "dataset_source": shared_globals.get("dataset_source"),
        "output_dir": str(shared_globals.get("OUTPUT_DIR")) if shared_globals.get("OUTPUT_DIR") else None,
        "export_dir": str(export_dir),
        "exports": exports,
        "deployment_targets": {
            "ollama": {
                "recommended_model_name": artifact_slug,
                "requires": "GGUF export for the simplest Ollama import path",
            },
            "google_cloud": {
                "recommended_runtime": "Cloud Run with Ollama container for demos, or GCE/GKE when you need more control",
            },
        },
    }
