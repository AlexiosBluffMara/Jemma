---
name: overnight-pipeline
description: "Run, monitor, debug, or resume the Jemma overnight training pipeline. Use when: training, fine-tuning, data ingestion, RAG indexing, QLoRA, checkpoint management, or pipeline troubleshooting."
argument-hint: "Describe what you need: start fresh, resume, check status, debug an error, or export results"
---

# Overnight Pipeline — Full Workflow

## When to Use
- Starting a fresh training run or resuming an interrupted one
- Debugging pipeline failures (data ingestion, RAG, training, export)
- Monitoring GPU health and training progress
- Exporting trained checkpoints to Ollama or GGUF

## Architecture
```
run_overnight.py (orchestrator)
  ├── data_ingestion.py → datasets/civic_data.db
  ├── rag_engine.py → SQLite vector store + 299 chunks
  ├── overnight_trainer.py → checkpoints/overnight/
  └── safety_watchdog.py → GPU monitoring (85°C throttle, 90°C stop)
```

## Procedure

### 1. Pre-flight Checks
```powershell
# Verify GPU
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# Check Ollama
curl http://127.0.0.1:11434/api/tags

# Check training data
python -c "import json; lines=open('datasets/civic_sft_train.jsonl').readlines(); print(f'{len(lines)} samples')"

# Check current state
Get-Content state/overnight_state.json
```

### 2. Launch Training
```powershell
# Fresh start (resets state)
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUNBUFFERED=1
& .\.venv_multimodal\Scripts\python.exe -u pipeline/run_overnight.py --max-iter=50 --fresh

# Resume from last checkpoint
& .\.venv_multimodal\Scripts\python.exe -u pipeline/run_overnight.py --max-iter=50
```

### 3. Monitor Progress
- **State**: `state/overnight_state.json` — iteration count, best score, timestamps
- **Logs**: `logs/overnight_master.log` — full execution log
- **GPU**: `python toolbox/live_monitor.py` — real-time GPU temps and VRAM
- **Checkpoints**: `checkpoints/overnight/` — per-iteration saves
- **Best model**: `checkpoints/overnight/best_score.json`

### 4. Export to Ollama
After training completes or produces a good checkpoint:
```powershell
python -u toolbox/import_gguf_to_ollama.py <checkpoint_path>
ollama list  # verify
```

### 5. Common Issues
| Symptom | Cause | Fix |
|---|---|---|
| CUDA OOM | Batch too large or model too big | Reduce batch_size in trainer config, or use E2B instead of E4B |
| Pipeline exits at ingest | Network/scraping failure | Check `data_ingestion.py` logs, verify URLs accessible |
| Watchdog killed training | GPU overheating | Improve cooling, reduce batch size, check fan speeds |
| State file corrupt | Interrupted write | Delete `state/overnight_state.json`, restart with `--fresh` |

## Key Files
- [run_overnight.py](../../pipeline/run_overnight.py) — Orchestrator
- [overnight_trainer.py](../../pipeline/overnight_trainer.py) — Training loop
- [data_ingestion.py](../../pipeline/data_ingestion.py) — Data scraper
- [rag_engine.py](../../pipeline/rag_engine.py) — RAG engine
- [safety_watchdog.py](../../pipeline/safety_watchdog.py) — GPU monitor
