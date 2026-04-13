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

## Window management — HARD RULE
- **Never spawn a new VS Code window or instance.** Do not call `code <path>`, `code --new-window`, `run_vscode_command workbench.action.newWindow`, or `create_new_workspace` unless the user explicitly requests a new window.
- Extra terminals within the existing window are allowed.
- Use `run_in_terminal` for shell tasks; never use it to invoke the `code` CLI in a way that opens a new VS Code window.
