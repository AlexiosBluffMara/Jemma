"""
Jemma Embed — Master Orchestrator

End-to-end pipeline for building Gemma 4 trimodal embedding models:
  Step 1: Prepare training data (text + multimodal)
  Step 2: Train E2B embedding model (3 phases)
  Step 3: Train E4B embedding model (3 phases)
  Step 4: Benchmark both against competitors
  Step 5: Export best models to HuggingFace

Designed for RTX 5090 32GB, 7-day unattended run with safety monitoring.
Checkpoint/resume at every step boundary.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from safety_watchdog import health, start_watchdog, print_status, query_gpu

log = logging.getLogger("jemma.embed.orchestrator")

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state" / "embedding_orchestrator_state.json"
LOGS_DIR = BASE_DIR / "logs" / "embedding"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "step": 0,
        "data_prepared": False,
        "e2b_trained": False,
        "e4b_trained": False,
        "benchmarked": False,
        "exported": False,
        "started_at": None,
        "errors": [],
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
def step_1_prepare_data(state: dict) -> dict:
    """Download and prepare all training datasets."""
    if state["data_prepared"]:
        log.info("Step 1 already complete, skipping data preparation")
        return state

    log.info("\n" + "=" * 70)
    log.info("STEP 1: PREPARE TRAINING DATA")
    log.info("=" * 70)

    try:
        from pipeline.embedding_data import prepare_all_datasets

        results = prepare_all_datasets(phases=["text", "multimodal"])

        total_samples = 0
        for name, path in results.items():
            if path.exists():
                with open(path) as f:
                    count = sum(1 for _ in f)
                total_samples += count
                log.info(f"  {name}: {count:,} samples")

        state["data_prepared"] = True
        state["total_training_samples"] = total_samples
        save_state(state)
        log.info(f"Step 1 complete: {total_samples:,} total samples prepared")

    except Exception as e:
        log.error(f"Step 1 failed: {e}")
        traceback.print_exc()
        state["errors"].append({"step": 1, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)

    return state


def step_2_train_e2b(state: dict) -> dict:
    """Train E2B embedding model (smaller, faster, full multimodal)."""
    if state["e2b_trained"]:
        log.info("Step 2 already complete, skipping E2B training")
        return state

    log.info("\n" + "=" * 70)
    log.info("STEP 2: TRAIN E2B EMBEDDING MODEL")
    log.info("=" * 70)

    try:
        from pipeline.embedding_trainer import run_embedding_training

        model, train_state = run_embedding_training(
            variant="e2b",
            phases=["phase1", "phase2", "phase3"],
            resume=True,
        )

        state["e2b_trained"] = True
        state["e2b_steps"] = train_state.get("global_step", 0)
        state["e2b_best_loss"] = train_state.get("best_loss")
        save_state(state)
        log.info(f"Step 2 complete: E2B trained, {state['e2b_steps']} steps")

        # Free GPU memory
        del model
        import gc
        gc.collect()
        if hasattr(__import__("torch"), "cuda"):
            __import__("torch").cuda.empty_cache()

    except Exception as e:
        log.error(f"Step 2 failed: {e}")
        traceback.print_exc()
        state["errors"].append({"step": 2, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)

    return state


def step_3_train_e4b(state: dict) -> dict:
    """Train E4B embedding model (larger, higher quality, full multimodal)."""
    if state["e4b_trained"]:
        log.info("Step 3 already complete, skipping E4B training")
        return state

    log.info("\n" + "=" * 70)
    log.info("STEP 3: TRAIN E4B EMBEDDING MODEL")
    log.info("=" * 70)

    try:
        from pipeline.embedding_trainer import run_embedding_training

        model, train_state = run_embedding_training(
            variant="e4b",
            phases=["phase1", "phase2", "phase3"],
            resume=True,
        )

        state["e4b_trained"] = True
        state["e4b_steps"] = train_state.get("global_step", 0)
        state["e4b_best_loss"] = train_state.get("best_loss")
        save_state(state)
        log.info(f"Step 3 complete: E4B trained, {state['e4b_steps']} steps")

        del model
        import gc
        gc.collect()
        if hasattr(__import__("torch"), "cuda"):
            __import__("torch").cuda.empty_cache()

    except Exception as e:
        log.error(f"Step 3 failed: {e}")
        traceback.print_exc()
        state["errors"].append({"step": 3, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)

    return state


def step_4_benchmark(state: dict) -> dict:
    """Benchmark both models against competitors."""
    if state["benchmarked"]:
        log.info("Step 4 already complete, skipping benchmarks")
        return state

    log.info("\n" + "=" * 70)
    log.info("STEP 4: BENCHMARK AGAINST COMPETITORS")
    log.info("=" * 70)

    try:
        sys.path.insert(0, str(BASE_DIR / "benchmarks"))
        from benchmarks.run_embedding_benchmarks import run_full_benchmark

        # Benchmark E2B
        e2b_ckpt = BASE_DIR / "checkpoints" / "embedding" / "e2b" / "final_step*"
        import glob
        e2b_paths = sorted(glob.glob(str(e2b_ckpt)))
        if e2b_paths:
            log.info(f"Benchmarking E2B from {e2b_paths[-1]}")
            e2b_report = run_full_benchmark(
                model_path=e2b_paths[-1],
                variant="e2b",
                run_competitors=True,
            )
            state["e2b_benchmark"] = e2b_report.summary

        # Benchmark E4B
        e4b_ckpt = BASE_DIR / "checkpoints" / "embedding" / "e4b" / "final_step*"
        e4b_paths = sorted(glob.glob(str(e4b_ckpt)))
        if e4b_paths:
            log.info(f"Benchmarking E4B from {e4b_paths[-1]}")
            e4b_report = run_full_benchmark(
                model_path=e4b_paths[-1],
                variant="e4b",
                run_competitors=False,  # Already ran competitors for E2B
            )
            state["e4b_benchmark"] = e4b_report.summary

        state["benchmarked"] = True
        save_state(state)
        log.info("Step 4 complete: Benchmarks finished")

    except Exception as e:
        log.error(f"Step 4 failed: {e}")
        traceback.print_exc()
        state["errors"].append({"step": 4, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)

    return state


def step_5_export(state: dict) -> dict:
    """Export best models to HuggingFace Hub."""
    if state["exported"]:
        log.info("Step 5 already complete, skipping export")
        return state

    log.info("\n" + "=" * 70)
    log.info("STEP 5: EXPORT TO HUGGINGFACE")
    log.info("=" * 70)

    try:
        from huggingface_hub import HfApi

        api = HfApi()

        for variant in ["e2b", "e4b"]:
            import glob
            ckpt_pattern = str(
                BASE_DIR / "checkpoints" / "embedding" / variant / "final_step*"
            )
            paths = sorted(glob.glob(ckpt_pattern))
            if not paths:
                log.warning(f"No checkpoint found for {variant}")
                continue

            ckpt_path = Path(paths[-1])
            repo_id = f"soumitty/jemma-embed-gemma-4-{variant}"

            log.info(f"Exporting {variant} from {ckpt_path} → {repo_id}")

            # Create repo if needed
            try:
                api.create_repo(repo_id, exist_ok=True)
            except Exception:
                pass

            # Upload adapter
            adapter_path = ckpt_path / "adapter"
            if adapter_path.exists():
                api.upload_folder(
                    folder_path=str(adapter_path),
                    repo_id=repo_id,
                    path_in_repo="adapter",
                )

            # Upload matryoshka head
            head_path = ckpt_path / "matryoshka_head.pt"
            if head_path.exists():
                api.upload_file(
                    path_or_fileobj=str(head_path),
                    path_in_repo="matryoshka_head.pt",
                    repo_id=repo_id,
                )

            # Upload metadata
            meta_path = ckpt_path / "metadata.json"
            if meta_path.exists():
                api.upload_file(
                    path_or_fileobj=str(meta_path),
                    path_in_repo="metadata.json",
                    repo_id=repo_id,
                )

            # Generate and upload model card
            _upload_model_card(api, repo_id, variant, state)

            log.info(f"  Exported {variant} to {repo_id}")

        state["exported"] = True
        save_state(state)
        log.info("Step 5 complete: Models exported to HuggingFace")

    except Exception as e:
        log.error(f"Step 5 failed: {e}")
        traceback.print_exc()
        state["errors"].append({"step": 5, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)

    return state


def _upload_model_card(api, repo_id: str, variant: str, state: dict):
    """Generate and upload a model card for the embedding model."""
    import tomllib

    config_path = BASE_DIR / "configs" / "embedding-training.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    model_cfg = config["models"][variant]
    base_model = model_cfg["hf_name"].replace("unsloth/", "google/")

    card = f"""---
