# Jemma web UI and API stack

## Stack choice
The current implementation uses:

- **FastAPI + Uvicorn** for the HTTP API
- **React + TypeScript + Vite** for the web UI
- **SQLite + JSON artifacts** for persistent run data
- **SSE** for live job event streaming

This matches the repo's existing Python-first benchmark framework while adding a TypeScript control plane for the hackathon demo.

## API surface
The backend lives under `src/jemma/api/` and currently exposes:

- `GET /api/health`
- `GET /api/models`
- `GET /api/system`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/summary`
- `GET /api/runs/{run_id}/results`
- `GET /api/runs/{run_id}/events`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/events`
- `GET /api/benchmarks/presets`
- `POST /api/jobs/benchmark/solo`
- `POST /api/jobs/benchmark/pairwise`
- `POST /api/jobs/benchmark/stress`
- `GET /api/objectives`
- `POST /api/objectives/lan-watch`

## UI information architecture
The web app in `web/src/` is organized around five demo tabs:

1. **Overview** - provider health, models, preset suites, and system snapshot
2. **Benchmarks** - launch solo, pairwise, or stress runs
3. **Jobs** - live event stream and progress
4. **Runs** - completed summaries and raw result previews
5. **System** - telemetry and optimization notes

## Stress test design
The current stress workflow is manifest-driven:

- `manifests/benchmarks/gemma-stress-vs-reasoning.toml`
- `datasets/prompts/stress-standard.jsonl`
- `datasets/prompts/stress-reasoning.jsonl`

This is intended to compare:

- standard direct-response prompts,
- structured reasoning-style prompts,
- quantized defaults versus BF16 baselines,
- smaller fallback models versus larger workstation models.

## Public demo boundary
The public demo recommendation remains strict:

- **Do not expose Ollama directly**
- **Do not expose raw LAN capability execution**
- expose only the web UI plus a constrained API facade if public access is needed
- keep actuation disabled in public mode

Recommended public architecture:

1. Vite build behind a reverse proxy or static host
2. FastAPI reachable only through a hardened demo facade/tunnel
3. preset-only benchmark submission for public users
4. direct workstation access only over trusted LAN or Tailscale

## Hardware optimization story
The UI and API are designed to surface the metrics judges care about:

- latency and pass rate
- model tradeoffs across quantization levels
- fallback behavior under degraded operation
- system and GPU telemetry snapshots
- benchmark evidence stored under `artifacts/runs/`

## Next technical steps
- add richer TTFT/token throughput telemetry
- add public-demo auth and rate limits
- add run cancellation
- add static frontend serving from the Python app for single-host demos
- add deeper benchmark rubrics and charts
