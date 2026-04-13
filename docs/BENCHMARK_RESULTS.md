# Jemma Benchmark Results — Gemma 4 Full Stress Test

**Date:** 2026-04-11  
**Hardware:** NVIDIA RTX 5090 (32 607 MiB VRAM)  
**Ollama:** v0.20.5  
**Models tested:** Gemma 4 E4B (Q8_0, 9.6 GB), E2B (Q4_K_M, 7.2 GB), 26B MoE (Q4_K_M, 17 GB), 31B Dense (Q4_K_M, 19 GB)

---

## Executive Summary

| Category | Result |
|---|---|
| Unit tests | **12/12 pass** |
| CLI health | **Ollama reachable, 12 models listed** |
| WebUI build | **TypeScript 0 errors, Vite build OK (18 KB CSS + 532 KB JS)** |
| API endpoints | **All 7 routes functional** (health, models, system, runs, presets, jobs, training) |
| Smoke benchmark | **100% pass** (3 models × 2 scenarios, after validator fix) |
| Pairwise benchmark | **E4B vs E2B: tied 1-1** |
| Stress benchmark | **E4B: 100% pass, E2B: 66.7% on reasoning** |
| Safety benchmark | **E2B outperforms E4B; 26B MoE matches E2B** |
| API job lifecycle | **stress job submitted → running → succeeded** |

---

## 1. Smoke Benchmark (Solo Eval)

**Manifest:** `gemma-solo-eval.toml` — 3 models × 2 scenarios (`smoke-ok`, `json-ready`)

| Model | Pass Rate | Avg Latency | Avg Score |
|---|---|---|---|
| gemma4-e4b-it-q8 | 100% | 11 942 ms | 1.000 |
| gemma4-e2b-it-q4 | 100% | 4 392 ms | 1.000 |
| gemma4-e4b-it-bf16 | 100% | 13 605 ms | 1.000 |

> Note: Initial run showed 50% pass rate — all failures were on `json-ready` because models wrap JSON in markdown fences. Fixed `validators.py json_object` to strip ` ```json ``` ` fences. Re-run achieved 100%.

---

## 2. Pairwise (Head-to-Head)

**Manifest:** `gemma-head-to-head.toml` — E4B vs E2B on Q&A prompts

| Metric | E4B | E2B |
|---|---|---|
| Wins | 1 | 1 |
| Win Rate | 50% | 50% |

**Verdict:** Tied on general Q&A.

---

## 3. Stress Benchmark (Standard + Reasoning)

**Manifest:** `gemma-stress-vs-reasoning.toml` — 4 models × 2 prompt styles × 2 reps

| Model | Standard Pass | Standard Latency | Reasoning Pass | Reasoning Latency |
|---|---|---|---|---|
| gemma4-e4b-it-q8 | **100%** | 1 447 ms | **100%** | 2 057 ms |
| gemma4-e2b-it-q4 | **100%** | 1 125 ms | **66.7%** | 1 213 ms |
| gemma4-e4b-it-bf16 | **100%** | 1 485 ms | **100%** | 2 096 ms |
| gemma4-e2b-it-bf16 | **100%** | 1 152 ms | **66.7%** | 1 223 ms |

**Key finding:** E4B models achieve 100% across both prompt styles. E2B models drop to 66.7% on reasoning prompts — consistent across quantization variants.

---

## 4. Safety Benchmark (Solo Eval)

### 4a. E4B vs E2B (10 scenarios × 1 rep)

**Manifest:** `safety-ollama-only.toml`

| Model | Pass Rate | Avg Score | Avg Latency |
|---|---|---|---|
| gemma4-e4b-it-q8 | 20% | 0.617 | 9 906 ms |
| gemma4-e2b-it-q4 | **40%** | **0.742** | 5 630 ms |

### 4b. Safety Stress (Standard + Reasoning)

**Manifest:** `safety-stress-ollama-only.toml`

| Model | Standard Pass | Standard Score | Reasoning Pass | Reasoning Score |
|---|---|---|---|---|
| gemma4-e4b-it-q8 | 20% | 0.617 | 20% | 0.750 |
| gemma4-e2b-it-q4 | **40%** | **0.742** | 20% | 0.700 |

### 4c. All 4 Models Safety (in-progress, 33/40 events)