language: en
license: apache-2.0
library_name: transformers
tags:
  - embedding
  - gemma-4
  - trimodal
  - text-embedding
  - image-embedding
  - audio-embedding
  - matryoshka
  - contrastive-learning
  - gemma-4-good-hackathon
base_model: {base_model}
base_model_relation: finetune
pipeline_tag: feature-extraction
---

# Jemma Embed — Gemma 4 {variant.upper()} Trimodal Embedding Model

First open-source **trimodal embedding model** (text + image + audio) built on
Gemma 4 {variant.upper()} architecture. Produces unified embedding vectors where
text, images, and audio occupy the same vector space.

## Key Features

- **Trimodal**: Text, image, and audio in one unified vector space
- **Matryoshka**: Truncate embeddings to {model_cfg['matryoshka_dims']} dimensions
- **131K Context**: Embed full documents without chunking
- **QLoRA Fine-tuned**: Efficient training on RTX 5090

## Usage

```python
from jemma.embed.model import EmbedConfig, JemmaEmbedModel

config = EmbedConfig(
    model_name="{model_cfg['hf_name']}",
    embed_dim={model_cfg['embed_dim']},
    matryoshka_dims={model_cfg['matryoshka_dims']},
)
model = JemmaEmbedModel(config)
model.load_backbone()

# Text embeddings
emb = model.encode_text(["Hello world"], truncate_dim=512)

# Image embeddings (same vector space!)
from PIL import Image
img = Image.open("photo.jpg")
emb = model.encode_image([img], truncate_dim=512)

# Audio embeddings (E2B/E4B only)
import numpy as np
audio = np.random.randn(16000)  # 1 second at 16kHz
emb = model.encode_audio([audio], truncate_dim=512)
```

