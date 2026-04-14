---
description: "Launch the overnight training pipeline with data ingestion, RAG, and QLoRA fine-tuning"
agent: "agent"
argument-hint: "Number of iterations (default 50) and whether to use --fresh flag"
tools: [execute, read, search]
---
Launch the overnight autonomous training pipeline.

Pre-flight checks:
1. GPU available: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`
2. Ollama running: `curl http://127.0.0.1:11434/api/tags`
3. Training data exists: `datasets/civic_sft_train.jsonl`
4. State file: `state/overnight_state.json` (check last iteration count)

Launch command:
```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUNBUFFERED=1
& .\.venv_multimodal\Scripts\python.exe -u pipeline/run_overnight.py --max-iter=50 --fresh
```

Monitor:
- Logs: `logs/overnight_master.log`
- State: `state/overnight_state.json`
- GPU temps: `toolbox/live_monitor.py`
- Best checkpoint: `checkpoints/overnight/best_score.json`
