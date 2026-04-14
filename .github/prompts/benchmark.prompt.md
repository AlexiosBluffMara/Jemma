---
description: "Run benchmarks against the local Gemma 4 model via Ollama"
agent: "agent"
argument-hint: "Which benchmark suite to run (smoke, qa, safety, stress) and which model"
tools: [execute, read, search]
---
Run the specified benchmark suite against the local Olmma Gemma 4 model.

1. Verify Ollama is running: `curl http://127.0.0.1:11434/api/tags`
2. Check available benchmark prompts in `datasets/prompts/` (smoke.jsonl, qa.jsonl, safety-benchmark.jsonl, safety-reasoning.jsonl, stress-standard.jsonl, stress-reasoning.jsonl)
3. Run the benchmark via the Jemma CLI or directly using `src/jemma/benchmarks/runner.py`
4. Collect results: tokens/sec, time-to-first-token, accuracy scores
5. Compare against baseline in `docs/BENCHMARK_RESULTS.md`
6. Report results in a markdown table
