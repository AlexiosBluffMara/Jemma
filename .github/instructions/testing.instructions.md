---
description: "Use when writing or editing tests. Covers test conventions, fixtures, and mocking patterns."
applyTo: "tests/**"
---
# Testing Conventions — Jemma

- Use pytest. Tests live in `tests/` mirroring `src/jemma/` structure.
- Mock external services (Ollama, HuggingFace) — never make real HTTP calls in tests.
- Use `httpx.MockTransport` or `respx` for mocking httpx clients.
- Use `pytest.fixture` for reusable setup. Shared fixtures in `tests/conftest.py`.
- Benchmark prompts for integration tests live in `datasets/prompts/smoke.jsonl`.
- Run: `pytest tests/ -v` (all), `pytest tests/test_benchmarks.py -v` (specific).
- Test files named `test_*.py`. Test functions named `test_*`.
- For FastAPI route tests, use `httpx.AsyncClient` with `app` fixture.
