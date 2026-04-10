# Gemma 4 E2B and E4B local rollout

## Goal
Get the original Gemma 4 E2B and E4B checkpoints onto the workstation, register them in Ollama, create quantized local variants, fine-tune the instruct models with Unsloth, and expose a reliable mobile path with Pixel prioritized.

## Source of truth vs deployment artifacts
Use different artifacts for different stages:

- Original local checkpoints: `google/gemma-4-E2B`, `google/gemma-4-E2B-it`, `google/gemma-4-E4B`, `google/gemma-4-E4B-it`
- Unsloth fine-tuning targets: `unsloth/gemma-4-E2B-it`, `unsloth/gemma-4-E4B-it`
- Ollama deployment artifacts: local BF16 aliases plus local quantized aliases
- Mobile fallback artifacts: E2B GGUF exports, with remote-first Ollama as the primary phone path

## Model matrix
| Purpose | Original checkpoint | Unsloth checkpoint | Ollama alias | Default `num_ctx` | Recommendation |
| --- | --- | --- | --- | ---: | --- |
| E4B instruct workstation loop | `google/gemma-4-E4B-it` | `unsloth/gemma-4-E4B-it` | `gemma4-e4b-it:q8_0` | 131072 | primary local default |
| E4B original baseline | `google/gemma-4-E4B-it` | n/a | `gemma4-e4b-it:bf16` | 131072 | keep for fidelity checks |
| E4B base original | `google/gemma-4-E4B` | n/a | `gemma4-e4b:bf16` | 131072 | optional base-model experiments |
| E2B instruct mobile loop | `google/gemma-4-E2B-it` | `unsloth/gemma-4-E2B-it` | `gemma4-e2b-it:q4_k_m` | 131072 | phone-friendly default |
| E2B original baseline | `google/gemma-4-E2B-it` | n/a | `gemma4-e2b-it:bf16` | 131072 | keep for adapter and export tests |
| E2B base original | `google/gemma-4-E2B` | n/a | `gemma4-e2b:bf16` | 131072 | optional base-model experiments |

## Rollout order
1. Fetch the official Google checkpoints into a local model root.
2. Register BF16 originals in Ollama.
3. Quantize the instruct checkpoints into at least `q8_0` and `q4_k_m`.
4. Fine-tune E4B first in Unsloth.
5. Fine-tune E2B second for mobile and offline fallback.
6. Expose workstation-hosted Ollama to the Pixel over same-LAN or `adb reverse`.
7. Treat iPhone as a same-LAN client first and an offline target only later.

## Commands
### Fastest Ollama path
```bash
ollama pull gemma4:e2b
ollama pull gemma4:e4b
```

### Fetch original checkpoints
```bash
./toolbox/fetch_gemma4_hf.sh
```

### Register the Ollama matrix
```bash
MODEL_ROOT=/mnt/d/JemmaData/models/hf ./toolbox/setup_gemma4_ollama.sh
```

If the BF16 checkpoint directories are not local yet, you can still bootstrap from the official Ollama tags:

```bash
PULL_OFFICIAL_OLLAMA=1 ./toolbox/setup_gemma4_ollama.sh
```

That fallback creates `:stock` aliases for immediate local use. Keep the BF16 local checkpoint path for Unsloth, custom imports, and your own quantization flow.

### Verify the most important aliases
```bash
ollama run gemma4-e4b-it:q8_0 "Reply with exactly: OK"
ollama run gemma4-e2b-it:q4_k_m "Reply with exactly: OK"
```

## Context strategy
- E2B and E4B both support 128K context for inference.
- Use `131072` as the default Ollama context for both unless a benchmark shows you need less.
- Treat long-context training separately from long-context inference. Start Unsloth training at 8K to 16K before pushing sequence length higher.
- Keep `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, and `OLLAMA_NUM_PARALLEL=1` for the workstation service.

## Unsloth strategy
- Primary SFT target: E4B instruct.
- Secondary mobile target: E2B instruct.
- Delay 31B until the prompt format, dataset quality, and retrieval behavior are stable.
- Export adapters first. Export merged or GGUF artifacts only when you are ready to deploy them.

## Public dataset strategy
Follow `docs/second-brain-data-plan.md`.

Short version:
- SFT: Industrial Safety and Health Analytics transformed into grounded QA, summaries, risk classifications, and corrective actions.
- Eval: SQuAD and CNN/DailyMail.
- Demo: construction safety image datasets and optional arXiv-scale retrieval corpus.

## Mobile strategy
- Primary path for both phones: remote-first from the workstation-hosted Ollama endpoint.
- Pixel priority: use same-LAN first, then `adb reverse` for cable-only testing.
- iPhone priority: same-LAN only.
- Offline fallback: quantized E2B export, not full E4B or 31B.

## Do not optimize in the wrong order
- Do not start with 31B before the E4B and E2B loops are stable.
- Do not fine-tune on eval sets such as SQuAD or CNN/DailyMail.
- Do not expose Ollama openly beyond a trusted local network.
- Do not assume phone-local 128K context is realistic. Keep high context on the workstation.
