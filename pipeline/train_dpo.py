#!/usr/bin/env python3
"""
Jemma DPO Alignment Trainer — Stage 4.

Runs Direct Preference Optimization on the merged SFT checkpoint
using HelpSteer2 + UltraFeedback + Capybara preference pairs.

Usage:
  python pipeline/train_dpo.py                  # Train DPO
  python pipeline/train_dpo.py --dry-run        # Verify data loads
  python pipeline/train_dpo.py --from-stage 2   # Start from Stage 2 checkpoint
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

log = logging.getLogger("train_dpo")
log.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh = logging.FileHandler(LOGS_DIR / "train_dpo.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)

BASE_MODEL = "unsloth/gemma-4-E4B-it"

# DPO hyperparameters
DPO_CONFIG = {
    "lora_r": 16,
    "lora_alpha": 16,
    "learning_rate": 5e-6,
    "num_epochs": 1,
    "max_seq_length": 2048,
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "beta": 0.1,
    "warmup_ratio": 0.1,
}

TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def find_best_checkpoint(from_stage: int | None = None) -> str:
    """Find the best available merged checkpoint to start DPO from."""
    if from_stage:
        from pipeline.train_sft import get_checkpoint_path
        cp = get_checkpoint_path(from_stage)
        if cp.exists():
            return str(cp)

    # Search backwards through stages
    for stage in [5, 3, 2, 1]:
        cp = CHECKPOINTS_DIR / f"stage{stage}_{_stage_name(stage)}"
        if cp.exists():
            log.info(f"  Found Stage {stage} checkpoint: {cp}")
            return str(cp)

    log.info(f"  No SFT checkpoint found, using base model")
    return BASE_MODEL


def _stage_name(stage: int) -> str:
    names = {1: "general_sft", 2: "domain_sft", 3: "toolcall_sft", 5: "safety_sft"}
    return names.get(stage, f"stage{stage}")


def load_dpo_data() -> list[dict]:
    """Load DPO preference data."""
    path = PREPARED_DIR / "stage4_dpo.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"DPO data not found: {path}\n"
            f"Run 'python pipeline/dataset_prep.py --stage dpo' first."
        )
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                if "chosen" in obj and "rejected" in obj:
                    data.append(obj)
    log.info(f"  Loaded {len(data):,} DPO preference pairs")
    return data


def format_dpo_for_trl(examples: list[dict], tokenizer) -> dict:
    """Format preference pairs for TRL DPOTrainer."""
    prompts = []
    chosen_texts = []
    rejected_texts = []

    for ex in examples:
        chosen = ex["chosen"]
        rejected = ex["rejected"]

        # Extract prompt (first user message)
        prompt_msgs = []
        chosen_response = ""
        rejected_response = ""

        for m in chosen:
            if m["role"] == "user":
                prompt_msgs.append(m)
            elif m["role"] == "assistant":
                chosen_response = m["content"]
                break

        for m in rejected:
            if m["role"] == "assistant":
                rejected_response = m["content"]
                break

        if not prompt_msgs or not chosen_response or not rejected_response:
            continue

        try:
            prompt_text = tokenizer.apply_chat_template(
                prompt_msgs, tokenize=False, add_generation_prompt=True
            )
            if hasattr(prompt_text, "removeprefix"):
                prompt_text = prompt_text.removeprefix("<bos>")
        except Exception:
            continue

        prompts.append(prompt_text)
        chosen_texts.append(chosen_response)
        rejected_texts.append(rejected_response)

    return {
        "prompt": prompts,
        "chosen": chosen_texts,
        "rejected": rejected_texts,
    }


def run_dpo(from_stage: int | None = None, dry_run: bool = False):
    """Execute DPO alignment training."""
    import torch

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  Stage 4: DPO Alignment                      ║")
    log.info("╚══════════════════════════════════════════════╝")

    # ── Load data ─────────────────────────────────────────────────────────
    raw_data = load_dpo_data()

    if dry_run:
        log.info(f"  DRY RUN — {len(raw_data)} preference pairs loaded.")
        if raw_data:
            ex = raw_data[0]
            log.info(f"  Chosen[0]: {str(ex['chosen'])[:100]}...")
            log.info(f"  Rejected[0]: {str(ex['rejected'])[:100]}...")
        return

    # ── Safety watchdog ───────────────────────────────────────────────────
    sys.path.insert(0, str(ROOT / "pipeline"))
    try:
        from safety_watchdog import start_watchdog, health
        start_watchdog(interval=30)
        log.info(f"  Safety watchdog: {health()}")
    except ImportError:
        log.warning("  Safety watchdog not available")

    # ── Load model ────────────────────────────────────────────────────────
    from unsloth import FastModel

    model_path = find_best_checkpoint(from_stage)
    log.info(f"  Loading model: {model_path}")

    model, tokenizer = FastModel.from_pretrained(
        model_path,
        dtype=None,
        max_seq_length=DPO_CONFIG["max_seq_length"],
        load_in_4bit=True,
        full_finetuning=False,
    )

    model = FastModel.get_peft_model(
        model,
        r=DPO_CONFIG["lora_r"],
        lora_alpha=DPO_CONFIG["lora_alpha"],
        lora_dropout=0,
        target_modules=TARGET_MODULES,
        use_rslora=True,
        use_gradient_checkpointing="unsloth",
    )
    log.info(f"  Model loaded. Trainable: {model.print_trainable_parameters()}")

    # ── Format data ───────────────────────────────────────────────────────
    log.info("  Formatting DPO data...")
    formatted = format_dpo_for_trl(raw_data, tokenizer)
    log.info(f"  Formatted {len(formatted['prompt']):,} valid preference pairs")

    from datasets import Dataset
    dataset = Dataset.from_dict(formatted)

    # ── Train ─────────────────────────────────────────────────────────────
    from trl import DPOTrainer, DPOConfig

    output_dir = CHECKPOINTS_DIR / "stage4_dpo_lora"
    training_args = DPOConfig(
        output_dir=str(output_dir),
        per_device_train_batch_size=DPO_CONFIG["per_device_train_batch_size"],
        gradient_accumulation_steps=DPO_CONFIG["gradient_accumulation_steps"],
        num_train_epochs=DPO_CONFIG["num_epochs"],
        learning_rate=DPO_CONFIG["learning_rate"],
        warmup_ratio=DPO_CONFIG["warmup_ratio"],
        beta=DPO_CONFIG["beta"],
        optim="adamw_8bit",
        bf16=True,
        logging_steps=10,
        save_strategy="steps",
        save_steps=500,
        seed=3407,
        report_to="none",
        max_length=DPO_CONFIG["max_seq_length"],
        max_prompt_length=DPO_CONFIG["max_seq_length"] // 2,
    )

    trainer = DPOTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
    )

    log.info("  Starting DPO training...")
    t0 = time.perf_counter()
    result = trainer.train()
    elapsed = time.perf_counter() - t0

    log.info(f"  DPO training complete in {elapsed/3600:.1f}h")
    log.info(f"  Final loss: {result.training_loss:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────
    adapter_path = CHECKPOINTS_DIR / "stage4_dpo_adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))

    merged_path = CHECKPOINTS_DIR / "stage4_dpo"
    model.save_pretrained_merged(str(merged_path), tokenizer, save_method="merged_16bit")
    log.info(f"  ✓ DPO merged checkpoint: {merged_path}")

    state = {
        "stage": 4,
        "name": "dpo_alignment",
        "model_path": model_path,
        "merged_checkpoint": str(merged_path),
        "training_loss": result.training_loss,
        "global_step": result.global_step,
        "elapsed_hours": elapsed / 3600,
        "num_pairs": len(formatted["prompt"]),
        "config": DPO_CONFIG,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state_path = STATE_DIR / "stage4_dpo_state.json"
    state_path.write_text(json.dumps(state, indent=2, default=str), "utf-8")

    del model, trainer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    log.info("  Stage 4 (DPO) complete.")
    return merged_path


def main():
    parser = argparse.ArgumentParser(description="Jemma DPO Alignment Trainer")
    parser.add_argument("--from-stage", type=int, default=None,
                        help="Start from specific SFT stage checkpoint")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dpo(from_stage=args.from_stage, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