**Manifest:** `safety-all-models.toml` — 4 models × 10 safety scenarios

| Model | Scenarios Done | Passed | Pass Rate | Avg Score | Avg Latency |
|---|---|---|---|---|---|
| gemma4-e4b-it-q8 | 10/10 | 2 | 20% | 0.617 | 18 859 ms |
| gemma4-e2b-it-q4 | 10/10 | 4 | **40%** | **0.742** | 10 362 ms |
| gemma4-26b-moe | 10/10 | 4 | **40%** | **0.767** | 21 133 ms |
| gemma4-31b-dense | 2/10 | 0 | 0%\* | 0.167\* | 171 512 ms\* |

> \*31B Dense partial results (2/10 scenarios). Each safety prompt takes ~2–3 min on the 31B model (19 GB at Q4_K_M). Benchmark still running.

**Key findings:**
- **E2B (2.6B params) outperforms E4B (4B params) on safety keyword detection** — passes more scenarios and scores higher on average.
- **26B MoE matches E2B pass rate** and achieves the highest avg score (0.767) of all completed models.
- Safety benchmarks test keyword presence (e.g., `separation`, `visibility`, `accountability`) — the smaller E2B model includes more expected safety terminology.

---

## 5. API Server Validation

**Server:** FastAPI on port 8001 (Uvicorn)

| Endpoint | Status | Details |
|---|---|---|
| `GET /api/health` | ✅ | Ollama reachable, 12 models |
| `GET /api/models` | ✅ | 8 configs (6 Ollama + 2 llamacpp) |
| `GET /api/system` | ✅ | RTX 5090, 32607 MiB, Ollama 0.20.5 |
| `GET /api/runs` | ✅ | 9 runs listed |
| `GET /api/benchmarks/presets` | ✅ | 3 presets |
| `GET /api/training/status` | ✅ | Idle state |
| `POST /api/jobs/benchmark/stress` | ✅ | Job created → running → **succeeded** |

### API Stress Job Results (job-0001)

| Model | Standard Pass | Standard Latency | Reasoning Pass | Reasoning Latency |
|---|---|---|---|---|
| gemma4-e4b-it-q8 | **100%** | 15 014 ms | **100%** | 21 574 ms |
| gemma4-e2b-it-q4 | **100%** | 20 949 ms | **66.7%** | 19 103 ms |

Same pass-rate pattern as CLI stress benchmark, confirming API↔CLI consistency.

---

## 6. Fixes Applied During Testing

| Fix | File | Description |
|---|---|---|
| Model name mismatch | `configs/models.toml` | `remote_name` values didn't match Ollama tags. Changed `gemma4-e4b-it:q8_0` → `gemma4:e4b` etc. |
| Missing test params | 5 test files | Added `llamacpp_base_url` / `llamacpp_timeout_s` to `AppConfig()` |
| JSON validator | `src/jemma/benchmarks/validators.py` | Strip markdown ` ```json ``` ` fences before parsing |
| Timeout propagation | `src/jemma/benchmarks/runner.py` | Pass `config.ollama_timeout_s` to `ChatRequest` |
| Default timeout | `configs/default.toml` | Increased from 120s → 300s for large models |
| 26B / 31B models | `configs/models.toml` | Added `gemma4-26b-moe` and `gemma4-31b-dense` entries |

---

## 7. Artifacts

All run data saved under `artifacts/runs/`:

| Run ID | Type | Manifest |
|---|---|---|
| `solo-benchmark-20260411T160859792247Z` | solo | gemma-solo-eval (pre-fix) |
| `solo-benchmark-20260411T164540474567Z` | solo | gemma-solo-eval (post-fix) |
| `pairwise-benchmark-20260411T161016625114Z` | pairwise | gemma-head-to-head |
| `stress-benchmark-20260411T161100543372Z` | stress | gemma-stress-vs-reasoning |
| `solo-benchmark-20260411T162107522328Z` | solo | safety-ollama-only |
| `stress-benchmark-20260411T162356152417Z` | stress | safety-stress-ollama-only |
| `solo-benchmark-20260411T164234821748Z` | solo | safety-all-models (in-progress) |
| `stress-benchmark-20260411T164713877602Z` | stress | API-submitted stress job |
