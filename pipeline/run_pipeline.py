#!/usr/bin/env python3
"""
Jemma Training Pipeline — Master Orchestrator (v2).

Runs the complete training pipeline end-to-end with:
  - Auto-retry on transient failures (OOM, network, disk)
  - Loss sanity checks after each stage (detects divergence/NaN)
  - GPU health pre-flight and inter-stage cooldown
  - Rich state tracking with per-step timing and error history
  - Resume from any point after crash or interruption

Stages:
  1. Dataset preparation (download + format)
  2. Stage 1 SFT: General capability
  3. Stage 2 SFT: Domain specialization
  4. Stage 3 SFT: Tool calling (optional)
  5. Stage 4 DPO: Alignment (optional)
  6. Stage 5 SFT: Safety refusals (optional)
  7. Final benchmarks
  8. GGUF export + Ollama registration

Usage:
  python pipeline/run_pipeline.py                     # Full pipeline
  python pipeline/run_pipeline.py --stages 1 2        # 80/20 play (~10h)
  python pipeline/run_pipeline.py --stages 1 2 4      # SFT + DPO (~14h)
  python pipeline/run_pipeline.py --resume             # Resume after crash
  python pipeline/run_pipeline.py --max-retries 3      # Retry failed stages
  python pipeline/run_pipeline.py --estimate            # Print time estimate only
  python pipeline/run_pipeline.py --preflight           # GPU/env check only

Monitor in a second terminal:
  python toolbox/pipeline_monitor.py                   # Live dashboard
  python toolbox/pipeline_monitor.py --estimate 1 2    # Time estimate
  Get-Content logs/pipeline_master.log -Wait -Tail 20  # Tail log
"""
from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback as tb
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"
CHECKPOINTS_DIR = ROOT / "checkpoints"
PREPARED_DIR = ROOT / "datasets" / "prepared"

for d in [LOGS_DIR, STATE_DIR, CHECKPOINTS_DIR, PREPARED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "pipeline"))

log = logging.getLogger("pipeline")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh = logging.FileHandler(LOGS_DIR / "pipeline_master.log", encoding="utf-8")
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
if not log.handlers:
    log.addHandler(_fh)
    log.addHandler(_sh)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_RETRIES_DEFAULT = 2
COOLDOWN_BETWEEN_STAGES_S = 30      # GPU cooldown between stages
LOSS_SANITY_THRESHOLD = 15.0        # Loss above this = likely diverged
LOSS_NAN_IS_FATAL = True            # NaN loss = stop immediately
MIN_DISK_GB = 10                    # Abort if less than this free
MIN_VRAM_MB = 8000                  # Need at least 8GB free to start training

