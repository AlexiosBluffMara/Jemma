"""
Jemma SafeBrain — Master Orchestrator

Runs the complete overnight autonomous pipeline:
  Phase 1: Data ingestion (ISU, Normal, Illinois, Chicago, Kaggle, HF)
  Phase 2: RAG index build (chunk + embed all civic data)
  Phase 3: Autonomous training loop (QLoRA with eval + keep/discard)
  Phase 4: Export best model (GGUF for Ollama)

Self-healing with retry, checkpoint/resume, GPU protection.
Designed to run unattended for 8+ hours.
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

from safety_watchdog import (
    health, start_watchdog, print_status, get_status_report, query_gpu
)

log = logging.getLogger("orchestrator")

BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "state" / "overnight_state.json"
MASTER_LOG = BASE_DIR / "logs" / "overnight_master.log"


# ---------------------------------------------------------------------------
# State management (checkpoint/resume)
# ---------------------------------------------------------------------------
def load_state() -> dict:
    """Load orchestrator state for resume capability."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "phase": 0,
        "started_at": None,
        "ingestion_done": False,
        "rag_done": False,
        "training_started": False,
        "training_iterations": 0,
        "best_score": 0.0,
        "export_done": False,
        "errors": [],
    }


def save_state(state: dict):
    """Persist orchestrator state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------
def phase_1_ingestion(state: dict) -> dict:
    """Phase 1: Ingest all civic data sources."""
    if state["ingestion_done"]:
        log.info("Phase 1 already complete, skipping")
        return state

    log.info("\n" + "=" * 70)
    log.info("PHASE 1: DATA INGESTION")
    log.info("=" * 70)

    try:
        from data_ingestion import run_full_ingestion
        results = run_full_ingestion()
        state["ingestion_done"] = True
        state["ingestion_results"] = results
        state["phase"] = 1
        save_state(state)
        log.info("Phase 1 COMPLETE")
    except Exception as e:
        log.error(f"Phase 1 FAILED: {e}")
        traceback.print_exc()
        state["errors"].append({"phase": 1, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        save_state(state)
        # Non-fatal: continue with whatever data we have
        state["ingestion_done"] = True
        state["phase"] = 1
        save_state(state)

    return state


def phase_2_rag(state: dict) -> dict:
    """Phase 2: Build RAG index over all ingested data."""
    if state["rag_done"]:
        log.info("Phase 2 already complete, skipping")
        return state

    log.info("\n" + "=" * 70)
    log.info("PHASE 2: RAG INDEX BUILD")
    log.info("=" * 70)

    try:
        from rag_engine import build_rag_index
        n_chunks = build_rag_index(force_rebuild=True)
        state["rag_done"] = True
        state["rag_chunks"] = n_chunks
        state["phase"] = 2
        save_state(state)
        log.info(f"Phase 2 COMPLETE: {n_chunks} chunks indexed")
    except Exception as e:
        log.error(f"Phase 2 FAILED: {e}")
        traceback.print_exc()
        state["errors"].append({"phase": 2, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        # RAG failure is non-fatal for training (training generates its own data)
        state["rag_done"] = True
        state["phase"] = 2
        save_state(state)

    return state


def phase_3_training(state: dict, max_iterations: int = 50) -> dict:
    """Phase 3: Autonomous overnight training loop."""
    log.info("\n" + "=" * 70)
    log.info("PHASE 3: AUTONOMOUS TRAINING")
    log.info("=" * 70)

    try:
        from overnight_trainer import run_overnight_training
        results = run_overnight_training(max_iterations=max_iterations)
        state["training_started"] = True
        state["training_iterations"] = len(results) if results else 0
        state["phase"] = 3

        # Record summary
        if results:
            completed = sum(1 for r in results if r.get("status") == "completed")
            improved = sum(1 for r in results if r.get("saved", False))
            state["training_completed"] = completed
            state["training_improved"] = improved
            scores = [r.get("eval_score", 0) for r in results
                      if r.get("eval_score") is not None]
            state["best_score"] = max(scores) if scores else 0

        save_state(state)
        log.info("Phase 3 COMPLETE")
    except KeyboardInterrupt:
        log.info("Phase 3 interrupted by user")
        state["training_started"] = True
        state["phase"] = 3
        save_state(state)
    except Exception as e:
        log.error(f"Phase 3 FAILED: {e}")
        traceback.print_exc()
        state["errors"].append({"phase": 3, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        state["training_started"] = True
        state["phase"] = 3
        save_state(state)

    return state


def phase_4_export(state: dict) -> dict:
    """Phase 4: Export best adapter and prepare for Ollama."""
    if state["export_done"]:
        log.info("Phase 4 already complete, skipping")
        return state

    log.info("\n" + "=" * 70)
    log.info("PHASE 4: MODEL EXPORT")
    log.info("=" * 70)

    adapter_dir = BASE_DIR / "checkpoints" / "overnight" / "best_adapter"
    if not adapter_dir.exists():
        log.warning("No best adapter found — skipping export")
        state["phase"] = 4
        save_state(state)
        return state

    try:
        # Create merged model
        log.info("Merging adapter with base model...")
        # This will be done in a separate script to keep memory clean
        export_script = BASE_DIR / "pipeline" / "_export_adapter.py"
        if export_script.exists():
            import subprocess
            result = subprocess.run(
                [sys.executable, str(export_script)],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode == 0:
                state["export_done"] = True
                log.info("Phase 4 COMPLETE: Model exported")
            else:
                log.error(f"Export failed: {result.stderr[:500]}")
        else:
            log.info("Export script not found — adapter saved but not merged")
            state["export_done"] = False

        state["phase"] = 4
        save_state(state)
    except Exception as e:
        log.error(f"Phase 4 FAILED: {e}")
        state["errors"].append({"phase": 4, "error": str(e),
                                "time": datetime.utcnow().isoformat()})
        state["phase"] = 4
        save_state(state)

    return state


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_overnight(max_training_iterations: int = 50,
                  resume: bool = True):
    """Run the complete overnight autonomous pipeline."""
    start = time.time()

    # Setup logging
    MASTER_LOG.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(MASTER_LOG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)

    log.info("=" * 70)
    log.info("JEMMA SAFEBRAIN — OVERNIGHT AUTONOMOUS PIPELINE")
    log.info(f"Started: {datetime.now().isoformat()}")
    log.info("=" * 70)

    # System check
    print_status()
    gpu = query_gpu()
    log.info(f"GPU: {gpu.gpu_name} @ {gpu.temperature_c}°C, "
             f"VRAM: {gpu.vram_used_mb}/{gpu.vram_total_mb}MB")

    # Start watchdog
    watchdog = start_watchdog()
    log.info("GPU watchdog active")

    # Load or create state
    state = load_state() if resume else {
        "phase": 0, "started_at": datetime.utcnow().isoformat(),
        "ingestion_done": False, "rag_done": False,
        "training_started": False, "training_iterations": 0,
        "best_score": 0.0, "export_done": False, "errors": [],
    }
    if state["started_at"] is None:
        state["started_at"] = datetime.utcnow().isoformat()
    save_state(state)

    try:
        # Phase 1: Data ingestion
        state = phase_1_ingestion(state)

        # Phase 2: RAG index
        state = phase_2_rag(state)

        # Phase 3: Training
        state = phase_3_training(state, max_iterations=max_training_iterations)

        # Phase 4: Export
        state = phase_4_export(state)

    except KeyboardInterrupt:
        log.info("\nPipeline interrupted by user")
    except Exception as e:
        log.critical(f"Pipeline crashed: {e}")
        traceback.print_exc()
        state["errors"].append({"phase": "fatal", "error": str(e),
                                "time": datetime.utcnow().isoformat()})
    finally:
        health.should_stop = True

    # Final report
    elapsed = time.time() - start
    state["total_elapsed_s"] = elapsed
    state["completed_at"] = datetime.utcnow().isoformat()
    save_state(state)

    log.info("\n" + "=" * 70)
    log.info("OVERNIGHT PIPELINE — FINAL REPORT")
    log.info("=" * 70)
    log.info(f"  Total time:          {elapsed / 3600:.1f} hours")
    log.info(f"  Phase reached:       {state['phase']}")
    log.info(f"  Ingestion:           {'DONE' if state['ingestion_done'] else 'INCOMPLETE'}")
    log.info(f"  RAG index:           {'DONE' if state['rag_done'] else 'INCOMPLETE'} "
             f"({state.get('rag_chunks', 0)} chunks)")
    log.info(f"  Training:            {state.get('training_iterations', 0)} iterations")
    log.info(f"  Best score:          {state.get('best_score', 0):.3f}")
    log.info(f"  Errors:              {len(state.get('errors', []))}")
    log.info(f"  State file:          {STATE_FILE}")
    log.info("=" * 70)

    return state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Parse args
    max_iter = 50
    resume = True
    for arg in sys.argv[1:]:
        if arg.startswith("--max-iter="):
            max_iter = int(arg.split("=")[1])
        elif arg == "--fresh":
            resume = False
        elif arg == "--status":
            state = load_state()
            print(json.dumps(state, indent=2))
            sys.exit(0)
        elif arg == "--health":
            print_status()
            sys.exit(0)

    run_overnight(max_training_iterations=max_iter, resume=resume)
