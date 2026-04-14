---
description: "Use when writing or editing Python code in the Jemma project. Covers import conventions, type hints, async patterns, and error handling."
applyTo: "**/*.py"
---
# Python Conventions — Jemma

- Python 3.11+ required. Use `match/case`, `StrEnum`, `tomllib`, walrus operator where appropriate.
- Type hints on all public functions and class attributes. Private helpers can omit them.
- Use `httpx.AsyncClient` for async HTTP (Ollama, external APIs). Use `httpx.Client` for sync-only scripts.
- FastAPI routes go in `src/jemma/api/routes/`. Pydantic schemas in `src/jemma/api/schemas.py`.
- Configuration via TOML files in `configs/`. Load with `src/jemma/config/loader.py`. Never hardcode paths or URLs.
- Secrets in `configs/secrets.toml` (git-ignored). Access via config loader, never env vars in production code.
- Pipeline scripts (`pipeline/`) are standalone — they import from `src/jemma` but can run independently.
- Toolbox scripts (`toolbox/`) are CLI utilities. Use `argparse` for argument parsing.
- Use `logging` module, not `print()`, except in demos and one-off scripts.
- For Ollama calls: base URL `http://127.0.0.1:11434`, use `src/jemma/providers/ollama.py` abstractions.
