---
description: "Deploy a fine-tuned model checkpoint to Ollama locally"
agent: "agent"
argument-hint: "Path to GGUF file or checkpoint directory to deploy"
tools: [execute, read, search]
---
Deploy a model checkpoint to the local Ollama instance.

1. If checkpoint is not GGUF, export first using the Unsloth GGUF export path
2. Import into Ollama: `python -u toolbox/import_gguf_to_ollama.py <path>`
3. Verify: `ollama list` — confirm model appears
4. Smoke test: send a basic chat completion to the new model
5. If cloud deployment requested, run `python -u toolbox/prepare_ollama_cloud_bundle.py` to generate Dockerfile + Modelfile

Reference: `docs/local-gemma4-ollama-setup.md`
