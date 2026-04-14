---
description: "Use when working with Jupyter notebooks for Gemma 4 training, benchmarking, or demos."
applyTo: "**/*.ipynb"
---
# Notebook Conventions — Jemma

- Primary notebook: `gemma4-31b-unsloth-local-5090.ipynb` (RTX 5090 training).
- Use `toolbox/run_notebook_cells.py` for programmatic cell execution — avoid manual reruns.
- Training cells must check GPU availability before starting. Use `torch.cuda.is_available()`.
- Always include a cell that logs VRAM usage (`torch.cuda.memory_allocated()`).
- Model loading: use `AutoModelForMultimodalLM` + `AutoProcessor` from transformers for Gemma 4.
- For Unsloth: `from unsloth import FastLanguageModel` — check import succeeds before training.
- Export GGUF for Ollama deployment. Use `toolbox/import_gguf_to_ollama.py` to register.
- Keep cell outputs cleared in git commits to reduce repo size.
