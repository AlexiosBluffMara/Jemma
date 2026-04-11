#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


PHASES = [
    "setup",
    "deps_check",
    "model_load",
    "lora_attach",
    "dataset_load",
    "prompt_formatting",
    "trainer_construction",
    "train_step",
    "generation",
    "export",
]


SMOKE_DATASET_ROWS = [
    {
        "messages": [
            {
                "role": "user",
                "content": "Bridge inspection note: rust on lower truss joints, missing guardrail section, and oil residue near service walkway.",
            },
            {
                "role": "assistant",
                "content": "Top risks: structural corrosion at lower truss joints, fall hazard from the missing guardrail, and slip/fire risk from oil residue. Follow-up: schedule corrosion severity assessment, isolate and repair the guardrail immediately, and clean plus trace the oil source before reopening the walkway.",
            },
        ]
    },
    {
        "prompt": "Summarize a confined-space entry checklist for a wastewater pump room with low oxygen readings and one blocked egress path.",
        "response": "Confirm atmospheric testing, ventilation, attendant coverage, rescue readiness, and restoration of a clear egress path before entry. Low oxygen and blocked exit are stop-work conditions until corrected.",
    },
]


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
    }


def ensure_smoke_dataset(repo_root: Path) -> Path:
    dataset_path = repo_root / "state" / "notebook-smoke" / "datasets" / "second-brain-train.jsonl"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    if not dataset_path.exists():
        dataset_path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in SMOKE_DATASET_ROWS),
            encoding="utf-8",
        )
    return dataset_path


def load_notebook(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_code_cells(notebook: dict):
    code_index = 0
    for cell_index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        phase = PHASES[code_index] if code_index < len(PHASES) else f"code_cell_{code_index}"
        source = "".join(cell.get("source", []))
        yield code_index, cell_index, phase, source
        code_index += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute notebook code cells in shared globals.")
    parser.add_argument("notebook", type=Path)
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("state") / "notebook-smoke" / "notebook_run_report.json",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)
    for key, value in build_env_defaults(repo_root).items():
        os.environ.setdefault(key, value)
    smoke_dataset = ensure_smoke_dataset(repo_root)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    notebook = load_notebook(args.notebook)
    shared_globals = {"__name__": "__main__", "__file__": str(args.notebook)}
    report: dict[str, object] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "notebook": str(args.notebook),
        "smoke_dataset": str(smoke_dataset),
        "env": {key: os.environ.get(key) for key in sorted(build_env_defaults(repo_root))},
        "phases": {phase: "pending" for phase in PHASES},
        "first_failure": None,
    }

    print("NOTEBOOK:", args.notebook)
    print("PYTHON:", sys.executable)
    print("ENV:", json.dumps(report["env"], indent=2))

    for code_index, cell_index, phase, source in iter_code_cells(notebook):
        print(f"\n=== CODE CELL {code_index} (notebook cell {cell_index}) :: {phase} ===")
        report["phases"][phase] = "running"
        try:
            exec(compile(source, f"{args.notebook}::cell_{cell_index}", "exec"), shared_globals)
            report["phases"][phase] = "ok"
        except Exception:
            tb = traceback.format_exc()
            report["phases"][phase] = "failed"
            report["first_failure"] = {
                "phase": phase,
                "code_cell_index": code_index,
                "notebook_cell_index": cell_index,
                "traceback": tb,
            }
            print(tb)
            args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 1

    args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nAll notebook code cells executed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
