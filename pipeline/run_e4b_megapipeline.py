#!/usr/bin/env python3
"""
Jemma E4B MegaPipeline — Comprehensive bf16 baseline on RTX 5090.

Runs Gemma 4 E4B-it at full bf16 precision through five phases:
  Phase 1: Data preparation (civic chunks, Kaggle CSVs, test media)
  Phase 2: Synthetic dataset generation (Normal IL, ISU, Chicago)
  Phase 3: Comprehensive multimodal benchmarks (text/image/audio/video)
  Phase 4: RAG vs Knowledge-Graph comparison
  Phase 5: Export & packaging (Kaggle dataset, HF model card artifacts)

Self-healing: OOM recovery, automatic model reload, checkpoint/resume,
              safety-watchdog integration, graceful degradation per item.

Launch:
  python pipeline/run_e4b_megapipeline.py --fresh
  python pipeline/run_e4b_megapipeline.py --phase 3      # resume at phase 3
  python pipeline/run_e4b_megapipeline.py --dry-run       # verify setup only
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import shutil
import sys
import threading
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTHONUNBUFFERED"] = "1"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import torch

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cudnn.benchmark = True

# Suppress noisy loggers
for _name in ("transformers", "huggingface_hub", "accelerate", "torch"):
    logging.getLogger(_name).setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

log = logging.getLogger("megapipeline")
log.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_fh = logging.FileHandler(LOGS_DIR / "megapipeline.log", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
STATE_PATH = ROOT / "state" / "megapipeline_state.json"
STATE_PATH.parent.mkdir(exist_ok=True)

_DEFAULT_STATE: dict = {
    "phase": 0,
    "started_at": "",
    "last_checkpoint": "",
    "phases": {
        "1_data_prep":   {"status": "not_started", "elapsed_s": 0},
        "2_synth_gen":   {"status": "not_started", "elapsed_s": 0, "items_done": 0},
        "3_benchmarks":  {"status": "not_started", "elapsed_s": 0, "items_done": 0},
        "4_rag_compare": {"status": "not_started", "elapsed_s": 0},
        "5_export":      {"status": "not_started", "elapsed_s": 0},
    },
    "model_loads": 0,
    "oom_recoveries": 0,
    "errors": [],
    "gpu_max_temp_c": 0,
    "total_tokens_generated": 0,
}


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text("utf-8"))
        except Exception:
            log.warning("Corrupt state file — starting fresh")
    return dict(_DEFAULT_STATE)


def save_state(state: dict):
    state["last_checkpoint"] = datetime.now(timezone.utc).isoformat()
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), "utf-8")
    tmp.replace(STATE_PATH)


# ---------------------------------------------------------------------------
# Model holder with reload capability
# ---------------------------------------------------------------------------
class ModelHolder:
    """Wraps E4B loading/unloading for self-healing recovery."""

    def __init__(self):
        self.model = None
        self.processor = None
        self._loads = 0

    def load(self):
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        model_id = "unsloth/gemma-4-E4B-it"
        log.info(f"Loading {model_id} bf16 …")
        t0 = time.time()
        self.model = AutoModelForMultimodalLM.from_pretrained(
            model_id,
            dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="sdpa",
        )
        self.model.eval()
        self.processor = AutoProcessor.from_pretrained(
            model_id, trust_remote_code=True
        )
        self.processor.image_processor.max_soft_tokens = 560
        self._loads += 1
        vram = torch.cuda.max_memory_allocated() / 1024**3
        log.info(f"Model loaded in {time.time()-t0:.1f}s | VRAM {vram:.1f} GB | loads={self._loads}")

    def unload(self):
        del self.model
        del self.processor
        self.model = None
        self.processor = None
        gc.collect()
        torch.cuda.empty_cache()
        gc.collect()
        torch.cuda.empty_cache()
        log.info("Model unloaded, VRAM freed")

    def reload(self):
        log.warning("Reloading model after error …")
        self.unload()
        time.sleep(3)
        self.load()

    @property
    def loads(self) -> int:
        return self._loads


# ---------------------------------------------------------------------------
# Safe generation — core self-healing inference wrapper
# ---------------------------------------------------------------------------
def safe_generate(
    holder: ModelHolder,
    messages: list[dict],
    max_new_tokens: int = 1024,
    enable_thinking: bool = False,
    temperature: float = 0.7,
    max_retries: int = 3,
    _health=None,
) -> tuple[str, dict]:
    """Generate with OOM recovery, watchdog pausing, and retry logic.

    Returns (response_text, metadata_dict).
    """
    from pipeline.safety_watchdog import health as _wdog_health

    hw = _health or _wdog_health
    tokens = max_new_tokens
    meta: dict = {"attempts": 0, "tokens_generated": 0, "latency_ms": 0}

    for attempt in range(max_retries):
        # Wait for watchdog to un-pause
        pause_waited = 0
        while hw.paused:
            if pause_waited == 0:
                log.info("Watchdog paused — waiting for clearance …")
            time.sleep(5)
            pause_waited += 5
            if pause_waited > 600:
                log.error("Watchdog paused >10 min — skipping item")
                return "[SKIPPED: watchdog timeout]", meta

        meta["attempts"] = attempt + 1
        try:
            model = holder.model
            proc = holder.processor

            # Normalize messages for the processor
            normalized = []
            for msg in messages:
                m = dict(msg)
                if isinstance(m.get("content"), str):
                    m["content"] = [{"type": "text", "text": m["content"]}]
                elif isinstance(m.get("content"), list):
                    m["content"] = list(m["content"])
                normalized.append(m)

            inputs = proc.apply_chat_template(
                normalized,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                add_generation_prompt=True,
                enable_thinking=enable_thinking,
            ).to(model.device)

            input_len = inputs["input_ids"].shape[1]
            t0 = time.perf_counter()

            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=tokens,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-6),
                    top_p=0.95,
                    top_k=64,
                )

            elapsed_ms = (time.perf_counter() - t0) * 1000
            gen_tokens = outputs.shape[1] - input_len
            response = proc.decode(outputs[0][input_len:], skip_special_tokens=True)

            meta["latency_ms"] = round(elapsed_ms, 1)
            meta["tokens_generated"] = int(gen_tokens)
            meta["tok_per_s"] = round(gen_tokens / (elapsed_ms / 1000), 2) if elapsed_ms > 0 else 0
            meta["input_tokens"] = int(input_len)
            return response.strip(), meta

        except torch.cuda.OutOfMemoryError:
            log.warning(f"OOM at max_new_tokens={tokens} (attempt {attempt+1})")
            torch.cuda.empty_cache()
            gc.collect()
            torch.cuda.empty_cache()
            tokens = max(64, tokens // 2)
            meta["oom"] = True
            time.sleep(2)

        except Exception as e:
            log.error(f"Generate error (attempt {attempt+1}): {e}")
            if "CUDA" in str(e) or "device" in str(e).lower():
                try:
                    holder.reload()
                except Exception as re_err:
                    log.critical(f"Model reload failed: {re_err}")
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                return f"[ERROR: {e}]", meta

    return "[ERROR: max retries exceeded]", meta


# ---------------------------------------------------------------------------
# Phase dispatch
# ---------------------------------------------------------------------------
def run_phase_1_data_prep(holder: ModelHolder, state: dict) -> dict:
    """Prepare directories, verify data sources, create test media."""
    log.info("═══ Phase 1: Data Preparation ═══")
    t0 = time.time()

    for d in [
        ROOT / "datasets" / "synthetic",
        ROOT / "datasets" / "megapipeline" / "test_media",
        ROOT / "benchmarks" / "results" / "megapipeline",
        ROOT / "artifacts" / "kaggle_upload",
        ROOT / "artifacts" / "model_card",
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Verify civic data
    db_path = ROOT / "datasets" / "civic_data.db"
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        pages = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        conn.close()
        log.info(f"Civic DB: {pages} pages, {chunks} chunks")
    else:
        log.warning("civic_data.db not found — civic benchmarks will be limited")

    # Verify Kaggle data
    kaggle_dir = ROOT / "datasets" / "kaggle_downloads"
    if kaggle_dir.exists():
        csv_files = list(kaggle_dir.rglob("*.csv"))
        log.info(f"Kaggle CSVs: {len(csv_files)} files")
    else:
        log.warning("No Kaggle downloads found")

    # Create synthetic test media for multimodal benchmarks
    _create_test_media(ROOT / "datasets" / "megapipeline" / "test_media")

    elapsed = time.time() - t0
    state["phases"]["1_data_prep"]["status"] = "completed"
    state["phases"]["1_data_prep"]["elapsed_s"] = round(elapsed, 1)
    state["phase"] = 1
    save_state(state)
    log.info(f"Phase 1 complete in {elapsed:.1f}s")
    return state


def _create_test_media(media_dir: Path):
    """Generate synthetic images, audio, and video for benchmarks."""
    import numpy as np

    # --- Test images ---
    try:
        from PIL import Image, ImageDraw, ImageFont

        # 1. Chart-like image
        img = Image.new("RGB", (640, 480), "white")
        draw = ImageDraw.Draw(img)
        bars = [("Normal", 180), ("Bloomington", 220), ("Chicago", 400), ("ISU Area", 90)]
        for i, (label, h) in enumerate(bars):
            x = 80 + i * 130
            color = ["#4285F4", "#EA4335", "#FBBC04", "#34A853"][i]
            draw.rectangle([x, 400 - h, x + 100, 400], fill=color)
            draw.text((x + 20, 410), label, fill="black")
            draw.text((x + 40, 395 - h), str(h), fill="black")
        draw.text((200, 20), "Population (thousands)", fill="black")
        img.save(str(media_dir / "chart_population.png"))

        # 2. Text document image (OCR test)
        img2 = Image.new("RGB", (640, 480), "white")
        draw2 = ImageDraw.Draw(img2)
        lines = [
            "TOWN OF NORMAL, ILLINOIS",
            "Council Meeting Minutes - March 2026",
            "",
            "Agenda Item 1: Budget Review",
            "The FY2026 budget of $142.3M was discussed.",
            "Key allocations:",
            "  - Public Safety: $38.2M (26.8%)",
            "  - Infrastructure: $24.1M (16.9%)",
            "  - Education Support: $18.7M (13.1%)",
            "",
            "Motion to approve passed 5-2.",
        ]
        y = 30
        for line in lines:
            draw2.text((30, y), line, fill="black")
            y += 35
        img2.save(str(media_dir / "document_minutes.png"))

        # 3. Safety hazard image
        img3 = Image.new("RGB", (640, 480), "#FFF3E0")
        draw3 = ImageDraw.Draw(img3)
        # Warning triangle
        draw3.polygon([(320, 50), (200, 300), (440, 300)], fill="#FF9800", outline="#E65100")
        draw3.text((270, 150), "!", fill="white")
        draw3.text((220, 320), "CAUTION: WET FLOOR", fill="#E65100")
        draw3.text((180, 360), "Report hazards to x4567", fill="#666666")
        img3.save(str(media_dir / "safety_hazard.png"))

        # 4. Map-like image
        img4 = Image.new("RGB", (640, 480), "#E8F5E9")
        draw4 = ImageDraw.Draw(img4)
        draw4.rectangle([200, 150, 440, 330], outline="#2E7D32", width=3)
        draw4.text((260, 220), "ISU CAMPUS", fill="#1B5E20")
        draw4.ellipse([280, 160, 360, 200], fill="#F44336")
        draw4.text((285, 167), "Quad", fill="white")
        draw4.line([(100, 240), (540, 240)], fill="#666", width=2)
        draw4.text((105, 245), "College Ave", fill="#333")
        draw4.line([(320, 80), (320, 400)], fill="#666", width=2)
        draw4.text((325, 85), "School St", fill="#333")
        img4.save(str(media_dir / "campus_map.png"))

        # 5. Data table image
        img5 = Image.new("RGB", (640, 480), "white")
        draw5 = ImageDraw.Draw(img5)
        draw5.text((30, 20), "Chicago Crime Summary 2024-2026", fill="black")
        headers = ["Year", "Theft", "Battery", "Assault", "Total"]
        data_rows = [
            ["2024", "45,230", "28,100", "12,800", "86,130"],
            ["2025", "43,100", "26,900", "11,500", "81,500"],
            ["2026*", "10,200", "6,800", "2,900", "19,900"],
        ]
        y = 60
        for col_i, h in enumerate(headers):
            draw5.text((30 + col_i * 120, y), h, fill="#1565C0")
        y += 30
        for row in data_rows:
            for col_i, val in enumerate(row):
                draw5.text((30 + col_i * 120, y), val, fill="black")
            y += 30
        img5.save(str(media_dir / "crime_table.png"))

        log.info(f"Created 5 test images in {media_dir}")
    except ImportError:
        log.warning("PIL not available — image benchmarks will be skipped")

    # --- Test audio ---
    try:
        sr = 16000
        # 1. Pure tone (440Hz A note) — classification test
        t = np.linspace(0, 3.0, int(sr * 3.0), dtype=np.float32)
        tone = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        _write_wav(media_dir / "tone_440hz.wav", tone, sr)

        # 2. Multi-tone (chord) — more complex audio
        chord = (
            0.3 * np.sin(2 * np.pi * 261.63 * t) +
            0.3 * np.sin(2 * np.pi * 329.63 * t) +
            0.3 * np.sin(2 * np.pi * 392.00 * t)
        ).astype(np.float32)
        _write_wav(media_dir / "chord_cmajor.wav", chord, sr)

        # 3. Siren-like sound — emergency audio
        freq = 500 + 300 * np.sin(2 * np.pi * 2 * t)
        siren = (0.5 * np.sin(2 * np.pi * freq * t / sr * 50)).astype(np.float32)
        _write_wav(media_dir / "siren_sweep.wav", siren, sr)

        log.info(f"Created 3 test audio files in {media_dir}")
    except Exception as e:
        log.warning(f"Audio creation failed: {e}")


def _write_wav(path: Path, data, sr: int):
    """Write float32 mono audio to WAV."""
    import struct
    n = len(data)
    pcm = (data * 32767).clip(-32768, 32767).astype("<i2").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(pcm)))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16))
        f.write(b"data")
        f.write(struct.pack("<I", len(pcm)))
        f.write(pcm)


def run_phase_2_synth(holder: ModelHolder, state: dict) -> dict:
    log.info("═══ Phase 2: Synthetic Dataset Generation ═══")
    from pipeline.e4b_civic_synth import run_synth_generation
    t0 = time.time()
    result = run_synth_generation(holder, safe_generate, state)
    elapsed = time.time() - t0
    state["phases"]["2_synth_gen"]["status"] = "completed"
    state["phases"]["2_synth_gen"]["elapsed_s"] = round(elapsed, 1)
    state["phases"]["2_synth_gen"]["items_done"] = result.get("total_items", 0)
    state["phase"] = 2
    save_state(state)
    log.info(f"Phase 2 complete in {elapsed:.1f}s — {result.get('total_items', 0)} items")
    return state


def run_phase_3_bench(holder: ModelHolder, state: dict) -> dict:
    log.info("═══ Phase 3: Comprehensive Benchmarks ═══")
    from pipeline.e4b_multimodal_bench import run_all_benchmarks
    t0 = time.time()
    result = run_all_benchmarks(holder, safe_generate, state)
    elapsed = time.time() - t0
    state["phases"]["3_benchmarks"]["status"] = "completed"
    state["phases"]["3_benchmarks"]["elapsed_s"] = round(elapsed, 1)
    state["phases"]["3_benchmarks"]["items_done"] = result.get("total_tests", 0)
    state["phase"] = 3
    save_state(state)
    log.info(f"Phase 3 complete in {elapsed:.1f}s — {result.get('total_tests', 0)} tests")
    return state


def run_phase_4_rag(holder: ModelHolder, state: dict) -> dict:
    log.info("═══ Phase 4: RAG vs Knowledge-Graph Comparison ═══")
    from pipeline.rag_vs_kg import run_rag_comparison
    t0 = time.time()
    result = run_rag_comparison(holder, safe_generate, state)
    elapsed = time.time() - t0
    state["phases"]["4_rag_compare"]["status"] = "completed"
    state["phases"]["4_rag_compare"]["elapsed_s"] = round(elapsed, 1)
    state["phase"] = 4
    save_state(state)
    log.info(f"Phase 4 complete in {elapsed:.1f}s")
    return state


def run_phase_5_export(holder: ModelHolder, state: dict) -> dict:
    log.info("═══ Phase 5: Export & Packaging ═══")
    t0 = time.time()

    results_dir = ROOT / "benchmarks" / "results" / "megapipeline"
    synth_dir = ROOT / "datasets" / "synthetic"
    kaggle_dir = ROOT / "artifacts" / "kaggle_upload"
    card_dir = ROOT / "artifacts" / "model_card"

    # Aggregate benchmark results into a single summary
    all_results = {}
    for rfile in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(rfile.read_text("utf-8"))
            all_results[rfile.stem] = data
        except Exception:
            pass

    summary = {
        "model": "gemma-4-E4B-it",
        "precision": "bf16",
        "device": "RTX 5090 32GB",
        "pipeline_version": "megapipeline-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_state": state,
        "benchmark_files": list(all_results.keys()),
        "synthetic_datasets": [f.name for f in synth_dir.glob("*.jsonl")] if synth_dir.exists() else [],
    }

    # Compute aggregate scores per category
    category_scores = {}
    for fname, data in all_results.items():
        if "benchmarks" in data:
            for bench_name, bench_data in data["benchmarks"].items():
                cat = bench_data.get("category", "unknown")
                score = bench_data.get("avg_score", 0)
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(score)
    for cat, scores in category_scores.items():
        summary[f"avg_{cat}"] = round(sum(scores) / len(scores), 4) if scores else 0

    (card_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), "utf-8"
    )

    # Package synthetic datasets for Kaggle upload
    kaggle_meta = {
        "title": "Jemma SafeBrain Civic QA — Gemma 4 Synthetic Dataset",
        "subtitle": "Synthetic QA pairs for Normal IL, ISU, and Chicago generated by Gemma 4 E4B",
        "description": (
            "Question-answer pairs about the Town of Normal IL, Illinois State University, "
            "and Chicago public safety, generated by Gemma 4 E4B-it at bf16 precision. "
            "Includes multi-turn conversations, safety scenarios, structured data, and "
            "civic knowledge assessment. Generated for the Gemma 4 Good Hackathon."
        ),
        "licenses": [{"name": "Apache 2.0"}],
        "keywords": ["gemma-4", "civic", "qa", "synthetic", "normal-il", "isu", "safety"],
        "resources": [],
    }
    for f in synth_dir.glob("*.jsonl"):
        lines = sum(1 for _ in open(f, "r", encoding="utf-8"))
        kaggle_meta["resources"].append({"path": f.name, "description": f.stem, "rows": lines})
        shutil.copy2(f, kaggle_dir / f.name)

    (kaggle_dir / "dataset-metadata.json").write_text(
        json.dumps(kaggle_meta, indent=2), "utf-8"
    )

    elapsed = time.time() - t0
    state["phases"]["5_export"]["status"] = "completed"
    state["phases"]["5_export"]["elapsed_s"] = round(elapsed, 1)
    state["phase"] = 5
    save_state(state)
    log.info(f"Phase 5 complete in {elapsed:.1f}s")
    log.info(f"Kaggle dataset ready at: {kaggle_dir}")
    log.info(f"Model card artifacts at: {card_dir}")
    return state


# ---------------------------------------------------------------------------
# Self-healing phase runner
# ---------------------------------------------------------------------------
def run_phase_safe(phase_fn, holder: ModelHolder, state: dict, phase_key: str) -> dict:
    """Execute a phase with crash recovery and model reload."""
    max_phase_retries = 3
    for attempt in range(max_phase_retries):
        try:
            state["phases"][phase_key]["status"] = "in_progress"
            save_state(state)
            state = phase_fn(holder, state)
            return state
        except torch.cuda.OutOfMemoryError:
            state["oom_recoveries"] = state.get("oom_recoveries", 0) + 1
            log.error(f"Phase {phase_key} OOM (attempt {attempt+1})")
            torch.cuda.empty_cache()
            gc.collect()
            torch.cuda.empty_cache()
            if attempt < max_phase_retries - 1:
                holder.reload()
                state["model_loads"] = holder.loads
                save_state(state)
            else:
                state["phases"][phase_key]["status"] = "failed_oom"
                state["errors"].append(f"{phase_key}: OOM after {max_phase_retries} retries")
                save_state(state)
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt — saving state and exiting")
            state["phases"][phase_key]["status"] = "interrupted"
            save_state(state)
            raise
        except Exception as e:
            log.error(f"Phase {phase_key} error (attempt {attempt+1}): {e}")
            log.debug(traceback.format_exc())
            state["errors"].append(f"{phase_key}: {e}")
            if attempt < max_phase_retries - 1:
                try:
                    holder.reload()
                    state["model_loads"] = holder.loads
                except Exception:
                    log.critical("Model reload failed — aborting phase")
                    state["phases"][phase_key]["status"] = "failed"
                    save_state(state)
                    return state
                save_state(state)
            else:
                state["phases"][phase_key]["status"] = "failed"
                save_state(state)
    return state


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="E4B MegaPipeline")
    parser.add_argument("--fresh", action="store_true", help="Reset state and start from scratch")
    parser.add_argument("--phase", type=int, default=0, help="Resume at specific phase (1-5)")
    parser.add_argument("--dry-run", action="store_true", help="Verify setup without running inference")
    parser.add_argument("--max-hours", type=float, default=168, help="Max runtime in hours (default: 168 = 1 week)")
    args = parser.parse_args()

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║   Jemma E4B MegaPipeline — RTX 5090 bf16    ║")
    log.info("╚══════════════════════════════════════════════╝")

    # State
    if args.fresh:
        state = dict(_DEFAULT_STATE)
    else:
        state = load_state()

    state["started_at"] = state.get("started_at") or datetime.now(timezone.utc).isoformat()
    start_phase = args.phase or (state.get("phase", 0) + 1)
    start_phase = max(1, min(5, start_phase))

    # Dry run — just verify everything loads
    if args.dry_run:
        log.info("DRY RUN — verifying setup …")
        assert torch.cuda.is_available(), "CUDA not available"
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        log.info(f"GPU: {gpu_name} | VRAM: {vram:.1f} GB")
        log.info(f"Civic DB exists: {(ROOT / 'datasets' / 'civic_data.db').exists()}")
        log.info(f"State file: {STATE_PATH}")
        log.info(f"Would start at phase {start_phase}")
        log.info("DRY RUN complete — all checks passed ✓")
        return

    # Start safety watchdog
    from pipeline.safety_watchdog import health, monitor_loop
    watchdog_thread = threading.Thread(target=monitor_loop, daemon=True, name="watchdog")
    watchdog_thread.start()
    log.info("Safety watchdog started")

    # Load model
    holder = ModelHolder()
    holder.load()
    state["model_loads"] = holder.loads
    save_state(state)

    # Deadline guard
    deadline = time.time() + args.max_hours * 3600

    # Phase dispatch table
    phases = [
        (1, "1_data_prep",   run_phase_1_data_prep),
        (2, "2_synth_gen",   run_phase_2_synth),
        (3, "3_benchmarks",  run_phase_3_bench),
        (4, "4_rag_compare", run_phase_4_rag),
        (5, "5_export",      run_phase_5_export),
    ]

    for phase_num, phase_key, phase_fn in phases:
        if phase_num < start_phase:
            continue
        if time.time() > deadline:
            log.warning("Max runtime reached — stopping")
            break
        if health.should_stop:
            log.warning("Watchdog requested stop — saving and exiting")
            break

        log.info(f"▶ Starting phase {phase_num} ({phase_key})")
        state = run_phase_safe(phase_fn, holder, state, phase_key)

        status = state["phases"][phase_key]["status"]
        if status in ("failed", "failed_oom"):
            log.warning(f"Phase {phase_key} failed — continuing to next phase")

    # Final report
    log.info("═══ Pipeline Complete ═══")
    for key, pdata in state["phases"].items():
        log.info(f"  {key}: {pdata['status']} ({pdata.get('elapsed_s', 0):.0f}s)")
    log.info(f"  Model loads: {state.get('model_loads', 0)}")
    log.info(f"  OOM recoveries: {state.get('oom_recoveries', 0)}")
    log.info(f"  Errors: {len(state.get('errors', []))}")

    # Cleanup
    health.should_stop = True
    save_state(state)
    log.info("State saved. Pipeline finished.")


if __name__ == "__main__":
    main()
