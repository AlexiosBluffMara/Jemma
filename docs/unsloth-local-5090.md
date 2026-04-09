# Unsloth local RTX 5090 workflow

## What the Unsloth notebook is
The original `gemma4-31b-unsloth.ipynb` is a **Colab-oriented supervised fine-tuning notebook** from the Unsloth ecosystem. Its flow is:

1. install Unsloth and the Hugging Face training stack,
2. load a Gemma 4 model in quantized form,
3. add LoRA adapters so only a small fraction of weights are trained,
4. format conversational data into the Gemma 4 chat template,
5. train with TRL's `SFTTrainer`,
6. save adapters or export merged model artifacts.

It is good as a reference, but it assumes a hosted notebook runtime and includes Colab/Kaggle-friendly defaults such as lightweight smoke-test data and a multi-device-friendly `device_map`.

## What changed in the local variant
`gemma4-31b-unsloth-local-5090.ipynb` is the local-first version for this machine profile:

- **GPU:** RTX 5090
- **RAM:** 64 GB
- **Storage:** large SSD-backed dataset/cache directories
- **Target workflow:** local QLoRA training with explicit output paths

The new notebook:

- keeps the core Unsloth flow,
- switches to **single-GPU local loading** with `device_map='auto'`,
- defaults to **`unsloth/gemma-4-31B-it` in 4-bit**,
- uses **SSD-backed cache, dataset, checkpoint, and export directories**,
- supports **WSL/Linux and Windows path detection**,
- expects a prepared local JSONL file for the Second Brain project,
- falls back to a small public dataset for smoke testing.

## Why WSL/Linux is the best option
Use **WSL2 Ubuntu** or native Linux unless you have a strong reason not to.

Reasons:

- CUDA and LLM tooling are usually more stable on Linux/WSL.
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

### Optional environment variables
These are the main knobs used by the new notebook:

```bash
export JEMMA_WORKSPACE_DIR=/home/soumitty/Jemma
export JEMMA_DATA_DIR=/mnt/d/JemmaData
export JEMMA_MODEL_NAME=unsloth/gemma-4-31B-it
export JEMMA_MAX_SEQ_LENGTH=4096
export JEMMA_BATCH_SIZE=1
export JEMMA_GRAD_ACC=8
export JEMMA_EPOCHS=1
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

For the project, the best path is to build a **prepared training file** such as:

`/mnt/d/JemmaData/datasets/second-brain-train.jsonl`

and keep raw source dumps, parsed chunks, and embedding corpora in separate directories.

## Practical tuning guidance
- Start with **31B 4-bit QLoRA**.
- Keep **batch size 1** and adjust with gradient accumulation first.
- Use **4096 context** until the pipeline is stable, then increase carefully.
- Save LoRA adapters first; only export merged or GGUF artifacts when needed.
