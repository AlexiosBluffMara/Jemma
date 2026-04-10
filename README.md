# Jemma
Jemma is a variant of Gemma inspired by Jemma Simmons.

## Current focus
The current rollout target is a local Gemma 4 matrix built around:

- official Google Gemma 4 E2B and E4B checkpoints as the original source artifacts,
- Ollama aliases for both BF16 originals and quantized local variants,
- Unsloth fine-tuning with E4B as the primary workstation loop and E2B as the mobile and offline fallback,
- public, hackathon-safe datasets for safety-oriented SFT, evaluation, and demo flows.

## Guides
- Master rollout: docs/gemma4-e2b-e4b-local-rollout.md
- Ollama setup: docs/local-gemma4-ollama-setup.md
- Unsloth workflow: docs/unsloth-local-5090.md
- Mobile deployment: docs/mobile-gemma4-setup.md
- Public dataset plan: docs/second-brain-data-plan.md

## Toolbox
- Fetch official Gemma 4 checkpoints: ./toolbox/fetch_gemma4_hf.sh
- Register and quantize Ollama models: ./toolbox/setup_gemma4_ollama.sh
- USB bridge for Pixel testing: ./toolbox/pixel_fold_adb_reverse.sh
