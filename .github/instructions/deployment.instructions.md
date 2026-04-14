---
description: "Use when deploying models via Ollama, preparing GGUF exports, publishing to HuggingFace, or setting up Google Cloud deployment."
---
# Deployment Patterns — Jemma

## Ollama (Local)
1. Models fetched via `ollama pull` or imported from GGUF via `toolbox/import_gguf_to_ollama.py`
2. Quantized aliases: E4B `q8_0` (workstation), E2B `q4_k_m` (mobile)
3. Health check: `GET http://127.0.0.1:11434/api/tags`
4. Chat: `POST http://127.0.0.1:11434/api/chat`

## HuggingFace Hub
- Publisher: `toolbox/publish_to_hf.py` — pushes model card, NOTICE, demos
- Run: `python -u -W ignore toolbox/publish_to_hf.py --demos`
- HF repo: `soumitty/jemma-safebrain-gemma-4-e4b-it` (public)
- Model card template: `toolbox/hf_model_card.md`
- Token via `huggingface_hub.login()` — write+delete access required

## Google Cloud
- Bundle builder: `toolbox/prepare_ollama_cloud_bundle.py`
- Creates Dockerfile + Modelfile from local GGUF checkpoint
- Deploy target: Google Cloud Run with Ollama container
- See `docs/google-cloud-ollama-deployment.md` for full guide

## GGUF Export
- Export from Unsloth checkpoint → GGUF (multiple quant levels)
- Register in Ollama with custom Modelfile
- Validate: `ollama list` to confirm model appears
