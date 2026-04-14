---
name: model-deployment
description: "End-to-end model deployment for Jemma: Ollama local, HuggingFace Hub, Google Cloud Run, GGUF export. Use when: deploying, publishing, exporting, packaging, or releasing a trained model."
argument-hint: "Describe target: local Ollama, HuggingFace Hub, Google Cloud, or GGUF export"
---

# Model Deployment — Full Workflow

## When to Use
- Deploying a fine-tuned checkpoint to local Ollama
- Publishing model + artifacts to HuggingFace Hub
- Preparing a Google Cloud Run deployment bundle
- Exporting to GGUF format for distribution

## Deployment Targets

### Target 1: Local Ollama
```powershell
# Import GGUF into Ollama
python -u toolbox/import_gguf_to_ollama.py <path_to_gguf>

# Verify model registered
ollama list

# Smoke test
curl http://127.0.0.1:11434/api/chat -d '{
  "model": "gemma4-e4b-it:q8_0",
  "messages": [{"role": "user", "content": "Hello"}]
}'
```

### Target 2: HuggingFace Hub
```powershell
# Validate token
python -u -W ignore demos/validate_hf_token.py

# Publish (includes model card, NOTICE, demos)
python -u -W ignore toolbox/publish_to_hf.py --demos
```

Checklist:
- [ ] Model card (`toolbox/hf_model_card.md`) has current benchmark scores
- [ ] `base_model` metadata points to `google/gemma-4-E4B-it`
- [ ] `base_model_relation` is `finetune`
- [ ] License: Apache-2.0
- [ ] Tags include `gemma-4-good-hackathon`
- [ ] Trademark: "Gemma is a trademark of Google LLC."
- [ ] Repo name follows Google naming: `soumitty/jemma-safebrain-gemma-4-e4b-it`

### Target 3: Google Cloud Run
```powershell
# Generate Docker bundle from GGUF
python -u toolbox/prepare_ollama_cloud_bundle.py

# Review generated artifacts (Dockerfile, Modelfile, deploy script)
# Follow docs/google-cloud-ollama-deployment.md for cloud deploy
```

### Target 4: GGUF Export
From an Unsloth checkpoint:
1. Load checkpoint with Unsloth `FastLanguageModel`
2. Export to GGUF with desired quantization (Q4_K_M, Q5_K_M, Q8_0)
3. Validate with `llama.cpp` or import to Ollama

## Verification Matrix
| Target | Verify Command | Success Criteria |
|---|---|---|
| Ollama | `ollama list` | Model name appears in list |
| Ollama | `curl .../api/chat` | Valid JSON response |
| HuggingFace | `python toolbox/publish_to_hf.py` | Exit code 0, URL printed |
| Cloud Run | `gcloud run services describe` | Service status: READY |
| GGUF | `llama.cpp/main -m <file>` | Model loads, generates text |

## Key Files
- [import_gguf_to_ollama.py](../../toolbox/import_gguf_to_ollama.py) — Ollama importer
- [publish_to_hf.py](../../toolbox/publish_to_hf.py) — HF publisher
- [prepare_ollama_cloud_bundle.py](../../toolbox/prepare_ollama_cloud_bundle.py) — Cloud bundle
- [hf_model_card.md](../../toolbox/hf_model_card.md) — Model card template
- [google-cloud-ollama-deployment.md](../../docs/google-cloud-ollama-deployment.md) — Cloud guide
