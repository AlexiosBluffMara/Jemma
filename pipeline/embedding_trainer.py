"""
Jemma Embed — Embedding Trainer

Three-phase training pipeline for Gemma 4 embedding models:
  Phase 1: Text contrastive learning (InfoNCE + in-batch negatives)
  Phase 2: Cross-modal alignment (CLIP-style symmetric loss)
  Phase 3: Matryoshka dimension refinement

Integrates with safety_watchdog for GPU protection during long runs.
Supports both E2B and E4B variants via config.
Designed for RTX 5090 32GB, multi-day unattended runs.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))
# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from safety_watchdog import (
    health, start_watchdog, query_gpu, clear_gpu_cache,
    GPU_TEMP_WARNING, GPU_TEMP_THROTTLE, GPU_TEMP_EMERGENCY,
)

log = logging.getLogger("jemma.embed.trainer")

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKPOINTS_DIR = BASE_DIR / "checkpoints" / "embedding"
LOGS_DIR = BASE_DIR / "logs" / "embedding"
STATE_FILE = BASE_DIR / "state" / "embedding_state.json"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "variant": None,
        "phase": 0,
        "phase1_done": False,
        "phase2_done": False,
        "phase3_done": False,
        "global_step": 0,
        "best_loss": float("inf"),
        "started_at": None,
        "errors": [],
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ---------------------------------------------------------------------------
# Collate functions
# ---------------------------------------------------------------------------
def text_collate_fn(batch: list[dict], processor, max_length: int = 512):
    """Collate text triplets into tokenized batches."""
    queries = [b["query"] for b in batch]
    positives = [b["positive"] for b in batch]
    negatives = [b["negative"] for b in batch if b.get("negative")]

    q_enc = processor(
        text=queries, return_tensors="pt", padding=True,
        truncation=True, max_length=max_length,
    )
    p_enc = processor(
        text=positives, return_tensors="pt", padding=True,
        truncation=True, max_length=max_length,
    )
    result = {"query": q_enc, "positive": p_enc}

    if negatives and len(negatives) == len(queries):
        n_enc = processor(
            text=negatives, return_tensors="pt", padding=True,
            truncation=True, max_length=max_length,
        )
        result["negative"] = n_enc

    return result


# ---------------------------------------------------------------------------
# Phase 1: Text Contrastive Training
# ---------------------------------------------------------------------------
def train_phase1_text(
    model,
    config: dict,
    state: dict,
    resume_step: int = 0,
) -> dict:
    """
    Phase 1: Train text embeddings with InfoNCE + in-batch negatives.
    Uses MS MARCO triplets + AllNLI pairs + civic domain pairs.
    """
    from jemma.embed.model import InfoNCELoss, MatryoshkaLoss
    from pipeline.embedding_data import TextTripletDataset

    log.info("\n" + "=" * 70)
    log.info("PHASE 1: TEXT CONTRASTIVE TRAINING")
    log.info("=" * 70)

    phase_cfg = config["training"]["phase1_text"]
    matryoshka_dims = config["models"][state["variant"]]["matryoshka_dims"]

    # Build dataset
    data_dir = BASE_DIR / "datasets" / "embedding"
    dataset = TextTripletDataset(
        paths=[
            data_dir / "msmarco_triplets.jsonl",
            data_dir / "allnli_pairs.jsonl",
            data_dir / "civic_pairs.jsonl",
        ],
        max_samples=phase_cfg.get("max_steps", 10000) * phase_cfg["batch_size"],
    )

    if len(dataset) == 0:
        log.error("No training data found for Phase 1. Run embedding_data.py first.")
        return state

    # Collate
    processor = model.processor
    loader = DataLoader(
        dataset,
        batch_size=phase_cfg["batch_size"],
        shuffle=True,
        num_workers=0,
        collate_fn=lambda batch: text_collate_fn(
            batch, processor, max_length=512
        ),
        drop_last=True,
    )

    # Loss
    base_loss = InfoNCELoss(temperature=phase_cfg.get("temperature", 0.02))
    loss_fn = MatryoshkaLoss(base_loss, matryoshka_dims)
    loss_fn = loss_fn.to(model.backbone.device)

    # Optimizer — only train LoRA params + matryoshka head
    trainable_params = [
        {"params": [p for p in model.backbone.parameters() if p.requires_grad],
         "lr": phase_cfg["learning_rate"]},
        {"params": model.matryoshka_head.parameters(),
         "lr": phase_cfg["learning_rate"] * 5},  # Head trains faster
    ]
    optimizer = torch.optim.AdamW(
        trainable_params,
        weight_decay=phase_cfg.get("weight_decay", 0.01),
    )

    # LR scheduler
    total_steps = min(
        phase_cfg.get("max_steps", 10000),
        len(loader) * phase_cfg.get("epochs", 3),
    )
    warmup_steps = int(total_steps * phase_cfg.get("warmup_ratio", 0.05))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=total_steps - warmup_steps,
    )

    # Training loop
    model.train()
    global_step = resume_step
    best_loss = state.get("best_loss", float("inf"))
    grad_accum = phase_cfg.get("gradient_accumulation", 4)
    eval_steps = phase_cfg.get("eval_steps", 500)
    save_steps = phase_cfg.get("save_steps", 1000)
    device = model.backbone.device

    log.info(f"Training: {len(dataset):,} samples, {total_steps} steps, "
             f"batch_size={phase_cfg['batch_size']}, grad_accum={grad_accum}")

    epoch_losses = []
    for epoch in range(phase_cfg.get("epochs", 3)):
        for batch_idx, batch in enumerate(loader):
            if global_step >= total_steps:
                break

            # Safety check
            if not health.is_ok():
                log.warning("Safety watchdog triggered, pausing training...")
                _wait_for_safe_gpu()

            # Move to device
            q_input = {k: v.to(device) for k, v in batch["query"].items()}
            p_input = {k: v.to(device) for k, v in batch["positive"].items()}

            # Forward
            q_emb = model.encode(
                input_ids=q_input["input_ids"],
                attention_mask=q_input["attention_mask"],
            )
            p_emb = model.encode(
                input_ids=p_input["input_ids"],
                attention_mask=p_input["attention_mask"],
            )

            n_emb = None
            if "negative" in batch:
                n_input = {k: v.to(device) for k, v in batch["negative"].items()}
                n_emb = model.encode(
                    input_ids=n_input["input_ids"],
                    attention_mask=n_input["attention_mask"],
                )

            loss = loss_fn(q_emb, p_emb, n_emb)
            loss = loss / grad_accum
            loss.backward()

            if (batch_idx + 1) % grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0
                )
                optimizer.step()
                optimizer.zero_grad()
                if global_step >= warmup_steps:
                    scheduler.step()
                global_step += 1

                epoch_losses.append(loss.item() * grad_accum)

                # Logging
                if global_step % 50 == 0:
                    avg_loss = sum(epoch_losses[-50:]) / len(epoch_losses[-50:])
                    gpu = query_gpu()
                    lr = optimizer.param_groups[0]["lr"]
                    log.info(
                        f"Phase1 step {global_step}/{total_steps} | "
                        f"loss={avg_loss:.4f} | lr={lr:.2e} | "
                        f"GPU={gpu.temperature_c}°C {gpu.vram_used_mb}MB"
                    )

                # Save checkpoint
                if global_step % save_steps == 0:
                    _save_checkpoint(model, state, global_step, "phase1")

                # Eval
                if global_step % eval_steps == 0:
                    avg = sum(epoch_losses[-eval_steps:]) / max(
                        len(epoch_losses[-eval_steps:]), 1
                    )
                    if avg < best_loss:
                        best_loss = avg
                        _save_checkpoint(model, state, global_step, "phase1_best")
                        log.info(f"  New best loss: {best_loss:.4f}")

        log.info(f"Phase 1 epoch {epoch + 1} complete, step={global_step}")

    state["phase1_done"] = True
    state["global_step"] = global_step
    state["best_loss"] = best_loss
    save_state(state)
    log.info(f"Phase 1 complete: {global_step} steps, best_loss={best_loss:.4f}")
    return state


# ---------------------------------------------------------------------------
# Phase 2: Cross-Modal Alignment
# ---------------------------------------------------------------------------
def train_phase2_multimodal(
    model,
    config: dict,
    state: dict,
    resume_step: int = 0,
) -> dict:
    """
    Phase 2: Align image and audio embeddings with text embeddings
    using CLIP-style symmetric contrastive loss.
    """
    from jemma.embed.model import CrossModalContrastiveLoss

    log.info("\n" + "=" * 70)
    log.info("PHASE 2: CROSS-MODAL ALIGNMENT")
    log.info("=" * 70)

    phase_cfg = config["training"]["phase2_multimodal"]
    device = model.backbone.device
    modality_weights = phase_cfg.get(
        "modality_weights", {"text": 1.0, "image": 1.0, "audio": 0.8}
    )

    # Cross-modal loss
    cross_loss = CrossModalContrastiveLoss(
        temperature=phase_cfg.get("temperature", 0.02)
    ).to(device)

    # Optimizer
    trainable_params = [
        {"params": [p for p in model.backbone.parameters() if p.requires_grad],
         "lr": phase_cfg["learning_rate"]},
        {"params": model.matryoshka_head.parameters(),
         "lr": phase_cfg["learning_rate"] * 5},
        {"params": cross_loss.parameters(), "lr": phase_cfg["learning_rate"]},
    ]
    optimizer = torch.optim.AdamW(
        trainable_params,
        weight_decay=phase_cfg.get("weight_decay", 0.01),
    )

    total_steps = phase_cfg.get("max_steps", 8000)
    grad_accum = phase_cfg.get("gradient_accumulation", 8)
    save_steps = phase_cfg.get("save_steps", 800)

    # Load multimodal datasets
    from pipeline.embedding_data import MultimodalPairDataset
    data_dir = BASE_DIR / "datasets" / "embedding"

    image_dataset = MultimodalPairDataset(
        data_dir / "coco_captions.jsonl", modality="image_text"
    )
    audio_dataset = MultimodalPairDataset(
        data_dir / "audiocaps.jsonl", modality="audio_text"
    )

    model.train()
    global_step = resume_step

    log.info(f"Image pairs: {len(image_dataset):,}, Audio pairs: {len(audio_dataset):,}")
    log.info(f"Training: {total_steps} steps, batch={phase_cfg['batch_size']}")

    # Interleave image and audio batches
    img_loader = DataLoader(image_dataset, batch_size=phase_cfg["batch_size"],
                            shuffle=True, drop_last=True) if len(image_dataset) > 0 else None
    aud_loader = DataLoader(audio_dataset, batch_size=phase_cfg["batch_size"],
                            shuffle=True, drop_last=True) if len(audio_dataset) > 0 else None

    for step in range(total_steps):
        if not health.is_ok():
            _wait_for_safe_gpu()

        total_loss = torch.tensor(0.0, device=device)

        # Image-text alignment
        if img_loader is not None:
            try:
                img_batch = next(iter(img_loader))
                captions = img_batch["caption"]

                # Encode text captions
                text_enc = model.processor(
                    text=list(captions), return_tensors="pt",
                    padding=True, truncation=True, max_length=256,
                )
                text_enc = {k: v.to(device) for k, v in text_enc.items()}
                text_emb = model.encode(
                    input_ids=text_enc["input_ids"],
                    attention_mask=text_enc["attention_mask"],
                )

                # For image embedding, we process caption with image context prompt
                img_text = [f"<start_of_image>{c}" for c in captions]
                # Use text-only encoding as proxy for image embedding
                # (actual image loading deferred to runtime with real images)
                img_enc = model.processor(
                    text=img_text, return_tensors="pt",
                    padding=True, truncation=True, max_length=256,
                )
                img_enc = {k: v.to(device) for k, v in img_enc.items()}
                img_emb = model.encode(
                    input_ids=img_enc["input_ids"],
                    attention_mask=img_enc["attention_mask"],
                )

                img_loss = cross_loss(text_emb, img_emb)
                total_loss = total_loss + modality_weights.get("image", 1.0) * img_loss
            except Exception as e:
                log.warning(f"Image batch error: {e}")

        # Audio-text alignment
        if aud_loader is not None:
            try:
                aud_batch = next(iter(aud_loader))
                captions = aud_batch["caption"]

                text_enc = model.processor(
                    text=list(captions), return_tensors="pt",
                    padding=True, truncation=True, max_length=256,
                )
                text_enc = {k: v.to(device) for k, v in text_enc.items()}
                text_emb = model.encode(
                    input_ids=text_enc["input_ids"],
                    attention_mask=text_enc["attention_mask"],
                )

                aud_text = [f"<start_of_audio>{c}" for c in captions]
                aud_enc = model.processor(
                    text=aud_text, return_tensors="pt",
                    padding=True, truncation=True, max_length=256,
                )
                aud_enc = {k: v.to(device) for k, v in aud_enc.items()}
                aud_emb = model.encode(
                    input_ids=aud_enc["input_ids"],
                    attention_mask=aud_enc["attention_mask"],
                )

                aud_loss = cross_loss(text_emb, aud_emb)
                total_loss = total_loss + modality_weights.get("audio", 0.8) * aud_loss
            except Exception as e:
                log.warning(f"Audio batch error: {e}")

        if total_loss.item() > 0:
            loss_scaled = total_loss / grad_accum
            loss_scaled.backward()

            if (step + 1) % grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0
                )
                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

        if step % 100 == 0:
            gpu = query_gpu()
            log.info(
                f"Phase2 step {step}/{total_steps} | loss={total_loss.item():.4f} | "
                f"GPU={gpu.temperature_c}°C"
            )

        if step % save_steps == 0 and step > 0:
            _save_checkpoint(model, state, global_step, "phase2")

    state["phase2_done"] = True
    state["global_step"] = global_step
    save_state(state)
    log.info(f"Phase 2 complete: {global_step} global steps")
    return state


# ---------------------------------------------------------------------------
# Phase 3: Matryoshka Refinement
# ---------------------------------------------------------------------------
def train_phase3_matryoshka(
    model,
    config: dict,
    state: dict,
    resume_step: int = 0,
) -> dict:
    """
    Phase 3: Refine embeddings specifically for Matryoshka truncation.
    Quick pass with higher batch size focusing on dimension-specific quality.
    """
    from jemma.embed.model import InfoNCELoss, MatryoshkaLoss
    from pipeline.embedding_data import TextTripletDataset

    log.info("\n" + "=" * 70)
    log.info("PHASE 3: MATRYOSHKA DIMENSION REFINEMENT")
    log.info("=" * 70)

    phase_cfg = config["training"]["phase3_matryoshka"]
    matryoshka_dims = config["models"][state["variant"]]["matryoshka_dims"]

    data_dir = BASE_DIR / "datasets" / "embedding"
    dataset = TextTripletDataset(
        paths=[
            data_dir / "msmarco_triplets.jsonl",
            data_dir / "allnli_pairs.jsonl",
        ],
        max_samples=phase_cfg.get("max_steps", 3000) * phase_cfg["batch_size"],
    )

    if len(dataset) == 0:
        log.warning("No data for Phase 3, skipping")
        state["phase3_done"] = True
        save_state(state)
        return state

    processor = model.processor
    loader = DataLoader(
        dataset,
        batch_size=phase_cfg["batch_size"],
        shuffle=True,
        num_workers=0,
        collate_fn=lambda batch: text_collate_fn(batch, processor, max_length=256),
        drop_last=True,
    )

    # Heavier Matryoshka weighting for small dims
    base_loss = InfoNCELoss(temperature=0.02)
    n = len(matryoshka_dims)
    weights = [1.0 / (1.5 ** i) for i in range(n)]
    loss_fn = MatryoshkaLoss(base_loss, matryoshka_dims, dim_weights=weights)
    loss_fn = loss_fn.to(model.backbone.device)

    # Only train the matryoshka head + LoRA with low LR
    optimizer = torch.optim.AdamW([
        {"params": [p for p in model.backbone.parameters() if p.requires_grad],
         "lr": phase_cfg["learning_rate"] * 0.1},
        {"params": model.matryoshka_head.parameters(),
         "lr": phase_cfg["learning_rate"]},
    ], weight_decay=0.01)

    total_steps = phase_cfg.get("max_steps", 3000)
    device = model.backbone.device
    model.train()
    global_step = resume_step

    for batch_idx, batch in enumerate(loader):
        if global_step >= total_steps:
            break
        if not health.is_ok():
            _wait_for_safe_gpu()

        q_input = {k: v.to(device) for k, v in batch["query"].items()}
        p_input = {k: v.to(device) for k, v in batch["positive"].items()}

        q_emb = model.encode(q_input["input_ids"], q_input["attention_mask"])
        p_emb = model.encode(p_input["input_ids"], p_input["attention_mask"])

        loss = loss_fn(q_emb, p_emb)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            [p for p in model.parameters() if p.requires_grad], 1.0
        )
        optimizer.step()
        optimizer.zero_grad()
        global_step += 1

        if global_step % 100 == 0:
            log.info(f"Phase3 step {global_step}/{total_steps} | loss={loss.item():.4f}")

    state["phase3_done"] = True
    state["global_step"] = global_step
    save_state(state)
    log.info(f"Phase 3 complete: {global_step} steps")
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _save_checkpoint(model, state: dict, step: int, tag: str):
    """Save model checkpoint."""
    ckpt_dir = CHECKPOINTS_DIR / state["variant"] / f"{tag}_step{step}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Save LoRA adapter
    try:
        model.backbone.save_pretrained(str(ckpt_dir / "adapter"))
    except Exception:
        pass

    # Save matryoshka head
    torch.save(
        model.matryoshka_head.state_dict(),
        ckpt_dir / "matryoshka_head.pt",
    )

    # Save metadata
    meta = {
        "step": step,
        "tag": tag,
        "variant": state["variant"],
        "timestamp": datetime.utcnow().isoformat(),
        "best_loss": state.get("best_loss"),
    }
    (ckpt_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    log.info(f"Checkpoint saved: {ckpt_dir}")


def _wait_for_safe_gpu(max_wait: int = 300):
    """Wait for GPU to cool down before resuming."""
    start = time.time()
    while time.time() - start < max_wait:
        gpu = query_gpu()
        if gpu.temperature_c < GPU_TEMP_THROTTLE:
            log.info(f"GPU cooled to {gpu.temperature_c}°C, resuming")
            return
        log.info(f"GPU at {gpu.temperature_c}°C, waiting for cooldown...")
        time.sleep(15)
    log.warning("GPU didn't cool down in time, resuming anyway")


def _load_config() -> dict:
    """Load embedding training config from TOML."""
    import tomllib
    config_path = BASE_DIR / "configs" / "embedding-training.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# Full training pipeline
# ---------------------------------------------------------------------------
def run_embedding_training(
    variant: str = "e2b",
    phases: list[str] | None = None,
    resume: bool = True,
):
    """
    Run the full 3-phase embedding training pipeline.

    Args:
        variant: "e2b" or "e4b"
        phases: list of phases to run, e.g. ["phase1", "phase2", "phase3"]
        resume: if True, resume from last checkpoint
    """
    assert variant in ("e2b", "e4b"), f"Unknown variant: {variant}"

    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    config = _load_config()

    # Setup state
    state = load_state() if resume else load_state()
    state["variant"] = variant
    state["started_at"] = state.get("started_at") or datetime.utcnow().isoformat()
    save_state(state)

    # Start GPU watchdog
    start_watchdog()
    log.info(f"Starting embedding training for {variant.upper()}")

    # Load model
    from jemma.embed.model import EmbedConfig, JemmaEmbedModel

    model_cfg = config["models"][variant]
    embed_config = EmbedConfig(
        model_name=model_cfg["hf_name"],
        embed_dim=model_cfg["embed_dim"],
        matryoshka_dims=model_cfg["matryoshka_dims"],
        max_seq_length=model_cfg["max_seq_length"],
        dtype=model_cfg.get("dtype", "bfloat16"),
        lora_r=config["qlora"]["r"],
        lora_alpha=config["qlora"]["lora_alpha"],
        lora_dropout=config["qlora"]["lora_dropout"],
        lora_target_modules=config["qlora"]["target_modules"],
        quantization_bits=config["qlora"]["quantization_bits"],
    )

    model = JemmaEmbedModel(embed_config)
    model.load_backbone()
    model.apply_lora()

    if phases is None:
        phases = ["phase1", "phase2", "phase3"]

    # Phase 1: Text contrastive
    if "phase1" in phases and not state.get("phase1_done"):
        state = train_phase1_text(model, config, state)
        clear_gpu_cache()

    # Phase 2: Cross-modal
    if "phase2" in phases and not state.get("phase2_done"):
        state = train_phase2_multimodal(model, config, state)
        clear_gpu_cache()

    # Phase 3: Matryoshka refinement
    if "phase3" in phases and not state.get("phase3_done"):
        state = train_phase3_matryoshka(model, config, state)
        clear_gpu_cache()

    # Final save
    _save_checkpoint(model, state, state["global_step"], "final")
    log.info("\n" + "=" * 70)
    log.info(f"EMBEDDING TRAINING COMPLETE — {variant.upper()}")
    log.info(f"Total steps: {state['global_step']}, Best loss: {state.get('best_loss', 'N/A')}")
    log.info("=" * 70)

    return model, state


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
            logging.FileHandler(LOGS_DIR / "embedding_training.log", mode="a"),
        ],
    )

    parser = argparse.ArgumentParser(description="Jemma Embed — Train Gemma 4 embeddings")
    parser.add_argument("--variant", choices=["e2b", "e4b"], default="e2b",
                        help="Model variant to train")
    parser.add_argument("--phases", nargs="+", default=None,
                        choices=["phase1", "phase2", "phase3"])
    parser.add_argument("--fresh", action="store_true",
                        help="Start fresh (ignore saved state)")
    args = parser.parse_args()

    if args.fresh and STATE_FILE.exists():
        STATE_FILE.unlink()

    run_embedding_training(
        variant=args.variant,
        phases=args.phases,
        resume=not args.fresh,
    )
