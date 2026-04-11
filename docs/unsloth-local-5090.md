# Unsloth local RTX 5090 workflow

## What the notebook is for
The original `gemma4-31b-unsloth.ipynb` is a Colab-oriented supervised fine-tuning notebook from the Unsloth ecosystem. The local variant keeps the same core flow but turns it into a workstation-oriented single-GPU pipeline.

## What changed in the local variant
`gemma4-31b-unsloth-local-5090.ipynb` remains the repo's main local notebook, but it should now be treated as an E4B and E2B-first workflow rather than a 31B-first workflow.

Recommended ladder:

1. `unsloth/gemma-4-E4B-it` as the primary local fine-tuning loop.
2. `unsloth/gemma-4-E2B-it` as the mobile and offline-friendly follow-up target.
3. `unsloth/gemma-4-31B-it` only after the data and prompt pipeline are stable.

Why this order works better on a single RTX 5090:

- E4B is much faster to iterate on while still preserving long-context and agentic behavior.
- E2B gives you a realistic path to phone-friendly exports.
- 31B is still valuable for final comparisons, but it is an expensive debugging target.

## Why WSL/Linux is the best option
Use WSL2 Ubuntu or native Linux unless you have a strong reason not to.

Reasons:

- CUDA and LLM tooling are usually more stable on Linux or WSL.
- `bitsandbytes`, Triton-backed tooling, and export flows tend to be smoother there.
- Most surrounding tooling for evaluation, serving, and data prep also assumes Linux paths and shells.

Native Windows is still supported in the notebook's path logic, but it should be treated as the secondary path rather than the default.

## How to run it
### WSL / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/.venvs/unsloth --python 3.13
source ~/.venvs/unsloth/bin/activate
uv pip install unsloth --torch-backend=auto
uv pip install datasets trl accelerate sentencepiece pillow torchvision
```

### Windows PowerShell
```powershell
winget install -e --id Python.Python.3.13
winget install --id=astral-sh.uv -e
uv venv $HOME\.venvs\unsloth --python 3.13
& $HOME\.venvs\unsloth\Scripts\activate
uv pip install unsloth --torch-backend=auto
uv pip install datasets trl accelerate sentencepiece pillow torchvision
```

## Recommended environment variables
These are the main knobs used by the local notebook.

### Primary workstation run
```bash
export JEMMA_WORKSPACE_DIR=/home/soumitty/Jemma
export JEMMA_DATA_DIR=/mnt/d/JemmaData
export JEMMA_MODEL_NAME=unsloth/gemma-4-E4B-it
export JEMMA_MAX_SEQ_LENGTH=16384
export JEMMA_BATCH_SIZE=1
export JEMMA_GRAD_ACC=8
export JEMMA_EPOCHS=1
export JEMMA_ARTIFACT_SLUG=gemma4-e4b-second-brain
```

### Mobile-friendly follow-up run
```bash
export JEMMA_MODEL_NAME=unsloth/gemma-4-E2B-it
export JEMMA_MAX_SEQ_LENGTH=8192
export JEMMA_ARTIFACT_SLUG=gemma4-e2b-second-brain
```

## Recommended dataset shape
The notebook accepts JSONL rows in one of these forms:

```json
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

```json
{"conversations":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

```json
{"prompt":"...","response":"..."}
```

For this repo, the preferred path is still a prepared training file such as:

`/mnt/d/JemmaData/datasets/second-brain-train.jsonl`

The recommended public-data source bundle is in `docs/second-brain-data-plan.md`.

## Practical tuning guidance
- Start with E4B 4-bit QLoRA, not 31B.
- Use E2B after E4B when you want a phone-friendly or faster follow-up target.
- Treat the full 128K context window as an inference goal, not a first-pass training default.
- Start training at 8K to 16K sequence length, then increase only after memory use and loss look stable.
- Keep batch size 1 and adjust with gradient accumulation first.
- Save LoRA adapters first; only export merged or GGUF artifacts when you need Ollama or mobile deployment.

## Export path to Ollama, llama.cpp, and mobile
The notebook can save:

- LoRA adapters,
- merged checkpoints,
- GGUF exports,
- push to HuggingFace Hub.

Recommended usage:

1. fine-tune E4B in the notebook,
2. export the adapter first,
3. export a merged or GGUF version only when you are ready to register it in Ollama or serve via llama.cpp,
4. use E2B exports for the mobile fallback path,
5. set `JEMMA_PUSH_TO_HUB=1` and `JEMMA_HUB_REPO=your-org/model-name` to publish weights.

### Import into Ollama
```bash
python toolbox/import_gguf_to_ollama.py /path/to/model-Q8_0.gguf --model-name gemma4-e4b-finetuned
```

### Serve via llama.cpp
```bash
# Linux / WSL
./toolbox/launch_llamacpp_server.sh /path/to/model-Q8_0.gguf

# Windows PowerShell
.\toolbox\launch_llamacpp_server.ps1 -GgufPath D:\path\to\model-Q8_0.gguf
```

The llama.cpp server exposes an OpenAI-compatible API at `http://127.0.0.1:8080` which the Jemma `LlamaCppProvider` connects to automatically.

## Deployment handoff
The notebook executor now emits a deployment manifest after a successful run. When you want a hosted Ollama endpoint on Google Cloud:

1. rerun the notebook with `JEMMA_SAVE_GGUF=1`,
2. keep the generated `*-deployment-manifest.json`,
3. run `python toolbox/prepare_ollama_cloud_bundle.py <manifest-path>`.

See `docs/google-cloud-ollama-deployment.md` for the hosted path.