STAGE_ORDER = [1, 2, 3, 4, 5]      # Canonical execution order
STAGE_NAMES = {
    1: "General SFT", 2: "Domain SFT", 3: "Tool Calling SFT",
    4: "DPO Alignment", 5: "Safety SFT",
}
STAGE_TO_DATASET = {1: "general", 2: "domain", 3: "toolcall", 4: "dpo", 5: "safety"}


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class PipelineState:
    """Rich pipeline state with atomic persistence."""

    _path = STATE_DIR / "pipeline_state.json"

    def __init__(self):
        self.started: str | None = None
        self.completed_stages: list[int] = []
        self.failed_stages: dict[int, dict] = {}  # stage -> {error, attempt, timestamp}
        self.stage_timings: dict[int, dict] = {}   # stage -> {start, end, hours, loss}
        self.current_phase: str = "idle"           # idle|preflight|data|training|dpo|benchmarks|export
        self.current_stage: int | None = None
        self.errors: list[dict] = []               # [{stage, error, timestamp, attempt}]
        self.total_hours: float = 0
        self.completed: str | None = None
        self.retries_used: dict[int, int] = {}     # stage -> retry count

    def save(self):
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.__dict__, indent=2, default=str), "utf-8")
        tmp.replace(self._path)  # Atomic rename

    @classmethod
    def load(cls) -> "PipelineState":
        s = cls()
        if cls._path.exists():
            try:
                data = json.loads(cls._path.read_text("utf-8"))
                for k, v in data.items():
                    if hasattr(s, k):
                        setattr(s, k, v)
            except Exception:
                pass
        return s

    def record_error(self, stage: int, error: str, attempt: int):
        entry = {
            "stage": stage, "error": error[:500],
            "attempt": attempt, "timestamp": _now(),
        }
        self.errors.append(entry)
        # Keep last 50 errors
        if len(self.errors) > 50:
            self.errors = self.errors[-50:]
        self.failed_stages[str(stage)] = entry
        self.save()

    def record_stage_complete(self, stage: int, loss: float, hours: float):
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)
        self.stage_timings[str(stage)] = {
            "loss": loss, "hours": round(hours, 2), "completed_at": _now(),
        }
        self.current_stage = None
        # Clear from failed if it recovered
        self.failed_stages.pop(str(stage), None)
        self.save()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def preflight_check() -> list[str]:
    """Run pre-flight environment checks. Returns list of issues (empty = all good)."""
    issues = []

    log.info("  Pre-flight checks...")

    # 1. GPU available
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.free,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        parts = [p.strip() for p in r.stdout.strip().split(",")]
        if len(parts) >= 3:
            gpu_name = parts[0]
            free_mb = int(parts[1])
            temp = int(parts[2])
            log.info(f"  GPU: {gpu_name} | Free VRAM: {free_mb}MB | Temp: {temp}C")
            if free_mb < MIN_VRAM_MB:
                issues.append(f"Low VRAM: {free_mb}MB free (need {MIN_VRAM_MB}MB). "
                              f"Close other GPU apps or unload Ollama models.")
            if temp >= 80:
                issues.append(f"GPU already at {temp}C — let it cool before training.")
        else:
            issues.append("nvidia-smi returned unexpected output")
    except FileNotFoundError:
        issues.append("nvidia-smi not found — no GPU available")
    except Exception as e:
        issues.append(f"GPU check failed: {e}")

    # 2. Disk space
    free_gb = shutil.disk_usage(str(ROOT)).free / (1024**3)
    log.info(f"  Disk: {free_gb:.1f}GB free")
    if free_gb < MIN_DISK_GB:
        issues.append(f"Low disk: {free_gb:.1f}GB free (need {MIN_DISK_GB}GB)")

    # 3. Python packages
    missing = []
    for pkg in ["torch", "unsloth", "transformers", "trl", "datasets", "peft"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        issues.append(f"Missing packages: {missing}. Run: pip install {' '.join(missing)}")
    else:
        log.info(f"  Packages: all required packages found")

    # 4. CUDA available
    try:
        import torch
        if not torch.cuda.is_available():
            issues.append("PyTorch CUDA not available")
        else:
            log.info(f"  CUDA: {torch.version.cuda} | PyTorch: {torch.__version__}")
    except ImportError:
        pass  # Already caught above

    # 5. Ollama (non-blocking)
    try:
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            log.info(f"  Ollama: running ({len(models)} models)")
    except Exception:
        log.info(f"  Ollama: not running (export will start it later)")

    if issues:
        for issue in issues:
            log.warning(f"  !! {issue}")
    else:
        log.info(f"  All pre-flight checks passed")

    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-CORRECTION / RETRY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def classify_error(error: Exception) -> str:
    """Classify an error to determine retry strategy."""
    msg = str(error).lower()

    if "cuda" in msg and ("out of memory" in msg or "oom" in msg):
        return "oom"
    if "nan" in msg or "inf" in msg:
        return "nan_loss"
    if any(k in msg for k in ["connection", "timeout", "urlopen", "network", "http"]):
        return "network"
    if any(k in msg for k in ["no space", "disk", "oserror", "permission"]):
        return "disk"
    if "filenotfound" in msg or "no such file" in msg:
        return "missing_data"
    if "import" in msg or "module" in msg:
        return "import"
    return "unknown"


def auto_fix(error_class: str, stage: int, attempt: int) -> str | None:
    """Attempt automatic fix. Returns description of fix applied, or None."""

    if error_class == "oom":
        log.info("  AUTO-FIX: Clearing GPU cache and reducing effective batch size...")
        try:
            import torch
            torch.cuda.empty_cache()
            gc.collect()
            torch.cuda.empty_cache()
        except Exception:
            pass
        # Reduce batch size for retry by modifying config in-memory
        from train_sft import STAGE_CONFIGS
        cfg = STAGE_CONFIGS.get(stage)
        if cfg and attempt == 1:
            old_batch = cfg["per_device_train_batch_size"]
            cfg["per_device_train_batch_size"] = max(1, old_batch // 2)
            cfg["gradient_accumulation_steps"] = cfg["gradient_accumulation_steps"] * 2
            return (f"Halved batch {old_batch}→{cfg['per_device_train_batch_size']}, "
                    f"doubled grad_accum to {cfg['gradient_accumulation_steps']}")
        elif cfg and attempt >= 2:
            old_seq = cfg["max_seq_length"]
            cfg["max_seq_length"] = max(512, old_seq // 2)
            return f"Halved max_seq_length {old_seq}→{cfg['max_seq_length']}"
        return "Cleared GPU cache"

    if error_class == "network":
        log.info(f"  AUTO-FIX: Network error, waiting 30s before retry...")
        time.sleep(30)
        return "Waited 30s for network recovery"

    if error_class == "nan_loss":
        log.info(f"  AUTO-FIX: NaN loss detected, reducing learning rate...")
        from train_sft import STAGE_CONFIGS
        cfg = STAGE_CONFIGS.get(stage)
        if cfg:
            old_lr = cfg["learning_rate"]
            cfg["learning_rate"] = old_lr / 3
            return f"Reduced LR {old_lr:.1e}→{cfg['learning_rate']:.1e}"
        return None

    if error_class == "missing_data":
        log.info(f"  AUTO-FIX: Missing dataset, attempting to prepare...")
        try:
            from dataset_prep import STAGE_MAP
            ds_name = STAGE_TO_DATASET.get(stage)
            if ds_name and ds_name in STAGE_MAP:
                STAGE_MAP[ds_name]()
                return f"Re-prepared dataset for stage {stage}"
        except Exception as e:
            log.error(f"  AUTO-FIX: Dataset prep also failed: {e}")
        return None

    return None


def inter_stage_cooldown(seconds: int = COOLDOWN_BETWEEN_STAGES_S):
    """Cool GPU between training stages."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
            torch.cuda.empty_cache()
    except Exception:
        pass

    log.info(f"  Cooldown: {seconds}s pause between stages...")
    # Check temperature
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        temp = int(r.stdout.strip())
        if temp >= 75:
            log.info(f"  GPU at {temp}C, extending cooldown to 60s...")
            seconds = max(seconds, 60)
        if temp >= 80:
            log.warning(f"  GPU at {temp}C! Extending cooldown to 120s...")
            seconds = max(seconds, 120)
    except Exception:
        pass

    time.sleep(seconds)


def validate_training_result(stage: int, state_file: Path) -> tuple[bool, str]:
    """Validate that training produced reasonable results."""
    if not state_file.exists():
        return False, "No training state file produced"

    try:
        data = json.loads(state_file.read_text("utf-8"))
    except Exception as e:
        return False, f"Can't read state file: {e}"

    loss = data.get("training_loss")
    if loss is None:
        return False, "No training_loss in state"

    import math
    if math.isnan(loss) or math.isinf(loss):
        return False, f"Training loss is {loss} (NaN/Inf — divergence)"

    if loss > LOSS_SANITY_THRESHOLD:
        return False, f"Training loss {loss:.4f} exceeds sanity threshold {LOSS_SANITY_THRESHOLD}"

    steps = data.get("global_step", 0)
    if steps < 10:
        return False, f"Only {steps} steps completed — likely crashed early"

    # Check merged checkpoint exists
    merged = data.get("merged_checkpoint")
    if merged and not Path(merged).exists():
        return False, f"Merged checkpoint missing: {merged}"

    return True, f"OK (loss={loss:.4f}, steps={steps})"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(stages: list[int], skip_benchmarks: bool = False,
                 skip_export: bool = False, resume: bool = False,
                 max_retries: int = MAX_RETRIES_DEFAULT):
    """Execute the Jemma training pipeline with retry and self-correction."""

    state = PipelineState.load() if resume else PipelineState()
    state.started = state.started or _now()
    state.current_phase = "starting"
    state.save()

    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║    Jemma Training Pipeline v2 — Master Orchestrator  ║")
    log.info("╠══════════════════════════════════════════════════════╣")
    log.info(f"║  Stages:      {str(stages):<40}║")
    log.info(f"║  Max retries: {max_retries:<40}║")
    log.info(f"║  Benchmarks:  {'skip' if skip_benchmarks else 'enabled':<40}║")
    log.info(f"║  Export:      {'skip' if skip_export else 'enabled':<40}║")
    if resume:
        log.info(f"║  Resuming:    completed={state.completed_stages!s:<27}║")
    log.info("╚══════════════════════════════════════════════════════╝")

    t_pipeline = time.perf_counter()

    # ── Pre-flight ────────────────────────────────────────────────────────
    state.current_phase = "preflight"
    state.save()
    issues = preflight_check()
    if issues:
        log.warning(f"  {len(issues)} pre-flight issue(s) found. Continuing with caution.")

    # ── Print time estimate ───────────────────────────────────────────────
    try:
        sys.path.insert(0, str(ROOT / "toolbox"))
        from pipeline_monitor import get_total_estimate
        est = get_total_estimate(stages, skip_export, skip_benchmarks)
        log.info(f"\n  Estimated total time: ~{est['total_hours']}h ({est['total_minutes']}min)")
        for phase, step, time_str, desc in est["breakdown"][:8]:
            log.info(f"    {step:<20} {time_str:<10} {desc}")
        log.info("")
    except Exception:
        pass

    # ── Step 1: Dataset Preparation ───────────────────────────────────────
    state.current_phase = "data"
    state.save()
    log.info("=" * 58)
    log.info("  STEP 1/5: Dataset Preparation")
    log.info("=" * 58)

    from dataset_prep import STAGE_MAP as DATASET_STAGES

    for stage_num in stages:
        ds_name = STAGE_TO_DATASET.get(stage_num)
        if ds_name and ds_name in DATASET_STAGES:
            out_path = PREPARED_DIR / f"stage{stage_num}_{ds_name if stage_num != 4 else 'dpo'}_{'sft' if stage_num != 4 else ''}.jsonl".replace("__", "_").rstrip("_").rstrip(".")
            # Check if already prepared
            expected_name = {
                1: "stage1_general_sft.jsonl", 2: "stage2_domain_sft.jsonl",
                3: "stage3_toolcall_sft.jsonl", 4: "stage4_dpo.jsonl",
                5: "stage5_safety_sft.jsonl",
            }
            expected_path = PREPARED_DIR / expected_name.get(stage_num, "")
            if expected_path.exists():
                n = sum(1 for _ in open(expected_path, encoding="utf-8"))
                log.info(f"  Stage {stage_num} ({ds_name}): already prepared ({n:,} examples)")
                continue

            log.info(f"  Preparing Stage {stage_num} ({ds_name})...")
            t0 = time.perf_counter()
            for attempt in range(max_retries + 1):
                try:
                    DATASET_STAGES[ds_name]()
                    elapsed = time.perf_counter() - t0
                    log.info(f"  ✓ {ds_name} prepared in {elapsed:.0f}s")
                    break
                except Exception as e:
                    err_class = classify_error(e)
                    log.error(f"  ✗ {ds_name} failed (attempt {attempt+1}/{max_retries+1}): {e}")
                    state.record_error(stage_num, f"data_prep: {e}", attempt)
                    if attempt < max_retries and err_class in ("network", "disk"):
                        fix = auto_fix(err_class, stage_num, attempt)
                        if fix:
                            log.info(f"  AUTO-FIX: {fix}")
                    else:
                        log.error(f"  Data prep for stage {stage_num} failed after {attempt+1} attempts")
                        break

    # ── Step 2+3: Training Stages (SFT + DPO) ────────────────────────────
    training_stages = [s for s in stages if s in STAGE_ORDER]
    total_training = len(training_stages)

    for idx, stage_num in enumerate(training_stages):
        if resume and stage_num in state.completed_stages:
            log.info(f"\n  Stage {stage_num} ({STAGE_NAMES.get(stage_num, '?')}): "
                     f"already completed, skipping")
            continue

        step_label = "2" if stage_num != 4 else "3"
        log.info(f"\n{'='*58}")
        log.info(f"  STEP {step_label}: {STAGE_NAMES.get(stage_num, f'Stage {stage_num}')} "
                 f"[{idx+1}/{total_training}]")
        log.info("=" * 58)

        state.current_phase = "dpo" if stage_num == 4 else "training"
        state.current_stage = stage_num
        state.save()

        # Inter-stage cooldown (except first stage)
        if idx > 0:
            inter_stage_cooldown()

        # Retry loop
        succeeded = False
        for attempt in range(max_retries + 1):
            t_stage = time.perf_counter()
            try:
                if stage_num == 4:
                    from train_dpo import run_dpo
                    result = run_dpo()
                else:
                    from train_sft import run_stage
                    result = run_stage(stage_num)

                elapsed_h = (time.perf_counter() - t_stage) / 3600

                # Validate result
                state_file = STATE_DIR / (
                    f"stage{stage_num}_dpo_state.json" if stage_num == 4
                    else f"stage{stage_num}_training_state.json"
                )
                valid, msg = validate_training_result(stage_num, state_file)

                if valid:
                    loss = json.loads(state_file.read_text("utf-8")).get("training_loss", 0)
                    state.record_stage_complete(stage_num, loss, elapsed_h)
                    log.info(f"  ✓ Stage {stage_num} complete: {msg} ({elapsed_h:.1f}h)")
                    succeeded = True
                    break
                else:
                    log.warning(f"  ⚠ Stage {stage_num} validation failed: {msg}")
                    if attempt < max_retries:
                        fix = auto_fix("nan_loss" if "NaN" in msg else "unknown",
                                       stage_num, attempt)
                        if fix:
                            log.info(f"  AUTO-FIX: {fix}")
                    else:
                        log.error(f"  Stage {stage_num} failed validation after all retries")
                        state.record_error(stage_num, msg, attempt)

            except Exception as e:
                elapsed_h = (time.perf_counter() - t_stage) / 3600
                err_class = classify_error(e)
                log.error(f"  ✗ Stage {stage_num} crashed (attempt {attempt+1}/{max_retries+1}, "
                          f"{elapsed_h:.1f}h): [{err_class}] {e}")
                state.record_error(stage_num, str(e), attempt)
                state.retries_used[str(stage_num)] = attempt + 1
                state.save()

                if attempt < max_retries:
                    fix = auto_fix(err_class, stage_num, attempt)
                    if fix:
                        log.info(f"  AUTO-FIX: {fix}")
                        inter_stage_cooldown(15)
                    else:
                        log.warning(f"  No auto-fix for error class '{err_class}'")
                        inter_stage_cooldown(30)
                else:
                    log.error(f"  Stage {stage_num} exhausted all {max_retries+1} attempts")
                    tb.print_exc()

        if not succeeded:
            log.error(f"\n  PIPELINE HALTED at Stage {stage_num}")
            log.error(f"  Resume with: python pipeline/run_pipeline.py --resume")
            state.current_phase = "halted"
            state.save()
            return state

    # ── Step 4: Benchmarks ────────────────────────────────────────────────
    if not skip_benchmarks:
        state.current_phase = "benchmarks"
        state.save()
        log.info(f"\n{'='*58}")
        log.info("  STEP 4/5: Benchmarks")
        log.info("=" * 58)

        try:
            sys.path.insert(0, str(ROOT / "benchmarks"))
            from run_full_benchmarks import run_all_benchmarks

            log.info("  Running baseline benchmarks (gemma4-e4b-it:q8_0)...")
            baseline = run_all_benchmarks("gemma4-e4b-it:q8_0")
            log.info(f"  Baseline: {baseline['overall_score']:.0%} "
                     f"({baseline['total_correct']}/{baseline['total_questions']})")
        except Exception as e:
            log.warning(f"  Benchmark step failed (non-fatal): {e}")

    # ── Step 5: Export ────────────────────────────────────────────────────
    if not skip_export:
        state.current_phase = "export"
        state.save()
        log.info(f"\n{'='*58}")
        log.info("  STEP 5/5: GGUF Export + Ollama")
        log.info("=" * 58)

        from export_model import find_best_checkpoint, export_gguf, register_ollama
        checkpoint = find_best_checkpoint()
        if checkpoint:
            for attempt in range(max_retries + 1):
                try:
                    exported = export_gguf(checkpoint, ["q4_k_m", "q8_0"])
                    for quant, gguf_path in exported.items():
                        register_ollama(gguf_path, quant)
                    break
                except Exception as e:
                    log.error(f"  Export attempt {attempt+1} failed: {e}")
                    if attempt >= max_retries:
                        log.error(f"  Export failed after all retries")
        else:
            log.warning("  No checkpoint to export")

    # ── Done ──────────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t_pipeline
    state.current_phase = "complete"
    state.completed = _now()
    state.total_hours = round(elapsed / 3600, 2)
    state.save()

    log.info(f"\n{'='*58}")
    log.info(f"  PIPELINE COMPLETE")
    log.info(f"  Total time:  {elapsed/3600:.1f} hours")
    log.info(f"  Stages done: {state.completed_stages}")
    if state.stage_timings:
        log.info(f"  Stage breakdown:")
        for snum_str, timing in sorted(state.stage_timings.items()):
            log.info(f"    Stage {snum_str}: loss={timing.get('loss', 0):.4f}, "
                     f"time={timing.get('hours', 0):.1f}h")
    if state.errors:
        log.info(f"  Errors encountered: {len(state.errors)} "
                 f"(all recovered)" if not state.failed_stages else "")
    log.info(f"  State: {STATE_DIR / 'pipeline_state.json'}")
    log.info(f"  Logs:  {LOGS_DIR / 'pipeline_master.log'}")
    log.info(f"{'='*58}")

    return state


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Jemma Training Pipeline v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline/run_pipeline.py --stages 1 2            # 80/20 play (~10h)
  python pipeline/run_pipeline.py --stages 1 2 4          # SFT + DPO (~14h)
  python pipeline/run_pipeline.py                         # Full pipeline (~21h)
  python pipeline/run_pipeline.py --resume                # Resume after crash
  python pipeline/run_pipeline.py --preflight             # Check env only
  python pipeline/run_pipeline.py --estimate              # Print time estimate

Monitor:
  python toolbox/pipeline_monitor.py                      # Live dashboard
  Get-Content logs\\pipeline_master.log -Wait -Tail 20     # Tail logs
        """,
    )
    parser.add_argument("--stages", nargs="+", type=int,
                        default=[1, 2, 3, 4, 5],
                        help="Stage numbers to run (default: 1 2 3 4 5)")
    parser.add_argument("--skip-benchmarks", action="store_true")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last successful stage")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES_DEFAULT,
                        help=f"Max retries per stage (default: {MAX_RETRIES_DEFAULT})")
    parser.add_argument("--preflight", action="store_true",
                        help="Run pre-flight checks only")
    parser.add_argument("--estimate", action="store_true",
                        help="Print time estimate and exit")
    args = parser.parse_args()

    if args.preflight:
        issues = preflight_check()
        sys.exit(1 if issues else 0)

    if args.estimate:
        try:
            sys.path.insert(0, str(ROOT / "toolbox"))
            from pipeline_monitor import get_total_estimate
            est = get_total_estimate(args.stages, args.skip_export, args.skip_benchmarks)
            print(f"\n  Time Estimate for Stages {args.stages}  (RTX 5090 32GB, QLoRA 4-bit)")
            print(f"  {'='*56}")
            print(f"  {'Phase':<8} {'Step':<20} {'Time':<10} Description")
            print(f"  {'-'*8} {'-'*20} {'-'*10} {'-'*30}")
            for phase, step, time_str, desc in est["breakdown"]:
                print(f"  {phase:<8} {step:<20} {time_str:<10} {desc}")
            print(f"  {'='*56}")
            print(f"  TOTAL: ~{est['total_hours']}h ({est['total_minutes']} min)")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(0)

    run_pipeline(args.stages, args.skip_benchmarks, args.skip_export,
                 args.resume, args.max_retries)


if __name__ == "__main__":
    main()
