#!/usr/bin/env python3
"""
Jemma Pipeline Monitor — Real-time training progress dashboard.

Tails pipeline state, training logs, and GPU health in one view.
Run this in a SEPARATE terminal while training runs.

Usage:
  python toolbox/pipeline_monitor.py                # Full dashboard, 5s refresh
  python toolbox/pipeline_monitor.py --interval 2   # 2s refresh
  python toolbox/pipeline_monitor.py --json          # Machine-readable JSON output
  python toolbox/pipeline_monitor.py --once          # Print once and exit
  python toolbox/pipeline_monitor.py --estimate 1 2  # Time estimate only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"
CHECKPOINTS_DIR = ROOT / "checkpoints"
PREPARED_DIR = ROOT / "datasets" / "prepared"

# ── Time estimates (RTX 5090 32GB, Unsloth QLoRA 4-bit, E4B) ─────────────────
# Based on: ~9-11 tok/s inference, ~600-800 samples/hr training at 2048 seq
# Model load: ~35s, LoRA merge: ~60-90s, GGUF export: ~5-8min per quant
TIME_ESTIMATES = {
    "dataset_prep": {
        "general": {"minutes": 8, "desc": "UltraChat 200K + OpenHermes 2.5 → 35K examples"},
        "domain":  {"minutes": 5, "desc": "OSHA + FEMA + synth repurpose → 30K examples"},
        "toolcall":{"minutes": 4, "desc": "Glaive Function Calling → 15K examples"},
        "dpo":     {"minutes": 10, "desc": "UltraFeedback + HelpSteer2 + Capybara → 40K pref pairs"},
        "safety":  {"minutes": 3, "desc": "Real Toxicity Prompts → 5K refusals"},
    },
    "training": {
        # steps = ceil(examples / effective_batch) * epochs
        # effective_batch = batch_size * grad_accum = 2*8=16 (stages 1,2,5) or 1*8=8 (stage 3)
        # throughput: ~650 samples/hr at seq2048, ~400 samples/hr at seq4096
        1: {"hours": 3.5, "steps_est": 2188, "desc": "General SFT (35K×1ep, batch16, seq2048, lr=2e-4)"},
        2: {"hours": 6.0, "steps_est": 3750, "desc": "Domain SFT (30K×2ep, batch16, seq2048, lr=1e-4)"},
        3: {"hours": 6.0, "steps_est": 3750, "desc": "Tool Calling SFT (15K×2ep, batch8, seq4096, lr=5e-5)"},
        4: {"hours": 4.0, "steps_est": 2500, "desc": "DPO Alignment (40K×1ep, batch8, seq2048, lr=5e-6, β=0.1)"},
        5: {"hours": 1.0, "steps_est": 625,  "desc": "Safety SFT (5K×2ep, batch16, seq2048, lr=5e-5)"},
    },
    "overhead": {
        "model_load":  {"minutes": 1, "desc": "Load model + apply LoRA (per stage)"},
        "lora_merge":  {"minutes": 2, "desc": "Merge LoRA into base (per stage)"},
        "gguf_export": {"minutes": 12, "desc": "GGUF export (Q4_K_M + Q8_0)"},
        "ollama_reg":  {"minutes": 3, "desc": "Ollama model registration"},
        "benchmarks":  {"minutes": 20, "desc": "Full 20-category benchmark suite (~100 questions)"},
    },
}


def get_total_estimate(stages: list[int],
                       skip_export: bool = False,
                       skip_benchmarks: bool = False) -> dict:
    """Calculate total time estimate for given stages."""
    total_min = 0
    breakdown = []

    stage_to_ds = {1: "general", 2: "domain", 3: "toolcall", 4: "dpo", 5: "safety"}

    # Data prep
    for s in stages:
        ds = stage_to_ds.get(s)
        if ds and ds in TIME_ESTIMATES["dataset_prep"]:
            e = TIME_ESTIMATES["dataset_prep"][ds]
            total_min += e["minutes"]
            breakdown.append(("data", f"Prep {ds}", f"~{e['minutes']}min", e["desc"]))

    # Training + per-stage overhead
    for s in stages:
        if s in TIME_ESTIMATES["training"]:
            e = TIME_ESTIMATES["training"][s]
            overhead = TIME_ESTIMATES["overhead"]["model_load"]["minutes"] + \
                       TIME_ESTIMATES["overhead"]["lora_merge"]["minutes"]
            total_min += e["hours"] * 60 + overhead
            breakdown.append(("train", f"Stage {s}", f"~{e['hours']}h", e["desc"]))

    # Export
    if not skip_export:
        e = TIME_ESTIMATES["overhead"]["gguf_export"]
        total_min += e["minutes"]
        breakdown.append(("export", "GGUF export", f"~{e['minutes']}min", e["desc"]))
        e = TIME_ESTIMATES["overhead"]["ollama_reg"]
        total_min += e["minutes"]
        breakdown.append(("export", "Ollama register", f"~{e['minutes']}min", e["desc"]))

    # Benchmarks
    if not skip_benchmarks:
        e = TIME_ESTIMATES["overhead"]["benchmarks"]
        total_min += e["minutes"]
        breakdown.append(("bench", "Benchmarks", f"~{e['minutes']}min", e["desc"]))

    return {"total_hours": round(total_min / 60, 1), "total_minutes": round(total_min),
            "breakdown": breakdown}


# ── GPU Query ────────────────────────────────────────────────────────────────

def query_gpu() -> dict:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,fan.speed,power.draw,power.limit,"
             "memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        parts = [p.strip() for p in r.stdout.strip().split(",")]
        if len(parts) >= 8:
            return {
                "name": parts[0], "temp_c": int(parts[1]),
                "fan_pct": parts[2], "power_w": float(parts[3]),
                "power_limit_w": float(parts[4]),
                "vram_used_mb": int(parts[5]), "vram_total_mb": int(parts[6]),
                "gpu_util_pct": int(parts[7]),
            }
    except Exception:
        pass
    return {"name": "Unknown", "temp_c": 0, "vram_used_mb": 0, "vram_total_mb": 0,
            "power_w": 0, "power_limit_w": 0, "gpu_util_pct": 0}


# ── State Readers ────────────────────────────────────────────────────────────

def read_pipeline_state() -> dict:
    p = STATE_DIR / "pipeline_state.json"
    if p.exists():
        try:
            return json.loads(p.read_text("utf-8"))
        except Exception:
            pass
    return {}


def read_stage_states() -> dict[int, dict]:
    states = {}
    for f in STATE_DIR.glob("stage*_*state.json"):
        try:
            data = json.loads(f.read_text("utf-8"))
            stage = data.get("stage")
            if stage:
                states[stage] = data
        except Exception:
            continue
    return states


def read_datasets_status() -> dict[str, dict]:
    status = {}
    for f in sorted(PREPARED_DIR.glob("*.jsonl")):
        try:
            n = sum(1 for _ in open(f, "r", encoding="utf-8"))
            size_mb = f.stat().st_size / (1024 * 1024)
            status[f.stem] = {"examples": n, "size_mb": round(size_mb, 1)}
        except Exception:
            status[f.stem] = {"examples": 0, "size_mb": 0}
    return status


def read_training_progress_from_log() -> dict:
    """Parse the most recent training progress from state + log files."""
    progress = {"stage": None, "step": 0, "total_steps": 0, "loss": None,
                "lr": None, "epoch": 0.0, "speed_samples_s": None,
                "started_at": None, "last_log_at": None, "eta_s": None}

    # First try the real-time progress file (written by ProgressCallback)
    progress_file = STATE_DIR / "training_progress.json"
    if progress_file.exists():
        try:
            data = json.loads(progress_file.read_text("utf-8"))
            # Only use if recent (within last 5 minutes)
            ts = data.get("timestamp", "")
            if ts:
                age_s = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
                if age_s < 300:
                    progress["stage"] = data.get("stage")
                    progress["step"] = data.get("global_step", 0)
                    progress["total_steps"] = data.get("max_steps", 0)
                    progress["loss"] = data.get("loss")
                    progress["lr"] = data.get("learning_rate")
                    progress["epoch"] = data.get("epoch", 0)
                    progress["speed_samples_s"] = data.get("samples_per_s")
                    progress["eta_s"] = data.get("eta_s")
                    progress["last_log_at"] = ts[:19]
                    return progress
        except Exception:
            pass

    # Fallback: parse log files

    # Try SFT log first, then DPO
    for log_name in ["train_sft.log", "train_dpo.log"]:
        log_path = LOGS_DIR / log_name
        if not log_path.exists():
            continue

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-300:]
        except Exception:
            continue

        for line in reversed(lines):
            # Extract stage
            if progress["stage"] is None:
                m = re.search(r"Stage\s+(\d+)", line)
                if m:
                    progress["stage"] = int(m.group(1))

            # HF Trainer log format: {'loss': 1.23, 'learning_rate': 2e-4, 'epoch': 0.5}
            if "'loss'" in line and progress["loss"] is None:
                m = re.search(r"\{[^}]+\}", line)
                if m:
                    try:
                        d = json.loads(m.group().replace("'", '"'))
                        progress["loss"] = d.get("loss")
                        progress["lr"] = d.get("learning_rate")
                        progress["epoch"] = d.get("epoch", 0)
                    except Exception:
                        pass

            # Timestamps
            m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if m and progress["last_log_at"] is None:
                progress["last_log_at"] = m.group(1)

            # Training complete
            if "Training complete" in line and "complete in" in line:
                m = re.search(r"(\d+\.?\d*)h", line)
                if m:
                    progress["total_elapsed_h"] = float(m.group(1))

            # Final loss
            if "Final loss:" in line:
                m = re.search(r"Final loss:\s*(\d+\.?\d*)", line)
                if m:
                    progress["final_loss"] = float(m.group(1))

        if progress["stage"]:
            break

    return progress


def read_gpu_health_log(n: int = 5) -> list[dict]:
    health_log = LOGS_DIR / "gpu_health.jsonl"
    if not health_log.exists():
        return []
    try:
        with open(health_log, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []


# ── Dashboard Render ─────────────────────────────────────────────────────────

def render_dashboard() -> str:
    gpu = query_gpu()
    pipe_state = read_pipeline_state()
    stage_states = read_stage_states()
    datasets = read_datasets_status()
    training = read_training_progress_from_log()

    lines = []
    now = datetime.now().strftime("%H:%M:%S")

    # Header
    lines.append("")
    lines.append(f"  {'='*56}")
    lines.append(f"   JEMMA PIPELINE MONITOR                       {now}")
    lines.append(f"  {'='*56}")

    # GPU
    vram_pct = (gpu["vram_used_mb"] / gpu["vram_total_mb"] * 100) if gpu["vram_total_mb"] else 0
    vram_bar = "#" * int(vram_pct / 5) + "-" * (20 - int(vram_pct / 5))
    if gpu["temp_c"] >= 85:
        temp_tag = "!! THROTTLE"
    elif gpu["temp_c"] >= 80:
        temp_tag = "! WARNING"
    elif gpu["temp_c"] >= 70:
        temp_tag = "WARM"
    else:
        temp_tag = "OK"

    lines.append(f"")
    lines.append(f"   GPU: {gpu['name']}")
    lines.append(f"   Temp: {gpu['temp_c']}C ({temp_tag})  |  Power: {gpu['power_w']:.0f}/{gpu['power_limit_w']:.0f}W  |  Util: {gpu['gpu_util_pct']}%")
    lines.append(f"   VRAM: [{vram_bar}] {gpu['vram_used_mb']}/{gpu['vram_total_mb']}MB ({vram_pct:.0f}%)")

    # Pipeline Status
    completed = pipe_state.get("completed_stages", [])
    lines.append(f"")
    lines.append(f"   -- Pipeline Status --")
    if pipe_state.get("started"):
        lines.append(f"   Started: {pipe_state['started']}")
    lines.append(f"   Completed stages: {completed if completed else 'none'}")
    if pipe_state.get("total_hours"):
        lines.append(f"   Total elapsed: {pipe_state['total_hours']}h")
    if pipe_state.get("errors"):
        for err in pipe_state["errors"][-3:]:
            lines.append(f"   !! ERROR: {str(err)[:80]}")

    # Datasets
    lines.append(f"")
    lines.append(f"   -- Datasets --")
    expected = [("stage1_general_sft", "General SFT"),
                ("stage2_domain_sft", "Domain SFT"),
                ("stage3_toolcall_sft", "Tool Calling"),
                ("stage4_dpo", "DPO Prefs"),
                ("stage5_safety_sft", "Safety")]
    for name, label in expected:
        if name in datasets:
            ds = datasets[name]
            lines.append(f"   [x] {label:<16} {ds['examples']:>7,} examples  ({ds['size_mb']:>6.1f} MB)")
        else:
            lines.append(f"   [ ] {label:<16} not prepared")

    # Active Training
    if training.get("stage"):
        lines.append(f"")
        lines.append(f"   -- Active Training (Stage {training['stage']}) --")
        if training.get("loss") is not None:
            lines.append(f"   Loss: {training['loss']:.4f}  |  LR: {training.get('lr', 0):.2e}  |  Epoch: {training.get('epoch', 0):.2f}")
        if training.get("last_log_at"):
            lines.append(f"   Last log: {training['last_log_at']}")
        if training.get("final_loss") is not None:
            lines.append(f"   ** Completed!  Final loss: {training['final_loss']:.4f}")
    else:
        lines.append(f"")
        lines.append(f"   -- Training: idle --")

    # Completed Stages Detail
    if stage_states:
        lines.append(f"")
        lines.append(f"   -- Completed Stage Results --")
        for snum in sorted(stage_states.keys()):
            s = stage_states[snum]
            lines.append(
                f"   Stage {snum}: loss={s.get('training_loss', 0):.4f}  "
                f"steps={s.get('global_step', '?')}  "
                f"time={s.get('elapsed_hours', 0):.1f}h  "
                f"examples={s.get('num_examples', '?')}"
            )

    # Checkpoints on disk
    cp_dirs = sorted(d for d in CHECKPOINTS_DIR.glob("stage*") if d.is_dir())
    if cp_dirs:
        lines.append(f"")
        lines.append(f"   -- Checkpoints --")
        for d in cp_dirs:
            try:
                size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024**2)
                lines.append(f"   {d.name}: {size_mb:,.0f} MB")
            except Exception:
                lines.append(f"   {d.name}: (calculating...)")

    # Export status
    export_state_path = STATE_DIR / "export_state.json"
    if export_state_path.exists():
        try:
            es = json.loads(export_state_path.read_text("utf-8"))
            lines.append(f"")
            lines.append(f"   -- Export --")
            for q, p in es.get("exported", {}).items():
                lines.append(f"   GGUF {q}: {p}")
            for q, ok in es.get("ollama_registered", {}).items():
                lines.append(f"   Ollama {q}: {'registered' if ok else 'FAILED'}")
        except Exception:
            pass

    lines.append(f"")
    lines.append(f"  {'='*56}")
    lines.append(f"   Ctrl+C to stop  |  Logs: logs/train_sft.log")
    lines.append(f"  {'='*56}")

    return "\n".join(lines)


def render_json() -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpu": query_gpu(),
        "pipeline": read_pipeline_state(),
        "stages": {str(k): v for k, v in read_stage_states().items()},
        "datasets": read_datasets_status(),
        "training": read_training_progress_from_log(),
    }, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Jemma Pipeline Monitor")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval (seconds)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--once", action="store_true", help="Print once and exit")
    parser.add_argument("--estimate", nargs="*", type=int, default=None,
                        help="Print time estimate for stages (e.g., --estimate 1 2 4)")
    args = parser.parse_args()

    # Time estimate mode
    if args.estimate is not None:
        stages = args.estimate or [1, 2, 3, 4, 5]
        est = get_total_estimate(stages)
        print(f"\n  Time Estimate for Stages {stages}  (RTX 5090 32GB, QLoRA 4-bit)")
        print(f"  {'='*56}")
        print(f"  {'Phase':<8} {'Step':<20} {'Time':<10} Description")
        print(f"  {'-'*8} {'-'*20} {'-'*10} {'-'*30}")
        for phase, step, time_str, desc in est["breakdown"]:
            print(f"  {phase:<8} {step:<20} {time_str:<10} {desc}")
        print(f"  {'='*56}")
        print(f"  TOTAL: ~{est['total_hours']}h ({est['total_minutes']} min)")

        # Show stage combos
        fast = get_total_estimate([1, 2])
        med = get_total_estimate([1, 2, 4])
        full = get_total_estimate([1, 2, 3, 4, 5])
        print(f"\n  Quick plans:")
        print(f"    80/20 play  (stages 1+2):       ~{fast['total_hours']}h")
        print(f"    SFT + DPO   (stages 1+2+4):     ~{med['total_hours']}h")
        print(f"    Full pipeline (stages 1-5):      ~{full['total_hours']}h")
        return

    if args.once:
        print(render_json() if args.json else render_dashboard())
        return

    try:
        while True:
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")
            print(render_json() if args.json else render_dashboard())
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


if __name__ == "__main__":
    main()
