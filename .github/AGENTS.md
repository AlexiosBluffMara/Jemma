# Jemma workspace agent instructions

Use these files as the canonical implementation surface for this repository:

## Priority paths
- `gemma4-31b-unsloth-local-5090.ipynb` for local Gemma 4 fine-tuning on the RTX 5090
- `FINAL_NOTEBOOK_RUNNER.py` for full notebook execution
- `toolbox/run_notebook_cells.py` for notebook phase execution and deployment manifest generation
- `toolbox/prepare_ollama_cloud_bundle.py` for Ollama + Google Cloud deployment packaging
- `src/jemma/cli.py` for the application CLI
- `docs/unsloth-local-5090.md`, `docs/local-gemma4-ollama-setup.md`, and `docs/google-cloud-ollama-deployment.md` for the supported training and deployment workflows

## Repository guidance
- Treat the many root-level `run_*`, `exec_*`, `quick_*`, `minimal_*`, and `final_*` scripts as legacy unless a task explicitly targets them.
- Prefer improving the canonical paths above over creating new top-level runner variants.
- Keep E4B and E2B ahead of 31B for local training and deployment work unless the task explicitly requires 31B.
- Prefer Ollama-compatible exports and explicit deployment manifests when turning notebook outputs into hosted artifacts.
- Keep safety defaults intact for LAN actuation and external exposure; do not widen access implicitly.

## Architecture overview
- **`src/jemma/`** — Main Python package: FastAPI app (`api/`), agent loop (`agent/`), benchmarks, providers (Ollama, llama.cpp), Discord integration, safety policies (`core/policies.py`)
- **`pipeline/`** — Autonomous overnight pipeline: `run_overnight.py` orchestrator → `data_ingestion.py` → `rag_engine.py` → `overnight_trainer.py` + `safety_watchdog.py`
- **`toolbox/`** — Deployment helpers: `publish_to_hf.py`, `prepare_ollama_cloud_bundle.py`, `import_gguf_to_ollama.py`, notebook runners
- **`demos/`** — Feature demos: text, image, audio, video, function calling (all multimodal)
- **`configs/`** — TOML config: `default.toml`, `models.toml`, `benchmark-defaults.toml`, `lan.toml`
- **`web/`** — React/Vite/TypeScript dashboard frontend
- **`datasets/`** — Training data: `civic_sft_train.jsonl`, benchmark prompts in `prompts/`, Kaggle CSVs in `kaggle/`

## Build and test
```bash
# Virtual environment (multimodal stack)
.\.venv_multimodal\Scripts\Activate.ps1

# Install package
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_benchmarks.py -v

# Run demos
python -u -W ignore demos/demo_text.py
python -u -W ignore demos/demo_image.py
python -u -W ignore demos/demo_audio.py
python -u -W ignore demos/demo_video.py
python -u -W ignore demos/run_all_demos.py

# Start API server
jemma-api

# Overnight pipeline
python -u pipeline/run_overnight.py --max-iter=50 --fresh

# Publish to HuggingFace
python -u -W ignore toolbox/publish_to_hf.py --demos
```

## Code style
- Python 3.11+, type hints on public API surfaces
- FastAPI for HTTP endpoints, Pydantic for schemas
- httpx for async HTTP calls (Ollama provider)
- TOML for configuration, JSONL for datasets
- Secrets in `configs/secrets.toml` (git-ignored), never hardcode tokens

## Models
- **Primary**: `gemma4-e4b-it` (E4B Instruct) — workstation inference
- **Fallback**: `gemma4-e2b-it` (E2B Instruct) — mobile/edge
- **Training**: QLoRA via Unsloth, r=32, 4096 seq len
- **Inference**: Ollama at `http://127.0.0.1:11434`
- All Gemma 4 models: Apache 2.0 license, 131K context

## Window management — HARD RULE
- **Never spawn a new VS Code window or instance.** Do not call `code <path>`, `code --new-window`, `run_vscode_command workbench.action.newWindow`, or `create_new_workspace` unless the user explicitly requests a new window.
- Extra terminals within the existing window are allowed.
- Use `run_in_terminal` for shell tasks; never use it to invoke the `code` CLI in a way that opens a new VS Code window.
