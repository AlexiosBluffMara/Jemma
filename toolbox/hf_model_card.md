---
library_name: transformers
license: apache-2.0
base_model: google/gemma-4-E4B-it
base_model_relation: finetune
tags:
  - gemma4
  - gemma
  - safety
  - trust
  - benchmark
  - local-first
  - ollama
  - unsloth
  - multimodal
  - text-generation
  - image-text-to-text
  - audio
  - function-calling
  - hackathon
  - gemma-4-good-hackathon
pipeline_tag: image-text-to-text
language:
  - en
---

# Jemma SafeBrain — Local Safety Operations on Gemma 4 E4B

> **Gemma is a trademark of Google LLC.**

Jemma SafeBrain is a local-first safety operations framework built on [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it). It benchmarks, routes, and coordinates safe autonomous AI operations entirely on private networks—no cloud required.

**This is a community project for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon). It is NOT an official Google product.**

## Model Details

| Property | Value |
|---|---|
| **Base Model** | [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) |
| **Architecture** | Gemma4ForConditionalGeneration (Dense, 4.5B effective / 8B with PLE) |
| **Modalities** | Text, Image, Audio, Video, Function Calling |
| **Context Window** | 128K tokens |
| **Precision** | BF16 (native Blackwell SM_120) |
| **Attention** | SDPA (Scaled Dot-Product Attention) with hybrid global/sliding window |
| **License** | Apache 2.0 |
| **Hardware Validated** | NVIDIA RTX 5090 (32 GB VRAM) |

## Capabilities Validated

All modalities tested end-to-end on local hardware:

| Capability | Tests | Status | Avg Latency |
|---|---|---|---|
| Text Generation | Basic, Thinking (CoT), System Prompt, Multi-turn | 4/4 PASS | 1.4s (basic), 22.5s (thinking) |
| Image Understanding | Captioning, OCR, Bounding Boxes, Local Image | 4/4 PASS | 6.6s avg |
| Audio Understanding | Classification, ASR Pipeline, Audio + Thinking | 3/3 PASS | 17.6s avg |
| Video Understanding | Description, Thinking, Frame-Level | 3/3 PASS | See demo logs |
| Function Calling | Single tool call, Multi-turn tool use | Native support | Per-task |

## Hardware Optimization

Maximized for RTX 5090 Blackwell architecture:

- **BF16 precision**: Native SM_120 support, no quantization overhead
- **TF32 matmuls**: `torch.backends.cuda.matmul.allow_tf32 = True`
- **cuDNN benchmark**: `torch.backends.cudnn.benchmark = True`
- **SDPA**: Flash-attention-like performance via PyTorch 2.11
- **VRAM budget**: 14.8 GB model + 2.3 GB KV cache + 3 GB activations = ~20.3 GB committed, ~11.5 GB headroom

## Quick Start

```python
from transformers import AutoProcessor, AutoModelForMultimodalLM
import torch

model = AutoModelForMultimodalLM.from_pretrained(
    "soumitty/jemma-safebrain-gemma-4-e4b-it",
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa",
)
processor = AutoProcessor.from_pretrained("soumitty/jemma-safebrain-gemma-4-e4b-it")

messages = [
    {"role": "system", "content": "You are Jemma, a local safety operations AI."},
    {"role": "user", "content": "Analyze the safety of this network configuration."},
]

inputs = processor.apply_chat_template(
    messages, tokenize=True, return_dict=True,
    return_tensors="pt", add_generation_prompt=True,
).to(model.device)

outputs = model.generate(**inputs, max_new_tokens=512, temperature=1.0, top_p=0.95, top_k=64)
response = processor.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print(response)
```

## Multimodal Usage

### Image Analysis
```python
from PIL import Image

messages = [{"role": "user", "content": [
    {"type": "image", "image": Image.open("photo.jpg")},
    {"type": "text", "text": "Describe any safety concerns visible in this image."},
]}]
```

### Audio Processing (E4B exclusive)
```python
messages = [{"role": "user", "content": [
    {"type": "audio", "audio": "recording.wav"},
    {"type": "text", "text": "Transcribe this emergency radio transmission."},
]}]
```

### Function Calling
```python
tools = [{"name": "check_network_status", "description": "Check local network health",
          "parameters": {"type": "object", "properties": {"host": {"type": "string"}}}}]
messages = [
    {"role": "system", "content": [{"type": "text", "text": "You have access to tools."}]},
    {"role": "user", "content": [{"type": "text", "text": "Check if the router is online."}]},
]
```

## Training & Methodology

This initial release publishes the **base E4B model with validated multimodal demos** and hardware-optimized inference configuration. Fine-tuning for safety-specific tasks is in progress using:

- **Framework**: Unsloth + PEFT (QLoRA, 4-bit)
- **Target domains**: Safety incident analysis, emergency communication processing, infrastructure monitoring
- **Dataset**: Custom safety operations dataset (in development)

## Benchmarks

### Inference Performance (RTX 5090, BF16)

| Metric | Value |
|---|---|
| Model load time | 11.1s |
| VRAM at load | 14.8 GB |
| Text generation (short) | ~1.4s |
| Text generation (CoT thinking) | ~22.5s |
| Image captioning | ~13.0s |
| OCR extraction | ~1.8s |
| Object detection (bbox) | ~5.9s |
| Audio classification | ~13.3s |
| ASR pipeline | ~3.1s |

## Project Links

- **GitHub**: [AlexiosBluffMara/Jemma](https://github.com/AlexiosBluffMara/Jemma)
- **Hackathon**: [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)

## License & Attribution

This model is released under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).

Based on [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) by Google DeepMind.

**Gemma is a trademark of Google LLC.**

This is an independent community project and is NOT affiliated with, endorsed by, or sponsored by Google.

## Citation

```bibtex
@misc{jemma-safebrain-2026,
  title={Jemma SafeBrain: Local Safety Operations on Gemma 4 E4B},
  author={Soumit Lahiri},
  year={2026},
  url={https://huggingface.co/soumitty/jemma-safebrain-gemma-4-e4b-it},
  note={Built for the Gemma 4 Good Hackathon}
}
```
