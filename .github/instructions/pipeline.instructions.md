---
description: "Use when working on the overnight training pipeline, data ingestion, RAG engine, or safety watchdog."
applyTo: "pipeline/**"
---
# Pipeline Development — Jemma

- Entry point: `pipeline/run_overnight.py` — orchestrates ingest → RAG → train → export.
- State persisted in `state/overnight_state.json`. Always read/write state atomically.
- Training uses Unsloth QLoRA (preferred) with PEFT+bitsandbytes fallback.
- Config: r=32 LoRA rank, 4096 sequence length, batch size 2, gradient accumulation 8.
- Safety watchdog (`safety_watchdog.py`) auto-throttles at 85°C GPU temp, stops at 90°C.
- Data ingestion (`data_ingestion.py`) uses multi-threaded scraping with rate limiting.
- RAG engine (`rag_engine.py`) uses sentence-transformers + SQLite vector store at `datasets/civic_data.db`.
- Checkpoints go to `checkpoints/overnight/`. Best model tracked in `checkpoints/overnight/best_score.json`.
- Training datasets: `datasets/civic_sft_train.jsonl` (8,129 samples), `datasets/civic_sft_val.jsonl`.
- Never remove or weaken safety watchdog thresholds without explicit user approval.
