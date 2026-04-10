# Jemma autonomous benchmark framework

## What this adds
Jemma now has a Python-first framework for running **local autonomous objectives** and **repeatable Gemma benchmarks** against the same Ollama-served model matrix described in the existing rollout docs.

The first implementation is intentionally opinionated:

- **Ollama-first** local inference.
- **Pairwise and solo benchmarks** as the main proving ground.
- **Checkpointed agent loops** instead of open-ended recursion.
- **Deny-by-default LAN adapters** for Tailscale, router status, Hue, and smart plug integrations.

## Product direction
The best hackathon story is **Jemma SafeBrain Command**: a local safety operations system that can benchmark models, route tasks to the best local Gemma variant, and coordinate safe automation on a private network.

That story aligns with:

- Main Track
- Safety & Trust
- Global Resilience
- Ollama
- Unsloth

## Package layout
The framework lives under `src/jemma/` and is split into:

- `agent/` - planner and execution loop
- `benchmarks/` - solo and head-to-head evaluation
- `capabilities/` - private-network adapters
- `config/` - TOML loading for models, LAN, and manifests
- `core/` - shared dataclasses, policies, and artifact storage
- `providers/` - Ollama integration

## Safety model
The framework separates **observation** from **actuation**.

- Tailscale and router checks are read-only.
- Hue and smart plug operations are configured but blocked unless actuation is enabled.
- Confirmation is required for non-observe actions.
- A file-based kill switch at `state/disable_actuation.flag` blocks all actuation even if config is changed.

## Benchmark workflow
1. Define a solo or pairwise manifest in `manifests/benchmarks/`.
2. Define prompt scenarios in `datasets/prompts/*.jsonl`.
3. Run the benchmark through the CLI.
4. Review raw results and summaries under `artifacts/runs/<run-id>/`.

Recommended first comparisons:

1. `gemma4-e4b-it:q8_0` solo
2. `gemma4-e2b-it:q4_k_m` solo
3. `gemma4-e4b-it:q8_0` vs `gemma4-e2b-it:q4_k_m`
4. BF16 baselines after the quantized loop is stable

## Objective workflow
`manifests/objectives/lan-watch.toml` demonstrates the first autonomous path:

- plan with the workstation model,
- call registered capabilities if needed,
- checkpoint each step,
- retry failed inference once on the fallback model.

## Next build targets
- richer benchmark rubrics
- judge-assisted pairwise scoring
- nightly benchmark scheduling
- PDF and retrieval ingestion
- safety-oriented task routing based on benchmark evidence
