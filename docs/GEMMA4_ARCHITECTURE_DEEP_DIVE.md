# Gemma 4 Architecture Deep Dive

> **Author:** Jemma Research Team  
> **Date:** April 13, 2026  
> **Context:** Gemma 4 Good Hackathon (Deadline: May 18, 2026)  
> **Hardware:** NVIDIA RTX 5090 32GB + Ollama + Unsloth  
> **Sources:** Google DeepMind model cards, HuggingFace, Ollama, Unsloth docs, Google Blog  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Family Overview & Architecture Innovations](#family-overview--architecture-innovations)
3. [Model-by-Model Breakdown](#model-by-model-breakdown)
   - [Gemma 4 E2B](#1-gemma-4-e2b-effective-2b)
   - [Gemma 4 E4B](#2-gemma-4-e4b-effective-4b)
   - [Gemma 4 26B-A4B](#3-gemma-4-26b-a4b-moe)
   - [Gemma 4 31B](#4-gemma-4-31b-dense)
4. [Benchmark Comparison](#benchmark-comparison)
5. [Multimodal Capabilities Matrix](#multimodal-capabilities-matrix)
6. [Quantization & VRAM Requirements](#quantization--vram-requirements)
7. [Ollama Availability](#ollama-availability)
8. [Fine-Tuning with Unsloth](#fine-tuning-with-unsloth)
9. [Strategic Analysis](#strategic-analysis)
10. [Hackathon Recommendations](#hackathon-recommendations)

---

## Executive Summary

Gemma 4 is Google DeepMind's most capable open model family, released April 2, 2026 under **Apache 2.0** license. It comprises four models spanning mobile to workstation deployment:

| Model | Type | Total Params | Effective/Active | Context | Modalities |
|-------|------|-------------|-----------------|---------|------------|
| **E2B** | Dense + PLE | 5.1B | 2.3B effective | 128K | Text, Image, Audio |
| **E4B** | Dense + PLE | 8B | 4.5B effective | 128K | Text, Image, Audio |
| **26B-A4B** | MoE | 25.2B | 3.8B active | 256K | Text, Image |
| **31B** | Dense | 30.7B | 30.7B | 256K | Text, Image |

**Key finding for our hackathon:** E4B is the optimal primary model for RTX 5090 — it fits comfortably in 32GB at Q8_0 (12GB) or BF16 (16GB), supports ALL modalities (text + image + audio + video), has native Unsloth support, trains with just 10-17GB VRAM, and exports cleanly to GGUF/Ollama. The 31B is feasible at Q4_K_M (20GB) for maximum quality inference.

---

## Family Overview & Architecture Innovations

### What Makes Gemma 4 Different from Gemma 2/3

Gemma 4 represents a fundamental architectural leap:

#### 1. Per-Layer Embeddings (PLE) — *New in Gemma 4*

The "E" in E2B/E4B stands for "effective" parameters. PLE gives **each decoder layer its own small embedding table** for every token. These tables are large but only used for quick lookups — the actual compute during forward pass uses the smaller "effective" parameter count.

- **E2B:** 2.3B effective / 5.1B total with embeddings
- **E4B:** 4.5B effective / 8B total with embeddings

**Why this matters:** PLE delivers the representational capacity of a larger model with the inference speed and memory footprint of a smaller one. This is specifically engineered for on-device deployment — you get "8B quality" at "4.5B speed."

#### 2. Hybrid Attention Mechanism

All Gemma 4 models employ a **hybrid attention** design that interleaves:
- **Local sliding window attention** (fast, memory-efficient)
- **Full global attention** (deep context awareness)

The **final layer is always global**, ensuring the model maintains deep awareness for complex tasks.

| Model | Sliding Window Size |
|-------|-------------------|
| E2B | 512 tokens |
| E4B | 512 tokens |
| 26B-A4B | 1024 tokens |
| 31B | 1024 tokens |

#### 3. Unified KV & Proportional RoPE (p-RoPE)

Global attention layers feature **unified Keys and Values** and apply **Proportional RoPE** for memory-optimized long-context processing. This allows the 31B and 26B models to support 256K context without quadratic memory blowup.

#### 4. KV Sharing Across Layers (E2B/E4B)

E2B and E4B share KV state across layers:
- **E2B:** `num_kv_shared_layers = 20`
- **E4B:** `num_kv_shared_layers = 18`

This is a critical implementation detail — it means the cache must always be active during training/inference (see [Unsloth bug fixes](#known-bugs--fixes)).

#### 5. Native System Prompt Support

Unlike Gemma 3 (which used workarounds), Gemma 4 supports the standard `system`, `assistant`, `user` roles natively.

#### 6. Configurable Thinking Mode

All models support built-in reasoning via the `<|think|>` token:
- Add `<|think|>` at start of system prompt to enable
- Model outputs: `<|channel>thought\n[reasoning]<channel|>[answer]`
- **E2B/E4B special behavior:** When thinking is disabled, these models genuinely skip thinking. The 26B/31B models still emit empty thought blocks.

#### 7. Comparison with Competitors

| Feature | Gemma 4 | Llama 4 | Qwen 3 |
|---------|---------|---------|--------|
| License | Apache 2.0 | Llama 3 Community | Apache 2.0 |
| Architecture | Dense + PLE + MoE | Dense + MoE (Scout/Maverick) | Dense + MoE |
| Native Audio | E2B/E4B only | No | No |
| Native Video | Frame-based all models | No | No |
| Function Calling | Native all models | Yes | Yes |
| Thinking Mode | Configurable `<\|think\|>` | Not native | QwQ-style |
| Context Window | 128K-256K | 128K-1M (Scout) | 128K |
| On-device PLE | Yes (E2B/E4B) | No | No |
| Arena Ranking | #3 open (31B), #6 (26B) | Varies | Varies |

---

## Model-by-Model Breakdown

### 1. Gemma 4 E2B (Effective 2B)

**Identity:** Mobile-first, smallest model, full multimodal

#### Architecture

| Property | Value |
|----------|-------|
| Total Parameters | 5.1B (with PLE embeddings) |
| Effective Parameters | 2.3B |
| Layers | 35 |
| Sliding Window | 512 tokens |
| Context Length | 128K tokens |
| Vocabulary Size | 262,144 |
| Vision Encoder | ~150M params |
| Audio Encoder | ~300M params |
| KV Shared Layers | 20 |
| Architecture | Dense + Per-Layer Embeddings |

#### Modalities
- **Text:** Full support
- **Image:** Variable resolution (70/140/280/560/1120 token budgets)
- **Audio:** Native — 30s max, 16kHz mono, ASR + translation
- **Video:** Frame-based — 60s max at 1fps

#### Key Characteristics
- Designed for phones, Raspberry Pi, NVIDIA Jetson Orin Nano
- Lightest weight model, runs on 5GB RAM at 4-bit
- Supports thinking mode with true on/off behavior (no empty blocks when disabled)
- Most parameter-efficient due to aggressive PLE ratio (5.1B total → 2.3B effective = 55% embedding overhead)

---

### 2. Gemma 4 E4B (Effective 4B)

**Identity:** Our primary model. Mid-range, best multimodal capability per VRAM dollar.

#### Architecture

| Property | Value |
|----------|-------|
| Total Parameters | 8B (with PLE embeddings) |
| Effective Parameters | 4.5B |
| Layers | 42 |
| Sliding Window | 512 tokens |
| Context Length | 128K tokens |
| Vocabulary Size | 262,144 |
| Vision Encoder | ~150M params |
| Audio Encoder | ~300M params |
| KV Shared Layers | 18 |
| Architecture | Dense + Per-Layer Embeddings |

#### Modalities
- **Text:** Full support
- **Image:** Variable resolution (70/140/280/560/1120 token budgets)
- **Audio:** Native — 30s max, 16kHz mono, ASR + translation
- **Video:** Frame-based — 60s max at 1fps

#### Key Characteristics
- Sweet spot for on-device multimodal AI
- Only 56% embedding overhead (8B → 4.5B)
- 7 more layers than E2B (42 vs 35) for deeper reasoning
- Same vision/audio encoders as E2B but better downstream quality
- **Unsloth recommends E4B QLoRA over E2B LoRA** — bigger model with minimal quantization accuracy loss
- Ollama default quantization is Q4_K_M at 9.6GB

---

### 3. Gemma 4 26B-A4B (MoE)

**Identity:** Speed champion. MoE architecture delivering 26B-quality at 4B-inference cost.

#### Architecture

| Property | Value |
|----------|-------|
| Total Parameters | 25.2B |
| Active Parameters | 3.8B per token |
| Layers | 30 |
| Expert Count | 128 total + 1 shared, 8 active per token |
| Sliding Window | 1024 tokens |
| Context Length | 256K tokens |
| Vocabulary Size | 262,144 |
| Vision Encoder | ~550M params |
| Audio Encoder | None |
| KV Shared Layers | 0 |
| Architecture | Mixture-of-Experts |

#### Modalities
- **Text:** Full support
- **Image:** Variable resolution (larger ~550M vision encoder than E2B/E4B)
- **Audio:** NOT supported
- **Video:** Frame-based (via image processor)

#### Key Characteristics
- **128 experts + 1 shared, 8 active per token** — extremely granular routing
- Runs almost as fast as a 4B model despite 25.2B total params
- Arena AI #6 open model — outcompetes models 20x its size
- Larger sliding window (1024 vs 512) and longer context (256K vs 128K)
- Larger vision encoder (~550M vs ~150M) for better image understanding
- **MoE QLoRA is NOT recommended by Unsloth** — use bf16 LoRA instead
- Requires >40GB for LoRA training (doesn't fit RTX 5090 for training)

---

### 4. Gemma 4 31B (Dense)

**Identity:** Maximum quality. Strongest Gemma 4 model, dense architecture.

#### Architecture

| Property | Value |
|----------|-------|
| Total Parameters | 30.7B |
| Effective Parameters | 30.7B (no PLE) |
| Layers | 60 |
| Sliding Window | 1024 tokens |
| Context Length | 256K tokens |
| Vocabulary Size | 262,144 |
| Vision Encoder | ~550M params |
| Audio Encoder | None |
| KV Shared Layers | 0 |
| Architecture | Dense (standard) |

#### Modalities
- **Text:** Full support
- **Image:** Variable resolution (larger ~550M vision encoder)
- **Audio:** NOT supported
- **Video:** Frame-based (via image processor)

#### Key Characteristics
- Arena AI **#3 open model in the world** on text leaderboard
- 60 layers — deepest in the family
- Same vision encoder as 26B-A4B (~550M)
- No audio support
- BF16 requires ~63GB (doesn't fit single RTX 5090)
- Q4_K_M fits at 20GB — leaves 12GB for context/KV cache
- Q8_0 at 34GB — exceeds RTX 5090 32GB
- 31B QLoRA training requires ~22GB VRAM with Unsloth
- Best foundation for fine-tuning if you want max quality and can accept text+image only

---

## Benchmark Comparison

All benchmarks are for instruction-tuned (-it) variants with thinking enabled.

### Text Benchmarks

| Benchmark | 31B | 26B-A4B | E4B | E2B |
|-----------|-----|---------|-----|-----|
| **MMLU Pro** | 85.2% | 82.6% | 69.4% | 60.0% |
| **AIME 2026** (no tools) | 89.2% | 88.3% | 42.5% | 37.5% |
| **LiveCodeBench v6** | 80.0% | 77.1% | 52.0% | 44.0% |
| **Codeforces ELO** | 2150 | 1718 | 940 | 633 |
| **GPQA Diamond** | 84.3% | 82.3% | 58.6% | 43.4% |
| **Tau2** (avg over 3) | 76.9% | 68.2% | 42.2% | 24.5% |
| **HLE** (no tools) | 19.5% | 8.7% | — | — |
| **HLE** (with search) | 26.5% | 17.2% | — | — |
| **BigBench Extra Hard** | 74.4% | 64.8% | 33.1% | 21.9% |
| **MMMLU** | 88.4% | 86.3% | 76.6% | 67.4% |

### Vision Benchmarks

| Benchmark | 31B | 26B-A4B | E4B | E2B |
|-----------|-----|---------|-----|-----|
| **MMMU Pro** | 76.9% | 73.8% | 52.6% | 44.2% |
| **OmniDocBench 1.5** (↓ better) | 0.131 | 0.149 | 0.181 | 0.290 |
| **MATH-Vision** | 85.6% | 82.4% | 59.5% | 52.4% |
| **MedXPertQA MM** | 61.3% | 58.1% | 28.7% | 23.5% |

### Audio Benchmarks (E2B/E4B only)

| Benchmark | E4B | E2B |
|-----------|-----|-----|
| **CoVoST** | 35.54 | 33.47 |
| **FLEURS** (↓ better) | 0.08 | 0.09 |

### Long Context

| Benchmark | 31B | 26B-A4B | E4B | E2B |
|-----------|-----|---------|-----|-----|
| **MRCR v2 8-needle 128K** | 66.4% | 44.1% | 25.4% | 19.1% |

### Key Observations

1. **31B and 26B-A4B are in a different league** for reasoning/coding — AIME 2026 at 89.2% and 88.3% respectively vs E4B at 42.5%
2. **26B-A4B closely tracks 31B** on most benchmarks despite running at 4B-active speed
3. **E4B is the best "small" model** — consistently 5-10% above E2B across all tasks
4. **Audio is exclusive to E2B/E4B** — neither 26B nor 31B can process audio
5. **Vision quality scales with encoder size** — 31B/26B use ~550M vs E2B/E4B at ~150M

---

## Multimodal Capabilities Matrix

| Capability | E2B | E4B | 26B-A4B | 31B |
|-----------|-----|-----|---------|-----|
| Text Generation | ✅ | ✅ | ✅ | ✅ |
| Image Understanding | ✅ (~150M) | ✅ (~150M) | ✅ (~550M) | ✅ (~550M) |
| Audio (ASR/Translation) | ✅ (~300M) | ✅ (~300M) | ❌ | ❌ |
| Video (frame-based) | ✅ | ✅ | ✅ | ✅ |
| Function Calling | ✅ | ✅ | ✅ | ✅ |
| Thinking Mode | ✅ (true off) | ✅ (true off) | ✅ (empty block) | ✅ (empty block) |
| System Prompts | ✅ | ✅ | ✅ | ✅ |
| Interleaved Multimodal | ✅ | ✅ | ✅ | ✅ |
| Variable Image Resolution | ✅ | ✅ | ✅ | ✅ |
| OCR/Document Parsing | ✅ | ✅ | ✅ (better) | ✅ (best) |
| Code Generation | ✅ | ✅ | ✅ | ✅ |
| Multilingual (140+ langs) | ✅ | ✅ | ✅ | ✅ |

### Audio Constraints
- Max duration: 30 seconds
- Format: 16kHz mono
- Token rate: ~25 tokens/second
- Encoder size: ~300M parameters
- Capabilities: ASR, speech-to-text translation

### Video Constraints
- Max duration: 60 seconds
- Processing: 1 frame per second
- Native on E2B/E4B, frame-based on all models

### Image Resolution Token Budgets
| Budget | Tokens | Best For |
|--------|--------|----------|
| 70 | 70 | Quick classification |
| 140 | 140 | Captioning, fast video |
| 280 | 280 | General multimodal chat |
| 560 | 560 | Charts, screens, UI reasoning |
| 1120 | 1120 | OCR, document parsing, small text |

---

## Quantization & VRAM Requirements

### Inference Memory (Model Weight Size)

| Model | BF16 | Q8_0 | Q4_K_M | 4-bit GGUF |
|-------|------|------|--------|-----------|
| **E2B** | 10 GB | 8.1 GB | 7.2 GB | ~5 GB |
| **E4B** | 16 GB | 12 GB | 9.6 GB | ~6 GB |
| **26B-A4B** | 52 GB | 28 GB | 18 GB | ~18 GB |
| **31B** | 63 GB | 34 GB | 20 GB | ~20 GB |

### Training VRAM (Unsloth)

| Model | Method | VRAM Required | RTX 5090 Feasible? |
|-------|--------|--------------|-------------------|
| **E2B** | LoRA | 8-10 GB | ✅ Easily |
| **E4B** | LoRA | 17 GB | ✅ Yes |
| **E4B** | QLoRA (4-bit) | ~10 GB | ✅ Easily |
| **26B-A4B** | LoRA (bf16) | >40 GB | ❌ No |
| **26B-A4B** | QLoRA (4-bit) | ~22 GB* | ⚠️ Not recommended for MoE |
| **31B** | QLoRA (4-bit) | ~22 GB | ✅ Yes |
| **31B** | LoRA (bf16) | >48 GB | ❌ No |

> *Unsloth explicitly warns: "MoE QLoRA not recommended, dense 31B is fine." Use bf16 LoRA for 26B-A4B if you have the memory.

### RTX 5090 (32GB) Fit Analysis

| Scenario | Model | Quant | VRAM Used | Headroom |
|----------|-------|-------|-----------|----------|
| **Inference** | E4B | BF16 | 16 GB | 16 GB for KV cache |
| **Inference** | E4B | Q8_0 | 12 GB | 20 GB for KV cache |
| **Inference** | 31B | Q4_K_M | 20 GB | 12 GB for KV cache |
| **Inference** | 26B-A4B | Q4_K_M | 18 GB | 14 GB for KV cache |
| **Training** | E4B | QLoRA 4-bit | ~10 GB | 22 GB for batch/grad |
| **Training** | E4B | LoRA bf16 | ~17 GB | 15 GB for batch/grad |
| **Training** | 31B | QLoRA 4-bit | ~22 GB | 10 GB for batch/grad |

---

## Ollama Availability

All four Gemma 4 models are available in Ollama (2.9M+ total downloads as of April 2026).

### Available Tags

| Tag | Size | Context | Input | Quantization |
|-----|------|---------|-------|-------------|
| `gemma4:latest` / `gemma4:e4b` | 9.6 GB | 128K | Text, Image | Q4_K_M |
| `gemma4:e2b` | 7.2 GB | 128K | Text, Image | Q4_K_M |
| `gemma4:26b` | 18 GB | 256K | Text, Image | Q4_K_M |
| `gemma4:31b` | 20 GB | 256K | Text, Image | Q4_K_M |
| `gemma4:31b-cloud` | — | 256K | Text, Image | Cloud-hosted |
| `gemma4:e2b-it-q4_K_M` | 7.2 GB | 128K | Text, Image | Q4_K_M |
| `gemma4:e2b-it-q8_0` | 8.1 GB | 128K | Text, Image | Q8_0 |
| `gemma4:e2b-it-bf16` | 10 GB | 128K | Text, Image | BF16 |
| `gemma4:e4b-it-q4_K_M` | 9.6 GB | 128K | Text, Image | Q4_K_M |
| `gemma4:e4b-it-q8_0` | 12 GB | 128K | Text, Image | Q8_0 |
| `gemma4:e4b-it-bf16` | 16 GB | 128K | Text, Image | BF16 |
| `gemma4:26b-a4b-it-q4_K_M` | 18 GB | 256K | Text, Image | Q4_K_M |
| `gemma4:26b-a4b-it-q8_0` | 28 GB | 256K | Text, Image | Q8_0 |
| `gemma4:31b-it-q4_K_M` | 20 GB | 256K | Text, Image | Q4_K_M |
| `gemma4:31b-it-q8_0` | 34 GB | 256K | Text, Image | Q8_0 |
| `gemma4:31b-it-bf16` | 63 GB | 256K | Text, Image | BF16 |

### Additional Quantization Formats

Ollama also provides `mxfp8` and `nvfp4` formats:
| Tag | Size | Notes |
|-----|------|-------|
| `gemma4:e2b-mxfp8` | 7.9 GB | Mixed FP8 |
| `gemma4:e2b-nvfp4` | 7.1 GB | NVIDIA FP4 |
| `gemma4:e4b-mxfp8` | 11 GB | Mixed FP8 |
| `gemma4:e4b-nvfp4` | 9.6 GB | NVIDIA FP4 |
| `gemma4:26b-mxfp8` | 27 GB | Mixed FP8 |
| `gemma4:26b-nvfp4` | 17 GB | NVIDIA FP4 |
| `gemma4:31b-mxfp8` | 32 GB | Mixed FP8 |
| `gemma4:31b-nvfp4` | 20 GB | NVIDIA FP4 |

### Ollama Commands

```bash
# Edge models (our primary targets)
ollama run gemma4:e4b          # Default E4B Q4_K_M (9.6GB)
ollama run gemma4:e4b-it-q8_0  # E4B Q8_0 (12GB) - best quality at RTX 5090
ollama run gemma4:e4b-it-bf16  # E4B full precision (16GB)
ollama run gemma4:e2b          # E2B Q4_K_M (7.2GB) - mobile fallback

# Workstation models
ollama run gemma4:31b          # 31B Q4_K_M (20GB) - fits RTX 5090
ollama run gemma4:26b          # 26B Q4_K_M (18GB) - fastest large model
```

> **Note:** Ollama lists input as "Text, Image" — audio processing requires using Transformers/llama.cpp directly with the audio encoder.

---

## Fine-Tuning with Unsloth

### Supported Training Configurations

| Model | SFT | QLoRA | LoRA (bf16) | Full FT | Vision FT | Audio FT | GRPO/RL |
|-------|-----|-------|-------------|---------|-----------|----------|---------|
| E2B | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| E4B | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 26B-A4B | ✅ | ⚠️ | ✅ | ✅ | ✅ | — | ✅ |
| 31B | ✅ | ✅ | ❌* | ✅* | ✅ | — | ✅ |

> *31B bf16 LoRA needs >48GB. QLoRA at 22GB fits RTX 5090. Full FT needs multi-GPU.  
> ⚠️ MoE QLoRA not recommended by Unsloth.

### Recommended Training Configuration (E4B on RTX 5090)

```python
from unsloth import FastModel

model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E4B-it",
    dtype=None,                # Auto detection
    max_seq_length=8192,       # Start with 8K, increase as needed
    load_in_4bit=True,         # QLoRA for memory efficiency
    full_finetuning=False,
)

model = FastModel.get_peft_model(
    model,
    finetune_vision_layers=False,     # Start with text only
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=8,                              # LoRA rank (8-32 range)
    lora_alpha=8,                     # Recommended: alpha == r
    lora_dropout=0,
    bias="none",
    random_state=3407,
    target_modules="all-linear",
)
```

### Training Hyperparameters

```python
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        dataset_text_field="text",
        per_device_train_batch_size=1,     # Keep at 1 for memory
        gradient_accumulation_steps=4,      # Effective batch = 4
        warmup_steps=5,
        max_steps=60,                       # Or num_train_epochs=1
        learning_rate=2e-4,                 # Reduce to 2e-5 for long runs
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.001,
        lr_scheduler_type="linear",
        seed=3407,
        report_to="none",
    ),
)
```

### Recommended Settings Per Model

| Parameter | E2B | E4B | 31B QLoRA | 26B-A4B |
|-----------|-----|-----|-----------|---------|
| `load_in_4bit` | True | True | True | False |
| `load_in_16bit` | False | False | False | True |
| LoRA `r` | 8 | 8-32 | 8-16 | 8 |
| `lora_alpha` | 8 | 8-32 | 8-16 | 8 |
| `max_seq_length` | 4096-8192 | 4096-8192 | 2048-4096 | 2048 |
| `batch_size` | 2 | 1-2 | 1 | 1 |
| `learning_rate` | 2e-4 | 2e-4 | 2e-4 | 2e-4 |
| Training VRAM | 8-10GB | 10-17GB | 22GB | >40GB |
| Chat template | `gemma-4` | `gemma-4-thinking` | `gemma-4-thinking` | `gemma-4-thinking` |

### Vision Fine-Tuning (E2B/E4B)

```python
from unsloth import FastVisionModel

model, processor = FastVisionModel.from_pretrained(
    "unsloth/gemma-4-E4B-it",
    load_in_4bit=True,
    use_gradient_checkpointing="unsloth",
)

model = FastVisionModel.get_peft_model(
    model,
    finetune_vision_layers=True,      # Enable for vision tasks
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=32,                              # Higher rank for vision
    lora_alpha=32,
    lora_dropout=0,
    bias="none",
    target_modules="all-linear",
)
```

### GGUF Export

```python
# Export to GGUF for Ollama deployment
model.save_pretrained_gguf("output_dir", tokenizer, quantization_method="q4_k_m")
model.save_pretrained_gguf("output_dir", tokenizer, quantization_method="q8_0")
model.save_pretrained_gguf("output_dir", tokenizer, quantization_method="f16")

# Push to Hugging Face
model.push_to_hub_gguf("soumitty/model-name", tokenizer, quantization_method="q4_k_m")
```

### Known Bugs & Fixes

#### 1. `use_cache=True` is REQUIRED (E2B/E4B)

**Critical:** E2B and E4B share KV state across layers. When `use_cache=False` (as many QLoRA tutorials set), shared KV layers recompute K/V locally, producing **garbage logits**. Unsloth has fixed this internally.

```
# Before fix:
use_cache=True  -> '1 + 1 = **2**'
use_cache=False -> 'BROAD\肯. Specificallyboard K supposed\_n통'

# After Unsloth fix: both produce correct output
```

#### 2. IndexError on 31B and 26B-A4B

Both models ship with `num_kv_shared_layers=0`. Python's `-0 == 0` causes `layer_types[:-0]` to collapse to `[]`, crashing the cache. Unsloth patches this.

#### 3. Gradient Accumulation Loss Inflation

Standard Transformers/TRL may show inflated losses (100-300+) during training. This is a gradient accumulation normalization bug that Unsloth fixes.

#### 4. Audio FP16 Overflow

`Gemma4AudioAttention` uses `attention_invalid_logits_value = -1e9` which overflows FP16's max of 65504 on older GPUs (T4). Use BF16 or Unsloth's fix.

#### 5. Normal Training Loss Values

- **E2B/E4B:** Loss of 13-15 is normal for multimodal models (common quirk)
- **26B/31B:** Loss of 1-3 is normal; vision tasks will be 2x higher (3-5)

### Training Tips from Unsloth

1. **Prefer E4B QLoRA over E2B LoRA** — bigger model, minimal quantization accuracy loss
2. **Use `gemma-4-thinking` template for 26B/31B**, `gemma-4` for E2B/E4B without thinking
3. **Mix 75% reasoning + 25% direct answers** to preserve reasoning ability during SFT
4. **Only keep final visible answer in chat history** for multi-turn — never feed thought blocks back
5. **Start with `finetune_vision_layers=False`** and add vision later if task requires it
6. **Use `use_gradient_checkpointing="unsloth"`** for extended context and reduced VRAM
7. **Do NOT use CUDA 13.2 runtime** for any GGUF — it causes poor outputs

---

## Strategic Analysis

### 1. Ease of Use vs Features

**Winner: E4B**

| Criterion | E4B Score | Rationale |
|-----------|-----------|-----------|
| Setup complexity | ⭐⭐⭐⭐⭐ | Single `ollama run gemma4:e4b`, done |
| Fine-tuning ease | ⭐⭐⭐⭐⭐ | Unsloth free notebooks, works on 10GB VRAM |
| Multimodal coverage | ⭐⭐⭐⭐⭐ | Only model with ALL modalities (text+image+audio+video) |
| GGUF export | ⭐⭐⭐⭐⭐ | One-line Unsloth export to Ollama |
| Community support | ⭐⭐⭐⭐ | 1.4M+ HF downloads, 73+ GGUF quantizations |
| Documentation | ⭐⭐⭐⭐⭐ | Best documented via Google, HF, Unsloth, Ollama |

### 2. Best for All Features

**Winner: E4B for modality breadth, 31B for quality ceiling**

- **E4B** is the ONLY model that supports text + image + audio + video natively
- **31B** has the highest quality on every benchmark but lacks audio
- **For hackathon multimodal demos:** E4B is the clear choice
- **For best possible benchmark scores:** 31B Q4_K_M at 20GB

### 3. Best for Optimization/Hackathon (RTX 5090 32GB)

**Primary: E4B | Secondary: 31B Q4_K_M**

#### Recommended Multi-Model Strategy

```
┌─────────────────────────────────────────────────┐
│         RTX 5090 32GB Budget Allocation          │
├─────────────────────────────────────────────────┤
│                                                  │
│  TRAINING PHASE (Unsloth):                       │
│  ├─ E4B QLoRA: ~10-12GB VRAM                    │
│  ├─ 31B QLoRA: ~22GB VRAM                       │
│  └─ Leaves room for batch/context                │
│                                                  │
│  INFERENCE PHASE (Ollama):                       │
│  ├─ E4B Q8_0: 12GB  → 20GB for KV cache         │
│  ├─ E4B BF16: 16GB  → 16GB for KV cache         │
│  ├─ 31B Q4_K_M: 20GB → 12GB for KV cache        │
│  └─ E2B Q4_K_M: 7.2GB → fallback/mobile demo    │
│                                                  │
│  DUAL-MODEL SERVING:                             │
│  ├─ E4B Q8_0 (12GB) + E2B Q4_K_M (7.2GB)       │
│  │   = 19.2GB → fits with headroom              │
│  └─ Enables smart routing by task complexity     │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 4. Architecture Innovations Summary

| Innovation | Gemma 4 | Gemma 3 | Gemma 2 |
|-----------|---------|---------|---------|
| PLE (Per-Layer Embeddings) | ✅ E2B/E4B | ❌ | ❌ |
| Hybrid Sliding+Global Attention | ✅ All | Partial | ❌ |
| Unified KV + p-RoPE | ✅ All | ❌ | ❌ |
| KV Sharing Across Layers | ✅ E2B/E4B | ❌ | ❌ |
| Native Audio Encoder | ✅ E2B/E4B | ❌ | ❌ |
| Native System Prompts | ✅ | ❌ | ❌ |
| Configurable Thinking | ✅ `<\|think\|>` | ❌ | ❌ |
| MoE (128 experts) | ✅ 26B-A4B | ❌ | ❌ |
| Variable Image Resolution | ✅ 5 budgets | Limited | ❌ |
| Apache 2.0 License | ✅ | ❌ (Gemma TOS) | ❌ (Gemma TOS) |

### 5. Fine-Tuning Strategy Recommendations

#### For E4B (Primary Hackathon Model)

```
Method:    QLoRA (4-bit) via Unsloth
Rank:      r=32, alpha=32 (for vision tasks)
           r=8, alpha=8 (for text-only tasks)
Modules:   all-linear (attention + MLP)
Seq Len:   4096 (start), up to 8192
Batch:     1 (per device) × 4 (gradient accumulation)
LR:        2e-4 (short runs), 2e-5 (long runs)
Optimizer: adamw_8bit
Template:  gemma-4 (no thinking) or gemma-4-thinking
VRAM:      ~10-12GB training, leaves 20GB headroom
Export:    GGUF q4_k_m → Ollama
```

#### For 31B (Quality Maximizer)

```
Method:    QLoRA (4-bit) via Unsloth
Rank:      r=8-16, alpha=8-16
Modules:   all-linear
Seq Len:   2048-4096 (memory-constrained)
Batch:     1 × 4
LR:        2e-4
Template:  gemma-4-thinking
VRAM:      ~22GB, tight on RTX 5090
Export:    GGUF q4_k_m → Ollama (20GB inference)
```

### 6. Deployment Strategy

#### Ollama Quantization Ladder (RTX 5090 32GB)

| Priority | Tag | Size | Use Case |
|----------|-----|------|----------|
| 1 | `gemma4:e4b-it-q8_0` | 12 GB | Primary workhorse — best quality/VRAM ratio |
| 2 | `gemma4:e4b-it-bf16` | 16 GB | Maximum E4B quality — full precision |
| 3 | `gemma4:31b-it-q4_K_M` | 20 GB | Best-possible text+vision quality |
| 4 | `gemma4:e2b-it-q4_K_M` | 7.2 GB | Mobile demo / fallback |
| 5 | `gemma4:26b-a4b-it-q4_K_M` | 18 GB | Speed-critical text+vision tasks |

#### GGUF Export Pipeline

```
Fine-tune (Unsloth) → Save GGUF (q4_k_m/q8_0) → Create Modelfile → ollama create → ollama serve
```

#### Memory/Speed Tradeoffs

| Quantization | Quality Loss | Speed Gain | RTX 5090 Context Budget |
|-------------|-------------|------------|------------------------|
| BF16 | 0% (baseline) | 1x | Limited by remaining VRAM |
| Q8_0 | ~1-2% | ~1.3x | Good context headroom |
| Q4_K_M | ~3-5% | ~1.8x | Excellent context headroom |
| Q4_K_S | ~5-7% | ~2x | Maximum context |

---

## Hackathon Recommendations

### Track-Specific Model Selection

| Track | Primary Model | Why |
|-------|--------------|-----|
| **Main Track** ($100K) | E4B fine-tuned + 31B Q4_K_M | E4B for demos/multimodal, 31B for quality benchmarks |
| **Safety & Trust** ($10K) | E4B | Full multimodal safety scanning (text+image+audio) |
| **Ollama Track** ($10K) | E4B Q8_0 / 31B Q4_K_M | Both fit perfectly, demonstrate local-first |
| **Unsloth Track** ($10K) | E4B QLoRA | Best Unsloth experience, free notebooks, GGUF export |

### Concrete Hackathon Plan

1. **Train E4B** with civic safety data using Unsloth QLoRA (10-12GB VRAM)
2. **Export to GGUF** q8_0 for Ollama deployment (12GB → 20GB for context)
3. **Run 31B Q4_K_M** for maximum quality demonstrations (20GB)
4. **Keep E2B Q4_K_M** as mobile/edge proof-of-concept (7.2GB)
5. **Publish weights** to HuggingFace with full model card and benchmarks
6. **Demo multimodal**: text + image + audio → unique to E4B vs competitors

### What Makes Our Setup Special

- **RTX 5090 32GB** can train E4B LoRA (17GB) AND run 31B Q4_K_M (20GB) — just not simultaneously
- **E4B is the only Gemma 4 model with text+image+audio+video** — this is a hackathon differentiator
- **Unsloth + Ollama pipeline** is first-class: train → GGUF → Ollama → serve, all local
- **Apache 2.0** means no license concerns for any deployment or competition

---

## Recommended Sampling Parameters (All Models)

```
temperature = 1.0
top_p = 0.95
top_k = 64
```

These are Google's recommended defaults. Do **not** change unless you have a specific reason.

---

## Best Practices Summary

1. **Place multimodal content before text** in prompts (image/audio first, then instruction)
2. **Strip thinking blocks from chat history** in multi-turn conversations
3. **Use higher image token budgets** (560/1120) for OCR/document tasks
4. **Use lower budgets** (70/140) for classification/captioning/video
5. **Audio max 30 seconds**, video max 60 seconds at 1fps
6. **End-of-sentence token** is `<turn|>`
7. **Start with 32K context** for responsiveness, scale up as needed
8. **Keep repetition penalty at 1.0** unless you see looping

---

## References

- [Google AI Model Card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [HuggingFace google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it)
- [HuggingFace google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it)
- [HuggingFace google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it)
- [HuggingFace google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it)
- [Google Blog: Gemma 4](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)
- [Ollama Gemma 4](https://ollama.com/library/gemma4)
- [Unsloth Gemma 4 Run Guide](https://unsloth.ai/docs/models/gemma-4)
- [Unsloth Gemma 4 Train Guide](https://unsloth.ai/docs/models/gemma-4/train)
- [Unsloth Gemma 4 GGUFs (HuggingFace)](https://huggingface.co/collections/unsloth/gemma-4)