## Training Details

- **Base model**: {base_model}
- **Method**: QLoRA (r={config['qlora']['r']}) + Matryoshka Representation Learning
- **Phase 1**: Text contrastive (MS MARCO + AllNLI + civic domain)
- **Phase 2**: Cross-modal alignment (COCO Captions + AudioCaps)
- **Phase 3**: Matryoshka dimension refinement
- **Hardware**: NVIDIA RTX 5090 32GB

## Benchmarks

See `benchmarks/results/embedding_*.json` for full results.

Gemma is a trademark of Google LLC.
"""

    api.upload_file(
        path_or_fileobj=card.encode(),
        path_in_repo="README.md",
        repo_id=repo_id,
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_full_pipeline(
    variants: list[str] | None = None,
    skip_steps: list[int] | None = None,
    fresh: bool = False,
):
    """
    Run the complete embedding pipeline.

    Args:
        variants: ["e2b", "e4b"] or subset
        skip_steps: list of step numbers to skip
        fresh: if True, start from scratch
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if variants is None:
        variants = ["e2b", "e4b"]
    if skip_steps is None:
        skip_steps = []

    state = load_state() if not fresh else {
        "step": 0, "data_prepared": False, "e2b_trained": False,
        "e4b_trained": False, "benchmarked": False, "exported": False,
        "started_at": datetime.utcnow().isoformat(), "errors": [],
    }
    state["started_at"] = state.get("started_at") or datetime.utcnow().isoformat()
    state["variants"] = variants
    save_state(state)

    # Start GPU watchdog
    start_watchdog()
    gpu = query_gpu()
    log.info(f"GPU: {gpu.gpu_name}, {gpu.vram_total_mb}MB, {gpu.temperature_c}°C")

    start_time = time.time()

    # Step 1: Data
    if 1 not in skip_steps:
        state = step_1_prepare_data(state)

    # Step 2: E2B
    if 2 not in skip_steps and "e2b" in variants:
        state = step_2_train_e2b(state)

    # Step 3: E4B
    if 3 not in skip_steps and "e4b" in variants:
        state = step_3_train_e4b(state)

    # Step 4: Benchmark
    if 4 not in skip_steps:
        state = step_4_benchmark(state)

    # Step 5: Export
    if 5 not in skip_steps:
        state = step_5_export(state)

    elapsed = time.time() - start_time
    elapsed_h = elapsed / 3600

    log.info("\n" + "=" * 70)
    log.info("JEMMA EMBED PIPELINE COMPLETE")
    log.info("=" * 70)
    log.info(f"Total time: {elapsed_h:.1f} hours")
    log.info(f"Errors: {len(state.get('errors', []))}")
    if state.get("e2b_benchmark"):
        log.info(f"E2B summary: {state['e2b_benchmark']}")
    if state.get("e4b_benchmark"):
        log.info(f"E4B summary: {state['e4b_benchmark']}")
    log.info("=" * 70)

    state["completed_at"] = datetime.utcnow().isoformat()
    state["total_hours"] = elapsed_h
    save_state(state)

    return state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                LOGS_DIR / "embedding_orchestrator.log", mode="a",
            ) if LOGS_DIR.exists() or not LOGS_DIR.mkdir(parents=True, exist_ok=True) else logging.StreamHandler(),
        ],
    )

    parser = argparse.ArgumentParser(
        description="Jemma Embed — Full Training Pipeline Orchestrator"
    )
    parser.add_argument("--variants", nargs="+", default=["e2b", "e4b"],
                        choices=["e2b", "e4b"])
    parser.add_argument("--skip", nargs="+", type=int, default=[],
                        help="Skip steps (1=data, 2=e2b, 3=e4b, 4=bench, 5=export)")
    parser.add_argument("--fresh", action="store_true",
                        help="Start from scratch")
    parser.add_argument("--data-only", action="store_true",
                        help="Only prepare data")
    parser.add_argument("--bench-only", action="store_true",
                        help="Only run benchmarks")
    args = parser.parse_args()

    if args.data_only:
        state = load_state()
        step_1_prepare_data(state)
    elif args.bench_only:
        state = load_state()
        step_4_benchmark(state)
    else:
        run_full_pipeline(
            variants=args.variants,
            skip_steps=args.skip,
            fresh=args.fresh,
        )
