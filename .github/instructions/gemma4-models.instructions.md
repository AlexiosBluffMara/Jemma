---
description: "Use when working with Gemma 4 model loading, inference, multimodal capabilities, quantization, or model selection. Covers E2B, E4B, 26B-A4B MoE, and 31B variants."
---
# Gemma 4 Model Reference

## Variant Capabilities
| Variant | Params | Modalities | Audio | Video | Context |
|---|---|---|---|---|---|
| E2B | ~2B | Text+Image+Audio+Video | Yes (30s) | Yes (60s@1fps) | 131K |
| E4B | ~4B | Text+Image+Audio+Video | Yes (30s) | Yes (60s@1fps) | 131K |
| 26B-A4B | 25.2B (3.8B active) | Text+Image | No | No | 160K |
| 31B | ~31B | Text+Image | No | No | 131K |

## Loading Pattern
```python
from transformers import AutoProcessor, AutoModelForMultimodalLM
import torch
processor = AutoProcessor.from_pretrained("unsloth/gemma-4-E4B-it")
model = AutoModelForMultimodalLM.from_pretrained(
    "unsloth/gemma-4-E4B-it", dtype=torch.bfloat16, device_map="auto"
)
```

## Key Facts
- All models: Apache 2.0 license, native function calling via `apply_chat_template(tools=[...])`
- Thinking mode: `enable_thinking=True` on all variants
- Audio: 16kHz mono, ~25 tokens/sec, ~300M encoder (E2B/E4B only)
- Vision: variable resolution via token budgets (70/140/280/560/1120)
- HuggingFace class: `AutoModelForMultimodalLM` (NOT `AutoModelForCausalLM`)
- Naming: model name FIRST, gemma reference AFTER (e.g., `jemma-safebrain-gemma-4-e4b-it`)
- Must include trademark notice: "Gemma is a trademark of Google LLC."

## Ollama Integration
- Base URL: `http://127.0.0.1:11434`
- E4B: `gemma4-e4b-it:q8_0` (workstation), E2B: `gemma4-e2b-it:q4_k_m` (mobile)
- Provider: `src/jemma/providers/ollama.py`
