#!/usr/bin/env python3
"""
Jemma Multi-Stage SFT Trainer — Unsloth QLoRA on Gemma 4 E4B.

Implements the sequential SFT pipeline:
  Stage 1: General capability (UltraChat + OpenHermes)
  Stage 2: Domain specialization (OSHA + FEMA + Construction)
  Stage 3: Tool calling (Glaive Function Calling)
  Stage 5: Safety refusals (toxicity + domain refusals)

Each stage:
  1. Loads the previous merged checkpoint (or base model for Stage 1)
  2. Applies a fresh LoRA adapter
  3. Trains with Unsloth QLoRA
  4. Merges LoRA into base
  5. Saves merged checkpoint

Usage:
  python pipeline/train_sft.py --stage 1            # General SFT
  python pipeline/train_sft.py --stage 2            # Domain SFT
  python pipeline/train_sft.py --stage 3            # Tool calling SFT
  python pipeline/train_sft.py --stage 5            # Safety SFT
  python pipeline/train_sft.py --stage 1 --dry-run  # Verify data loads
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINTS_DIR = ROOT / "checkpoints"
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"
PREPARED_DIR = ROOT / "datasets" / "prepared"

for d in [CHECKPOINTS_DIR, LOGS_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("train_sft")
log.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh = logging.FileHandler(LOGS_DIR / "train_sft.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)

# ── Stage configurations ──────────────────────────────────────────────────────
BASE_MODEL = "unsloth/gemma-4-E4B-it"

STAGE_CONFIGS = {
    1: {
        "name": "general_sft",
        "data_file": "stage1_general_sft.jsonl",
        "description": "General capability (UltraChat + OpenHermes)",
        "lora_r": 32,
        "lora_alpha": 32,
        "learning_rate": 2e-4,
        "num_epochs": 1,
        "max_steps": -1,  # full epoch
        "max_seq_length": 2048,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "cosine",
        "warmup_ratio": 0.1,
    },
    2: {
        "name": "domain_sft",
        "data_file": "stage2_domain_sft.jsonl",
        "description": "Domain specialization (OSHA + FEMA + Construction)",
        "lora_r": 32,
        "lora_alpha": 32,
        "learning_rate": 1e-4,
        "num_epochs": 2,
        "max_steps": -1,
        "max_seq_length": 2048,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "cosine",
        "warmup_ratio": 0.1,
    },
    3: {
        "name": "toolcall_sft",
        "data_file": "stage3_toolcall_sft.jsonl",
        "description": "Tool calling (Glaive Function Calling)",
        "lora_r": 16,
        "lora_alpha": 16,
        "learning_rate": 5e-5,
        "num_epochs": 2,
        "max_steps": -1,
        "max_seq_length": 4096,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "linear",
        "warmup_ratio": 0.05,
    },
    5: {
        "name": "safety_sft",
        "data_file": "stage5_safety_sft.jsonl",
        "description": "Safety refusal training",
        "lora_r": 16,
        "lora_alpha": 16,
        "learning_rate": 5e-5,
        "num_epochs": 2,
        "max_steps": -1,
        "max_seq_length": 2048,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "lr_scheduler_type": "linear",
        "warmup_ratio": 0.05,
    },
}

# Target modules for LoRA
TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def get_checkpoint_path(stage: int) -> Path:
    """Path for the merged checkpoint after a stage."""
    return CHECKPOINTS_DIR / f"stage{stage}_{STAGE_CONFIGS[stage]['name']}"


def get_previous_checkpoint(stage: int) -> str:
    """Get the model path to load for this stage."""
    # Look backwards for the most recent completed stage
    for prev in sorted(STAGE_CONFIGS.keys()):
        if prev >= stage:
            break
        cp = get_checkpoint_path(prev)
        if cp.exists():
            log.info(f"  Resuming from Stage {prev} checkpoint: {cp}")
            return str(cp)
    log.info(f"  Starting from base model: {BASE_MODEL}")
    return BASE_MODEL


def load_training_data(data_file: str) -> list[dict]:
    """Load training data from prepared JSONL."""
    path = PREPARED_DIR / data_file
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            f"Run 'python pipeline/dataset_prep.py' first."
        )
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    log.info(f"  Loaded {len(data):,} training examples from {data_file}")
    return data


def format_for_unsloth(examples: list[dict], tokenizer) -> list[str]:
    """Convert message-based examples to text using Gemma 4 chat template."""
    texts = []
    for ex in examples:
        messages = ex.get("messages", [])
        if not messages:
            continue
        try:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            # Remove leading <bos> — tokenizer adds it during encoding
            if hasattr(text, "removeprefix"):
                text = text.removeprefix("<bos>")
            texts.append(text)
        except Exception:
            continue
    return texts


def run_stage(stage: int, dry_run: bool = False):
    """Execute a single SFT training stage."""
    import torch

    config = STAGE_CONFIGS[stage]
    log.info(f"╔══════════════════════════════════════════════╗")
    log.info(f"║  Stage {stage}: {config['description']:<37}║")
    log.info(f"╚══════════════════════════════════════════════╝")

    # ── Load data ─────────────────────────────────────────────────────────
    raw_data = load_training_data(config["data_file"])

    if dry_run:
        log.info(f"  DRY RUN — {len(raw_data)} examples loaded. First example:")
        if raw_data:
            msgs = raw_data[0].get("messages", [])
            for m in msgs[:2]:
                log.info(f"    [{m['role']}]: {m['content'][:80]}...")
        return

    # ── Safety watchdog ───────────────────────────────────────────────────
    sys.path.insert(0, str(ROOT / "pipeline"))
    try:
        from safety_watchdog import start_watchdog, health
        start_watchdog(interval=30)
        log.info(f"  Safety watchdog started. GPU: {health()}")
    except ImportError:
        log.warning("  Safety watchdog not available")

    # ── Load model ────────────────────────────────────────────────────────
    from unsloth import FastModel

    model_path = get_previous_checkpoint(stage)
    log.info(f"  Loading model: {model_path}")
    log.info(f"  LoRA: r={config['lora_r']}, alpha={config['lora_alpha']}, "
             f"rslora=True, dropout=0")

    t0 = time.perf_counter()
    model, tokenizer = FastModel.from_pretrained(
        model_path,
        dtype=None,
        max_seq_length=config["max_seq_length"],
        load_in_4bit=True,
        full_finetuning=False,
    )

    model = FastModel.get_peft_model(
        model,
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=0,
        target_modules=TARGET_MODULES,
        use_rslora=True,
        use_gradient_checkpointing="unsloth",
    )
    load_time = time.perf_counter() - t0
    log.info(f"  Model loaded in {load_time:.1f}s")
    log.info(f"  Trainable params: {model.print_trainable_parameters()}")

    # ── Format data ───────────────────────────────────────────────────────
    log.info("  Formatting training data...")
    texts = format_for_unsloth(raw_data, tokenizer)
    log.info(f"  Formatted {len(texts):,} examples")

    from datasets import Dataset
    dataset = Dataset.from_dict({"text": texts})

    # ── Train ─────────────────────────────────────────────────────────────
    from trl import SFTTrainer, SFTConfig

    output_dir = CHECKPOINTS_DIR / f"stage{stage}_lora"
    training_args = SFTConfig(
        output_dir=str(output_dir),
        dataset_text_field="text",
        per_device_train_batch_size=config["per_device_train_batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        num_train_epochs=config["num_epochs"],
        max_steps=config["max_steps"],
        learning_rate=config["learning_rate"],
        lr_scheduler_type=config["lr_scheduler_type"],
        warmup_ratio=config["warmup_ratio"],
        optim="adamw_8bit",
        weight_decay=0.001,
        bf16=True,
        logging_steps=10,
        save_strategy="steps",
        save_steps=500,
        seed=3407,
        report_to="none",
        max_seq_length=config["max_seq_length"],
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
    )

    # Train on responses only (Gemma 4 format)
    try:
        from unsloth.chat_templates import train_on_responses_only
        trainer = train_on_responses_only(
            trainer,
            instruction_part="<|turn>user\n",
            response_part="<|turn>model\n",
        )
        log.info("  ✓ train_on_responses_only enabled")
    except Exception as e:
        log.warning(f"  train_on_responses_only not available: {e}")

    # Register progress callback for live monitoring
    from transformers import TrainerCallback

    class ProgressCallback(TrainerCallback):
        """Writes progress to state file for live_monitor to read."""
        def __init__(self, stage: int, total_examples: int):
            self._stage = stage
            self._total_examples = total_examples
            self._progress_path = STATE_DIR / "training_progress.json"
            self._start = time.perf_counter()

        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs is None:
                return
            elapsed = time.perf_counter() - self._start
            progress = {
                "stage": self._stage,
                "global_step": state.global_step,
                "max_steps": state.max_steps,
                "epoch": round(state.epoch or 0, 3),
                "loss": logs.get("loss"),
                "learning_rate": logs.get("learning_rate"),
                "grad_norm": logs.get("grad_norm"),
                "elapsed_s": round(elapsed, 1),
                "samples_per_s": round(self._total_examples * (state.epoch or 0) / max(elapsed, 1), 1),
                "eta_s": round((state.max_steps - state.global_step) / max(state.global_step / max(elapsed, 1), 0.001)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                tmp = self._progress_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(progress, indent=2, default=str), "utf-8")
                tmp.replace(self._progress_path)
            except Exception:
                pass

    trainer.add_callback(ProgressCallback(stage, len(texts)))

    eff_batch = config["per_device_train_batch_size"] * config["gradient_accumulation_steps"]
    total_steps = (len(texts) * config["num_epochs"]) // eff_batch
    est_hours = total_steps / 600  # ~600 steps/hr on RTX 5090

    log.info(f"  Starting training...")
    log.info(f"  Effective batch size: "
             f"{config['per_device_train_batch_size']} × {config['gradient_accumulation_steps']} = "
             f"{eff_batch}")
    log.info(f"  Estimated: {total_steps} steps, ~{est_hours:.1f}h on RTX 5090")

    t_train = time.perf_counter()
    result = trainer.train()
    elapsed = time.perf_counter() - t_train

    log.info(f"  Training complete in {elapsed/3600:.1f}h")
    log.info(f"  Final loss: {result.training_loss:.4f}")
    log.info(f"  Steps: {result.global_step}")

    # ── Save LoRA adapter ─────────────────────────────────────────────────
    adapter_path = CHECKPOINTS_DIR / f"stage{stage}_adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    log.info(f"  LoRA adapter saved: {adapter_path}")

    # ── Merge LoRA → base for next stage ──────────────────────────────────
    merged_path = get_checkpoint_path(stage)
    log.info(f"  Merging LoRA into base → {merged_path}")

    model.save_pretrained_merged(
        str(merged_path),
        tokenizer,
        save_method="merged_16bit",
    )
    log.info(f"  ✓ Merged checkpoint saved: {merged_path}")

    # ── Save training state ───────────────────────────────────────────────
    state = {
        "stage": stage,
        "name": config["name"],
        "description": config["description"],
        "model_path": str(model_path),
        "merged_checkpoint": str(merged_path),
        "adapter_path": str(adapter_path),
        "training_loss": result.training_loss,
        "global_step": result.global_step,
        "elapsed_hours": elapsed / 3600,
        "num_examples": len(texts),
        "config": {k: v for k, v in config.items() if k != "data_file"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
    }
    state_path = STATE_DIR / f"stage{stage}_training_state.json"
    state_path.write_text(json.dumps(state, indent=2, default=str), "utf-8")
    log.info(f"  Training state saved: {state_path}")

    # ── Cleanup ───────────────────────────────────────────────────────────
    del model, trainer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    log.info(f"  Stage {stage} complete.")
    return merged_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Jemma Multi-Stage SFT Trainer")
    parser.add_argument("--stage", type=int, required=True, choices=[1, 2, 3, 5],
                        help="Stage number: 1=General, 2=Domain, 3=ToolCall, 5=Safety")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load data only, no training")
    args = parser.parse_args()

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║    Jemma SFT Training — Unsloth QLoRA        ║")
    log.info("╚══════════════════════════════════════════════╝")

    run_stage(args.stage, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
