# Gemma 4 Model Family — Technical Specifications

## Overview
Gemma 4 is Google's April 2026 open-weights model family, licensed Apache 2.0. Four variants exist:
E2B (2.6B params), E4B (5.98B), 26B-A4B MoE (26B total / 4B active), and 31B dense.

## E2B — Gemma 4 E2B Instruct
- **Parameters**: 2.6 billion
- **Architecture**: Dense transformer, RoPE positional encoding
- **Context window**: 131,072 tokens
- **Modalities**: Text + Image + Audio + Video (full quad-modal)
- **Audio**: 30s max, 16kHz mono, ~25 tokens/sec, ~300M encoder
- **Video**: 60s max at 1fps native
- **VRAM (Q4)**: ~7 GB
- **Ollama throughput (RTX 5090)**: ~285 tok/s
- **Use case**: Edge, mobile, high-throughput inference
- **Official MMLU-Pro**: 60.0%
- **Official GSM8K**: 37.5%
- **Official HumanEval+**: 44.0%

## E4B — Gemma 4 E4B Instruct
- **Parameters**: 5.98 billion
- **Architecture**: Dense transformer, RoPE positional encoding
- **Context window**: 131,072 tokens
- **Modalities**: Text + Image + Audio + Video (full quad-modal)
- **Audio**: 30s max, 16kHz mono, ~25 tokens/sec, ~300M encoder
- **Video**: 60s max at 1fps native
- **VRAM (Q4)**: ~10 GB
- **Ollama throughput (RTX 5090)**: ~200 tok/s
- **Use case**: Workstation inference, fine-tuning base, best multimodal balance
- **Official MMLU-Pro**: 69.4%
- **Official GSM8K**: 42.5%
- **Official HumanEval+**: 52.0%
- **Official HellaSwag**: 76.6%
- **Official ARC-C**: 76.6%

## 26B-A4B — Gemma 4 MoE
- **Parameters**: 26B total, 4B active per token (Mixture of Experts)
- **Context window**: 131,072 tokens
- **Modalities**: Text + Image only (no audio/video)
- **VRAM (Q4)**: ~17 GB
- **Use case**: High-quality text/vision tasks where audio/video not needed

## 31B — Gemma 4 Dense
- **Parameters**: 31 billion dense
- **Context window**: 131,072 tokens
- **Modalities**: Text + Image only (no audio/video)
- **VRAM (Q4)**: ~19 GB
- **Use case**: Maximum quality text/vision, requires beefy GPU

## Key Features (All Models)
- **Function calling**: Native via `apply_chat_template(tools=[...])`
- **Thinking mode**: `enable_thinking=True` on all variants
- **HuggingFace class**: `AutoModelForMultimodalLM` + `AutoProcessor`
- **Fine-tuning**: Unsloth QLoRA (text only), transformers+trl+peft (multimodal)
- **License**: Apache 2.0 (NOT the old Gemma TOS)

## Why E4B for Jemma?
E4B is the only model in the family that offers full quad-modal support (text, image, audio, video) with a reasonable VRAM footprint. The 31B and 26B-A4B models only support text+image. For civic safety surveillance requiring video/audio analysis, E4B is the minimum viable choice. On an RTX 5090 (32GB), E4B at Q4 uses only 10GB, leaving 22GB for concurrent workloads.
