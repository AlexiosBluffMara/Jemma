# Jemma
Jemma is a variant of Gemma inspired by Jemma Simmons.

## Current focus
The current rollout target is a local Gemma 4 matrix built around:

- official Google Gemma 4 E2B and E4B checkpoints as the original source artifacts,
- Ollama aliases for both BF16 originals and quantized local variants,
- Unsloth fine-tuning with E4B as the primary workstation loop and E2B as the mobile and offline fallback,
- public, hackathon-safe datasets for safety-oriented SFT, evaluation, and demo flows.

## Autonomous framework
Jemma now includes a first-pass Python framework for building the hackathon submission as a **local autonomous benchmark lab**:

- a checkpointed agent loop under `src/jemma/agent/`,
- an Ollama-first benchmark runner under `src/jemma/benchmarks/`,
- deny-by-default LAN adapters for Tailscale, Hue, smart plugs, and router health under `src/jemma/capabilities/`,
- TOML-driven model, LAN, and benchmark manifests under `configs/` and `manifests/`,
- run artifacts and summaries under `artifacts/runs/`.

This is the implementation base for **Jemma SafeBrain Command**: a local safety operations system that can benchmark Gemma variants, route tasks to the best local model, and keep physical automation gated behind explicit safety controls.

### CLI
```bash
python -m jemma.cli health
python -m jemma.cli benchmark-solo --manifest manifests/benchmarks/gemma-solo-eval.toml
python -m jemma.cli benchmark-versus --manifest manifests/benchmarks/gemma-head-to-head.toml
python -m jemma.cli benchmark-stress --manifest manifests/benchmarks/gemma-stress-vs-reasoning.toml
python -m jemma.cli run-objective --manifest manifests/objectives/lan-watch.toml
python -m jemma.cli serve-api --host 127.0.0.1 --port 8000
```

## Web UI
Jemma now includes a TypeScript mission-control frontend in `web/` for:

- launching solo, pairwise, and stress benchmarks,
- tracking live jobs over SSE,
- reviewing completed runs and summaries,
- monitoring provider and system telemetry.

### Web UI dev loop
```bash
python -m jemma.cli serve-api --host 127.0.0.1 --port 8000
cd web
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

See `docs/agent-framework.md` and `docs/web-ui-stack.md` for the architecture, safety model, and public-demo boundaries.

## Guides
- Master rollout: docs/gemma4-e2b-e4b-local-rollout.md
- Ollama setup: docs/local-gemma4-ollama-setup.md
- Unsloth workflow: docs/unsloth-local-5090.md
- Mobile deployment: docs/mobile-gemma4-setup.md
- Public dataset plan: docs/second-brain-data-plan.md
- Discord server blueprint: docs/discord-research-server-blueprint.md

## Toolbox
- Fetch official Gemma 4 checkpoints: ./toolbox/fetch_gemma4_hf.sh
- Register and quantize Ollama models: ./toolbox/setup_gemma4_ollama.sh
- USB bridge for Pixel testing: ./toolbox/pixel_fold_adb_reverse.sh
- Windows machine profiling: `powershell.exe -NoProfile -File .\toolbox\windows\profile-machine.ps1`
