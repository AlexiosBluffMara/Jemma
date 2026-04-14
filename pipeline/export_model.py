#!/usr/bin/env python3
"""
Jemma Model Export — GGUF conversion + Ollama registration.

Exports the final merged checkpoint to GGUF quantized formats and
registers with the local Ollama instance.

Usage:
  python pipeline/export_model.py                        # Export best checkpoint
  python pipeline/export_model.py --stage 2              # Export specific stage
  python pipeline/export_model.py --quants q4_k_m q8_0   # Choose quant levels
  python pipeline/export_model.py --skip-ollama           # GGUF only, no Ollama
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINTS_DIR = ROOT / "checkpoints"
GGUF_DIR = ROOT / "exports" / "gguf"
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"

for d in [GGUF_DIR, LOGS_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("export_model")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
log.addHandler(_sh)

# Ollama config
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL_PREFIX = "jemma-safebrain"

SUPPORTED_QUANTS = ["q4_k_m", "q8_0", "f16"]


def find_best_checkpoint(stage: int | None = None) -> Path | None:
    """Find the best available merged checkpoint."""
    if stage:
        cp = CHECKPOINTS_DIR / f"stage{stage}_{_stage_name(stage)}"
        if cp.exists():
            return cp
        # Try DPO checkpoint
        cp = CHECKPOINTS_DIR / f"stage{stage}_dpo"
        if cp.exists():
            return cp

    # Search backwards: DPO → Safety → Tool → Domain → General
    for name in ["stage4_dpo", "stage5_safety_sft", "stage3_toolcall_sft",
                  "stage2_domain_sft", "stage1_general_sft"]:
        cp = CHECKPOINTS_DIR / name
        if cp.exists():
            return cp
    return None


def _stage_name(stage: int) -> str:
    names = {1: "general_sft", 2: "domain_sft", 3: "toolcall_sft",
             4: "dpo", 5: "safety_sft"}
    return names.get(stage, f"stage{stage}")


def export_gguf(checkpoint_path: Path, quants: list[str]) -> dict[str, Path]:
    """Export checkpoint to GGUF format using Unsloth."""
    log.info(f"╔══════════════════════════════════════════════╗")
    log.info(f"║  GGUF Export                                  ║")
    log.info(f"╚══════════════════════════════════════════════╝")
    log.info(f"  Source checkpoint: {checkpoint_path}")
    log.info(f"  Target quants: {quants}")

    from unsloth import FastModel

    model, tokenizer = FastModel.from_pretrained(
        str(checkpoint_path),
        dtype=None,
        load_in_4bit=False,  # Need full precision for GGUF export
    )

    exported: dict[str, Path] = {}
    for quant in quants:
        tag = f"{OLLAMA_MODEL_PREFIX}-e4b-{quant}"
        out_dir = GGUF_DIR / tag
        out_dir.mkdir(parents=True, exist_ok=True)

        log.info(f"  Exporting {quant}...")
        t0 = time.perf_counter()

        model.save_pretrained_gguf(
            str(out_dir),
            tokenizer,
            quantization_method=quant,
        )

        elapsed = time.perf_counter() - t0
        # Find the .gguf file
        gguf_files = list(out_dir.glob("*.gguf"))
        if gguf_files:
            size_mb = gguf_files[0].stat().st_size / (1024 * 1024)
            log.info(f"  ✓ {quant}: {gguf_files[0].name} ({size_mb:.0f} MB, {elapsed:.0f}s)")
            exported[quant] = gguf_files[0]
        else:
            log.warning(f"  ✗ {quant}: No .gguf file produced")

    return exported


def create_modelfile(gguf_path: Path, quant: str) -> Path:
    """Create an Ollama Modelfile for the exported GGUF."""
    modelfile = gguf_path.parent / "Modelfile"
    content = f"""# Jemma SafeBrain — Gemma 4 E4B fine-tuned ({quant})
FROM ./{gguf_path.name}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 2048
PARAMETER stop <|turn>

TEMPLATE \"\"\"{{{{- range .Messages }}}}
<|turn>{{{{ .Role }}}}
{{{{ .Content }}}}{{{{- end }}}}
<|turn>model
\"\"\"

SYSTEM \"\"\"You are Jemma SafeBrain, a local AI safety assistant specializing in construction safety, civic services, emergency response, and building code compliance. You provide accurate, actionable safety guidance while refusing harmful requests. You can call tools when needed for real-world actions.\"\"\"
"""
    modelfile.write_text(content, "utf-8")
    log.info(f"  Modelfile created: {modelfile}")
    return modelfile


def register_ollama(gguf_path: Path, quant: str) -> bool:
    """Register the GGUF model with local Ollama."""
    import urllib.request
    import urllib.error

    # Check Ollama is running
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                log.error("Ollama not responding")
                return False
    except (urllib.error.URLError, OSError):
        log.error(f"Ollama not running at {OLLAMA_BASE_URL}")
        return False

    # Create Modelfile
    modelfile = create_modelfile(gguf_path, quant)
    model_name = f"{OLLAMA_MODEL_PREFIX}-e4b:{quant.replace('_', '')}"

    log.info(f"  Creating Ollama model: {model_name}")

    try:
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", str(modelfile)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode == 0:
            log.info(f"  ✓ Registered: {model_name}")
            return True
        else:
            log.error(f"  ✗ Failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log.error("  ✗ Ollama create timed out (10min)")
        return False
    except FileNotFoundError:
        log.error("  ✗ 'ollama' CLI not found in PATH")
        return False


def main():
    parser = argparse.ArgumentParser(description="Jemma Model Export")
    parser.add_argument("--stage", type=int, default=None,
                        help="Export specific stage checkpoint")
    parser.add_argument("--quants", nargs="+", default=["q4_k_m", "q8_0"],
                        choices=SUPPORTED_QUANTS,
                        help="Quantization methods")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip Ollama registration")
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="Direct path to merged checkpoint")
    args = parser.parse_args()

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║    Jemma Model Export Pipeline                ║")
    log.info("╚══════════════════════════════════════════════╝")

    # Find checkpoint
    if args.checkpoint:
        checkpoint = Path(args.checkpoint)
    else:
        checkpoint = find_best_checkpoint(args.stage)

    if not checkpoint or not checkpoint.exists():
        log.error("No checkpoint found. Run training first.")
        sys.exit(1)

    log.info(f"  Checkpoint: {checkpoint}")

    # Export GGUF
    t0 = time.perf_counter()
    exported = export_gguf(checkpoint, args.quants)
    export_time = time.perf_counter() - t0

    # Register with Ollama
    registered = {}
    if not args.skip_ollama:
        for quant, gguf_path in exported.items():
            registered[quant] = register_ollama(gguf_path, quant)

    # Save export state
    state = {
        "checkpoint": str(checkpoint),
        "quants": args.quants,
        "exported": {q: str(p) for q, p in exported.items()},
        "ollama_registered": registered,
        "export_time_seconds": export_time,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state_path = STATE_DIR / "export_state.json"
    state_path.write_text(json.dumps(state, indent=2), "utf-8")

    log.info(f"\n═══ Export complete ({export_time:.0f}s) ═══")
    for quant, path in exported.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        reg = "✓ Ollama" if registered.get(quant) else "– no Ollama"
        log.info(f"  {quant}: {size_mb:.0f} MB {reg}")


if __name__ == "__main__":
    main()
