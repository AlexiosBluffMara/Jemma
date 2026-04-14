---
description: "Use when working on safety policies, LAN actuation, device capabilities, or external network exposure. Covers safety constraints and access controls."
applyTo: ["src/jemma/core/policies.py", "src/jemma/capabilities/**"]
---
# Safety Constraints — Jemma

- Safety policies defined in `src/jemma/core/policies.py`. Never bypass or weaken without explicit user approval.
- LAN capabilities (Hue, SmartPlug, router, Tailscale) require policy check before actuation.
- Never widen network exposure implicitly — all external access must be opt-in.
- GPU safety watchdog (`pipeline/safety_watchdog.py`): 85°C throttle, 90°C emergency stop. Do not raise thresholds.
- API endpoints must validate input via Pydantic schemas. No raw string interpolation into commands.
- Discord bot (`src/jemma/discord/`) must validate permissions before executing actions.
- Config secrets in `configs/secrets.toml` — never commit, never log, never expose in API responses.
- Benchmark safety prompts: `datasets/prompts/safety-benchmark.jsonl`, `datasets/prompts/safety-reasoning.jsonl`.
