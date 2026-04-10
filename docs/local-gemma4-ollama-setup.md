# Local Gemma 4 E2B and E4B with Ollama

This repo now treats Gemma 4 E4B and E2B as the primary local rollout:

- E4B is the default workstation and Unsloth target.
- E2B is the preferred mobile and offline fallback target.
- BF16 local checkpoints are the original source artifacts.
- Quantized Ollama aliases are derived from those original artifacts.

## Prerequisites
- Linux
- NVIDIA driver installed and working
- Ollama 0.20.0 or newer
- enough free disk for four original checkpoints plus quantized aliases
- one of `uvx`, `hf`, or `huggingface-cli` if you want to use the download helper

## Install and start Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
systemctl --user daemon-reload
systemctl --user enable --now ollama.service
systemctl --user status ollama.service --no-pager
```

## Recommended performance settings
Create `~/.config/systemd/user/ollama.service.d/override.conf` with:

```ini
[Service]
Environment=OLLAMA_FLASH_ATTENTION=1
Environment=OLLAMA_KV_CACHE_TYPE=q8_0
Environment=OLLAMA_NUM_PARALLEL=1
```

Then reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart ollama.service
```

These settings matter once you start pushing E2B and E4B toward their full 128K context window.

## Fastest usable Ollama path
If your immediate goal is to get official Gemma 4 E2B and E4B running locally through Ollama, pull the first-party Ollama tags directly:

```bash
ollama pull gemma4:e2b
ollama pull gemma4:e4b
```

Those are the fastest path to a working local E2B and E4B setup. They are suitable for immediate serving, benchmarking, and phone-client testing.

Use the BF16 local checkpoint path below when you also want source-of-truth artifacts for Unsloth, custom imports, or your own quantization pipeline.

## 1. Fetch the original checkpoints
By default the helper downloads the official Google checkpoints into `~/models/hf/google/...`:

```bash
./toolbox/fetch_gemma4_hf.sh
```

Default repos:

- `google/gemma-4-E2B`
- `google/gemma-4-E2B-it`
- `google/gemma-4-E4B`
- `google/gemma-4-E4B-it`

If you want a different root directory:

```bash
MODEL_ROOT=/mnt/d/JemmaData/models/hf ./toolbox/fetch_gemma4_hf.sh
```

## 2. Register BF16 originals and quantized variants in Ollama
The bootstrap script looks for the local checkpoint directories and creates Ollama aliases from them.

```bash
MODEL_ROOT=/mnt/d/JemmaData/models/hf ./toolbox/setup_gemma4_ollama.sh
```

If the local checkpoint directories are not present yet, the same script can fall back to the official Ollama tags instead:

```bash
PULL_OFFICIAL_OLLAMA=1 ./toolbox/setup_gemma4_ollama.sh
```

That fallback is useful when you want immediate local serving and will download the BF16 checkpoints later.
In fallback mode, the script creates `:stock` aliases from the official Ollama packages. It does not pretend those are BF16 source artifacts, and it skips custom requantization until the local BF16 or GGUF sources are present.

By default it creates:

- `gemma4-e2b:bf16`
- `gemma4-e2b-it:bf16`
- `gemma4-e2b-it:q8_0`
- `gemma4-e2b-it:q4_k_m`
- `gemma4-e4b:bf16`
- `gemma4-e4b-it:bf16`
- `gemma4-e4b-it:q8_0`
- `gemma4-e4b-it:q4_k_m`

Optional flags:

```bash
REGISTER_BASE_MODELS=0 ./toolbox/setup_gemma4_ollama.sh
REGISTER_BASE_QUANTS=1 ./toolbox/setup_gemma4_ollama.sh
E2B_NUM_CTX=131072 E4B_NUM_CTX=131072 ./toolbox/setup_gemma4_ollama.sh
RUN_SMOKE_TEST=1 ./toolbox/setup_gemma4_ollama.sh
```

## 3. Verify the local matrix
```bash
ollama list
ollama run gemma4-e4b-it:q8_0 "Reply with exactly: OK"
ollama run gemma4-e2b-it:q4_k_m "Reply with exactly: OK"
```

## 4. Recommended defaults
- Workstation default: `gemma4-e4b-it:q8_0`
- Mobile-target development default: `gemma4-e2b-it:q4_k_m`
- Keep BF16 aliases for conversion, adapter import tests, and high-fidelity comparisons.

## Notes
- The existing `gemma4-26b-moe` alias can coexist with this matrix.
- The setup script accepts either local Safetensors directories or local GGUF files as the source path.
- Ollama's import docs explicitly support local Safetensors and GGUF imports. If a future Ollama build regresses on a direct Gemma 4 Safetensors import, convert the same checkpoint to GGUF and point the script at the GGUF file instead.
- Use the E4B and E2B models for day-to-day work before spending more time on 31B. The 31B model is still useful, but it is not the fastest way to stabilize the training and mobile pipeline.
