# Gemma 4 Fine-Tuning Research Report — April 13, 2026

**Prepared for**: Jemma SafeBrain Command (Gemma 4 Good Hackathon)  
**Scope**: Comprehensive state-of-the-art survey for Gemma 4 E4B fine-tuning on RTX 5090  
**Methodology**: Web search synthesis from Unsloth docs, HuggingFace, Google blog, Reddit/HN community, arXiv papers, and GitHub issues

---

## 1. Latest Gemma 4 Model Releases (as of April 13, 2026)

### 1.1 Current Lineup — No New Variants Since Initial Release

The Gemma 4 family was released on **March 31, 2026** (per Unsloth changelog) / announced on the Google blog on **April 3, 2026**. As of April 13, **no new sizes, updated checkpoints, or additional variants** have been released. The current lineup remains:

| Variant | Params | Active Params | Modalities | Context | License |
|---------|--------|---------------|------------|---------|---------|
| **E2B** | ~2B | ~2B | Text+Image+Audio+Video | 131K | Apache 2.0 |
| **E4B** | ~4.3B | ~4.3B | Text+Image+Audio+Video | 131K | Apache 2.0 |
| **26B-A4B** (MoE) | ~25.2B | ~3.8B | Text+Image | 160K | Apache 2.0 |
| **31B** (Dense) | ~31B | ~31B | Text+Image | 131K | Apache 2.0 |

### 1.2 Official HuggingFace Repos

- `google/gemma-4-E2B-it` — Instruct, full multimodal
- `google/gemma-4-E4B-it` — Instruct, full multimodal (our primary target)
- `google/gemma-4-26B-A4B-it` — MoE Instruct
- `google/gemma-4-31B-it` — Dense Instruct

### 1.3 Unsloth Quantized Variants (Updated April 8–11, 2026)

Unsloth re-uploaded **all Gemma 4 GGUFs** on April 8 and again on April 11 to incorporate:
- Google's official chat template fixes for tool-calling
- 7 critical llama.cpp fixes (tokenizer, chat template, BOS token, logit softcapping, kv-cache iSWA rotation, byte token handling, CUDA buffer overlap)
- **Action item**: Re-download all Unsloth GGUFs if using older versions

Key repos: `unsloth/gemma-4-E4B-it`, `unsloth/gemma-4-E2B-it`, etc. on HuggingFace.

### 1.4 Key Benchmark Numbers (from Google/community)

From the Artificial Analysis Intelligence Index and Google model card:
- **Gemma 4 31B**: 89.2% on AIME 2026 (harder than AIME 2025); used only 39M output tokens (2.5x more token-efficient than Qwen3.5 27B)
- **Gemma 4 26B-A4B**: Competitive in the ~3-4B active parameter range (Intelligence Index 31)
- **Gemma 4 E4B**: Scores -20 on AA-Omniscience, substantially better than 31B (-45)
- **Gemma 4 E2B**: Scores -24 on AA-Omniscience, comparable to much larger models
- A fine-tuned E4B can outperform an un-tuned 26B MoE on specific tasks (per community reports)

---

## 2. Latest Fine-Tuning Techniques for Small LLMs (2–4B, April 2026)

### 2.1 Unsloth: Still the Recommended Framework — Stronger Than Ever

**Verdict: YES, Unsloth remains the clear leader for Gemma 4 fine-tuning.** Nothing has surpassed it.

Key developments (Unsloth v0.1.36-beta, April 2026):
- **1.5x faster** training vs Flash Attention 2 setups
- **60% less VRAM** than FA2 setups (no accuracy loss)
- E4B QLoRA: **~10GB VRAM** minimum
- E4B LoRA: **~17GB VRAM** (fits RTX 5090 32GB easily)
- **Unsloth Studio**: New web UI for no-code fine-tuning (released March 2026)
  - Compare Mode for LoRA vs original model
  - Built-in export to GGUF/safetensors
  - Speculative decoding support
  - Windows/Linux/Mac support
- **New `FastModel` API** replaces older loading patterns
- **Full fine-tuning (FFT)** now supported (`full_finetuning = True`)
- **GRPO** (reinforcement learning) works with Unsloth inference

**Critical Bug Fixes Unsloth Applied for Gemma 4**:
1. Gradient accumulation loss explosion (losses 100-300 → fixed to expected 10-15)
2. `IndexError` on 26B/31B inference (`num_kv_shared_layers = 0`, Python `-0 == 0` issue)
3. Gibberish outputs for E2B/E4B when `use_cache=False` (KV-shared layers bug)
4. Audio float16 overflow (`-1e9` exceeds fp16 max of 65504)

**Source**: https://unsloth.ai/docs/models/gemma-4/train

### 2.2 LoRA Rank Recommendation

**Current Jemma setting: r=32 — This is good, but consider the nuances.**

From Unsloth's official hyperparameter guide:

| Use Case | Recommended Rank | Notes |
|----------|-----------------|-------|
| Quick text SFT | r=8 | Fast, low VRAM |
| General text SFT (our case) | r=16–32 | Good balance for E4B |
| Multimodal fine-tuning | r=32 | Unsloth's default for vision examples |
| Complex domain adaptation | r=64–128 | Risk of overfitting |
| Simple knowledge injection | r=8 | Sufficient |

**Key guidance from Unsloth**:
- `lora_alpha` should be **equal to rank** (`alpha = r`) or **double** (`alpha = 2*r`)
- Our current `r=32, alpha=64` (`alpha = 2*r`) is **the aggressive learning variant** — good for civic domain injection
- `lora_dropout = 0` is **optimized** in Unsloth's internal code (faster than nonzero)
- Target `all-linear` or explicitly: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`

**Actionable recommendation**: Keep r=32, alpha=64. Consider r=16, alpha=32 if seeing overfitting on civic data.

### 2.3 rsLoRA — Worth Enabling

**rsLoRA (Rank-Stabilized LoRA)** scales alpha by `sqrt(r)` instead of `r`. Unsloth supports it natively:
```python
use_rslora = True  # In Unsloth's get_peft_model
```

From the rsLoRA paper (arXiv:2312.03732) and community consensus: rsLoRA is **strictly better than standard LoRA** with no downsides. It stabilizes training at higher ranks.

**Recommendation**: Enable `use_rslora = True` in the overnight trainer. This is a free improvement.

### 2.4 DoRA — Available but Not Standard

**DoRA (Weight-Decomposed Low-Rank Adaptation)** decomposes weights into magnitude and direction. Supported in PEFT >= 0.9.0 but NOT explicitly integrated into Unsloth's FastModel API. The community consensus is:
- DoRA shows marginal improvement (~1-2%) over LoRA in some benchmarks
- Adds computational overhead
- **Not recommended** for Jemma unless chasing marginal benchmark gains

### 2.5 GaLore and LOMO — Not Recommended for Our Use Case

**GaLore** (arXiv:2403.03507): Memory-efficient training via gradient low-rank projection.
- Reduces optimizer state memory by up to 65.5%
- **Primary use case**: Pre-training, not SFT/QLoRA
- Our E4B QLoRA already fits in 10GB VRAM — GaLore solves a problem we don't have
- Not integrated with Unsloth

**LOMO**: Similar — designed for full-parameter training on limited hardware.
- Irrelevant when using QLoRA/LoRA, which already reduces parameters to ~1%

**Verdict**: Skip both. Stick with QLoRA/LoRA via Unsloth.

### 2.6 Latest trl/SFTTrainer Best Practices

From Unsloth's official Gemma 4 training recipe:

```python
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        dataset_text_field="text",
        per_device_train_batch_size=1,        # Minimize for VRAM
        gradient_accumulation_steps=4,        # Effective batch = 4
        warmup_steps=5,
        max_steps=60,                         # Or num_train_epochs=1
        learning_rate=2e-4,                   # Standard starting point
        logging_steps=1,
        optim="adamw_8bit",                   # 8-bit Adam
        weight_decay=0.001,
        lr_scheduler_type="linear",           # Text SFT
        # lr_scheduler_type="cosine",         # Vision SFT
        seed=3407,
        report_to="none",
    ),
)
```

**Critical new best practices**:
1. **Train on completions only** — Mask user inputs, train only on assistant responses. The QLoRA paper shows ~1% accuracy improvement:
   ```python
   from unsloth.chat_templates import train_on_responses_only
   trainer = train_on_responses_only(
       trainer,
       instruction_part="<|turn>user\n",      # Gemma 4 format
       response_part="<|turn>model\n",         # Gemma 4 format
   )
   ```
2. **Remove `<bos>` when formatting** — The processor adds it:
   ```python
   texts = [tokenizer.apply_chat_template(convo, tokenize=False, 
            add_generation_prompt=False).removeprefix('<bos>') for convo in convos]
   ```
3. **Gradient checkpointing** — Use `"unsloth"` mode for 30% extra VRAM savings:
   ```python
   use_gradient_checkpointing="unsloth"
   ```
4. **Generation settings**: Gemma 4 recommends `temperature=1.0, top_p=0.95, top_k=64`

### 2.7 Optimal Hyperparameters for E4B on RTX 5090

**Recommended configuration (updated from research)**:

| Parameter | Current (Jemma) | Recommended | Rationale |
|-----------|----------------|-------------|-----------|
| LoRA rank | 32 | **32** (keep) | Sweet spot for 4B domain SFT |
| LoRA alpha | 64 | **32 or 64** | alpha=r for conservative, 2r for aggressive |
| use_rslora | False | **True** | Free stability improvement |
| lora_dropout | 0.05 | **0** | Unsloth optimizes for 0; research shows unreliable for short runs |
| max_seq_length | 4096 | **4096** (keep) | Good for SFT; can push to 8192 if data justifies |
| batch_size | 2 | **1** | Free more VRAM for longer contexts |
| gradient_accum | 4 → 8 | **8** (effective BS=8) | More stable gradients |
| learning_rate | 2e-4 | **2e-4** (keep) | Unsloth's recommended starting point |
| lr_scheduler | (not specified) | **cosine** for vision, **linear** for text | Per Unsloth recipes |
| optim | (not specified) | **adamw_8bit** | Memory efficient, standard |
| weight_decay | (not specified) | **0.001** | Unsloth default |
| train_on_completions | No | **Yes** | +1% accuracy, well-established |

---

## 3. Kaggle Competition Techniques and Winning Patterns (2026)

### 3.1 Hackathon-Specific Strategy

The **Gemma 4 Good Hackathon** evaluation criteria:

| Criteria | Points | What Judges Look For |
|----------|--------|---------------------|
| **Impact & Vision** | 40 | Real-world problem solving, societal benefit |
| **Video Pitch** | 30 | 3-min YouTube, clear storytelling, demo |
| **Technical Depth** | 30 | Benchmarks, methodology, published weights |

**Key requirement**: "If training a model, publish your weights and benchmarks."

### 3.2 Data Selection and Curation (Winning Patterns)

From Kaggle winning solutions analysis:
1. **Quality over quantity** — Curate a small, high-quality dataset rather than large noisy one
2. **Domain-specific synthetic data** — Use the base model to generate training data, then filter
3. **Multi-source mixing** — Combine real civic data with synthetic expansions (Jemma already does this)
4. **Validation set integrity** — Keep validation set completely unseen, representative of eval distribution
5. **Format consistency** — Ensure 100% of training examples follow the exact chat template format

**For Jemma specifically**: The civic SFT pipeline (food inspections, 311 requests, crime data, payroll) is strong. Consider:
- Adding safety-specific training examples (for Safety & Trust track)
- Adding structured output examples (JSON, tables) to improve benchmark scores
- Expanding multilingual civic data (Gemma 4 supports 140 languages)

### 3.3 Evaluation Frameworks

| Framework | Best For | Integration Path |
|-----------|----------|-----------------|
| **lm-eval-harness** (EleutherAI) | Standard academic benchmarks | `pip install lm-eval`, supports HF models directly |
| **tinyBenchmarks** | Quick approximation of full benchmarks | Subset selection from lm-eval-harness |
| **Custom benchmark suite** | Domain-specific evaluation | Already built in Jemma (14 categories) |
| **Chatbot Arena** | Human preference scoring | Submit model for community evaluation |

---

## 4. Best Open-Source Evaluation Benchmarks for Fine-Tuned E4B

### 4.1 lm-eval-harness Tasks (Most Appropriate for 4B Model)

**Tier 1 — Must-Run (matches hackathon evaluation expectations)**:
| Task | Category | Why Important |
|------|----------|---------------|
| `mmlu` | Knowledge | Industry standard, expected by judges |
| `gsm8k` | Math reasoning | Key reasoning benchmark |
| `hellaswag` | Commonsense | Classic LLM benchmark |
| `arc_challenge` | Science reasoning | Tests reasoning depth |
| `truthfulqa_mc2` | Factuality | Measures hallucination resistance |
| `winogrande` | Coreference | Standard inclusion |

**Tier 2 — Differentiators (impressive for 4B model)**:
| Task | Category | Why Important |
|------|----------|---------------|
| `gpqa` | Graduate-level science | Shows depth beyond size class |
| `ifeval` | Instruction following | Critical for agent/safety use cases |
| `bbh` (Big Bench Hard) | Complex reasoning | Good for showing fine-tuning gains |
| `humaneval` | Code generation | Practical capability |

**Tier 3 — Domain/Safety (for Safety & Trust track)**:
| Task | Category | Why Important |
|------|----------|---------------|
| `toxigen` | Toxicity detection | Safety benchmark |
| `bbq` | Social bias | Bias detection |
| Custom civic QA | Domain knowledge | Shows fine-tuning impact |
| Custom safety refusal | Safety | Shows Safety & Trust compliance |

### 4.2 Safety-Specific Benchmarks

For the **Safety & Trust track** ($10K prize), prioritize:

| Benchmark | Source | What It Tests |
|-----------|--------|---------------|
| **HarmBench** | mazeika2024 | Jailbreak resistance for LLMs and multimodal models |
| **SafetyBench** | zhang2024 | 7 safety categories, multiple-choice format |
| **TrustLLM** | sun2024 | 30 public datasets for multidimensional trustworthiness |
| **StrongReject** | soulystrongreject | Circumvention resistance |
| **JailbreakBench** | chaojailbreakbench | Jailbreak vulnerability evaluation |
| **SafeRBench** | 2026, arXiv | NEW — First benchmark for Large Reasoning Models safety (input → trace → output) |
| **RealToxicityPrompts** | gehman2020 | Toxicity quantification |
| **BBQ** | parrish2022 | Social bias in QA |

**SafeRBench** (2026) is particularly relevant — it evaluates safety across reasoning chains, not just outputs. This aligns perfectly with Gemma 4's thinking mode.

### 4.3 Gemma-Specific Leaderboards

- **Chatbot Arena / LMSYS**: Gemma 4 models are being actively evaluated
- **Artificial Analysis Intelligence Index**: Gemma 4 31B benchmark data available
- **Open LLM Leaderboard (v2)**: HuggingFace, supports custom model submissions
- **No Gemma-4-specific leaderboard exists yet** — opportunity to create one as part of the hackathon submission

---

## 5. Community Trends — Twitter/X and ML Community (April 2026)

### 5.1 Key Findings and Gotchas

**Bug: High initial loss is NORMAL for E2B/E4B** (Unsloth confirmed):
> "If you see Gemma-4 E2B and E4B having a loss of 13-15, this is perfectly normal — this is a common quirk of multimodal models."

This affected many practitioners who thought their training was broken. 26B and 31B have normal loss at 1-3.

**Bug: `use_cache=False` produces garbage** (Critical, now fixed in Unsloth):
Gemma 4 E2B/E4B share KV state across layers (`num_kv_shared_layers = 20 and 18`). When `use_cache=False` (as every QLoRA tutorial sets), KV-shared layers recompute locally → garbage logits. **Unsloth fixed this**, but other training frameworks may still be affected.

**Community consensus on model quality**:
- E4B is "amazing" — 4-bit GGUF can do web search, function calling (r/unsloth, 22h ago)
- Fine-tuned E4B can match untrained 26B on domain tasks
- Ollama benchmarks on Mac Mini M4: ~24.4 t/s (Ollama) vs ~19.5 t/s (LM Studio) for E4B
- Claude Code users are running Gemma 4 as coding backend successfully

**Data formatting gotcha**:
- Gemma 4 uses `<|turn>user\n` / `<|turn>model\n` — different from Gemma 3's `<start_of_turn>` format
- For thinking mode: `enable_thinking=True` in `apply_chat_template`
- Multi-turn: do NOT feed earlier thought blocks back into later turns
- Use non-thinking template for small models (E2B/E4B), thinking for larger (26B/31B)

**MoE 26B gotcha**: LoRA on 26B-A4B has abnormally low trainable parameters (~0.91% at r=128). QLoRA not recommended for MoE; use bf16 LoRA instead.

### 5.2 Community Tips (Verified)

1. **Prefer E4B QLoRA over E2B LoRA** — Bigger model + quantization accuracy difference is miniscule
2. **E4B LoRA (16-bit) is even better** if you have VRAM — RTX 5090 can handle it at 17GB
3. **Mix reasoning and direct answers** — Keep min 75% reasoning examples to preserve reasoning ability
4. **Use `unsloth` gradient checkpointing** — 30% VRAM savings, enables longer contexts
5. **Same chat template at inference** — Biggest cause of degraded GGUF exports is wrong template
6. **Reduce learning rate for long runs** — Start at 2e-4, reduce to 2e-5 for full epoch runs

---

## 6. Hardware Optimization for RTX 5090 (32GB VRAM)

### 6.1 Flash Attention Status on RTX 5090 (SM 120 / Blackwell)

**Critical finding: Flash Attention is complicated on RTX 5090.**

| FA Version | RTX 5090 Status | Notes |
|------------|----------------|-------|
| **FA2 (flash-attn 2.x)** | Partial — Compilation issues | flash-attn 2.7.3 from source + `--no-build-isolation` works for some; CUDA errors reported on xformers |
| **FA3 (flash-attn 3.x)** | **Does NOT support 5090** | FA3 targets SM 90 (H100/H200), not SM 120. Issue #1825 confirms "always fails to compile with 5090" |
| **FA4 (flash-attn 4.x)** | Targets SM 100 (B200) | Not for consumer Blackwell (SM 120). FAQ in Issue #2376 |
| **cuDNN Flash Attention** | Works via PyTorch SDPA | cuDNN 9.x has BF16 fused flash attention, up to 50% improvement |
| **Unsloth's built-in** | **Works — recommended** | Bypasses FA entirely; 60% less VRAM than FA2, 1.5x faster |

**Recommendation**: **Use Unsloth's built-in attention kernels.** They are specifically optimized and avoid all FA compatibility issues on 5090. Unsloth explicitly claims "~1.5x faster with ~60% less VRAM than FA2 setups."

### 6.2 SDPA vs Flash Attention

PyTorch's `torch.nn.functional.scaled_dot_product_attention` (SDPA) automatically dispatches to the best available backend:
1. cuDNN (if available and inputs match)
2. Flash Attention 2 (if installed)
3. Memory-efficient attention (xformers fallback)
4. Math (Python fallback)

**On RTX 5090**: SDPA will use cuDNN backend, which IS optimized for Blackwell. Some users report convergence differences between FA2 and SDPA — one GitHub issue (#2151) reports "significant training loss convergence" differences between SDPA and flash-attention on BF16.

**Recommendation**: For training via Unsloth, this is handled automatically. If using raw transformers, let SDPA auto-dispatch rather than forcing flash-attn.

### 6.3 BF16 vs TF32 Training

| Precision | RTX 5090 TFLOPs | Use Case | Notes |
|-----------|-----------------|----------|-------|
| **BF16** | 209.5 | Training (default) | Standard for LLM fine-tuning, Gemma 4 native |
| **TF32** | 209.5 (same compute unit) | Matmul accumulation | TF32 is automatic in A100+; less relevant with BF16 training |
| **FP16** | 209.5 | NOT recommended | Gemma 4 audio overflow bug with fp16 (-1e9 > 65504) |
| **Q4 (QLoRA)** | N/A (integer ops) | Memory savings | 4x less VRAM than bf16 LoRA |

**Key insight**: RTX 5090's BF16 TFLOPs (209.5) are modest compared to datacenter GPUs (B200: 2250 TFLOPs). The 5090's advantage is **32GB VRAM** and **1TB/s memory bandwidth**.

**Recommendation**: 
- Always use `bf16=True` in training config
- Enable `torch.set_float32_matmul_precision('high')` for TF32 accumulation
- Use QLoRA (4-bit) for memory efficiency — the accuracy loss vs LoRA is "miniscule" per Unsloth
- Avoid fp16 entirely (Gemma 4 has known fp16 overflow issues)

### 6.4 RTX 5090-Specific VRAM Budget

For Jemma's tri-model stack on 32GB:

| Component | VRAM (est.) | Notes |
|-----------|-------------|-------|
| E4B QLoRA training | ~10GB | 4-bit quantized base + LoRA adapters |
| E4B LoRA training | ~17GB | 16-bit LoRA, higher quality |
| E4B inference (Q4_K_M) | ~5GB | For Ollama serving |
| SAM 3.1 inference | ~7GB | Segment Anything 3.1 |
| System/CUDA overhead | ~2-3GB | Varies |

**Training mode**: E4B QLoRA at 10GB leaves ~20GB headroom (ample)  
**Training mode**: E4B LoRA at 17GB leaves ~13GB headroom (comfortable)  
**Inference mode**: E4B (5GB) + SAM 3.1 (7GB) = 12GB → 20GB free for batch processing

### 6.5 Additional RTX 5090 Tips

1. **vLLM on 5090**: Requires PyTorch 2.9+ nightly + source build with `TORCH_CUDA_ARCH_LIST="12.0"`, `VLLM_FLASH_ATTN_VERSION=2`
2. **llama.cpp**: Works well on 5090, Unsloth pre-compiles binaries
3. **Speculative decoding**: Supported in Unsloth Studio for non-vision models
4. **Environment variable**: Set `CUDA_LAUNCH_BLOCKING=0` for async kernel launches
5. **Install via**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128`

---

## 7. Actionable Recommendations for Jemma

### 7.1 Immediate Changes (Before Next Training Run)

1. **Enable `use_rslora=True`** in overnight trainer — free accuracy improvement
2. **Set `lora_dropout=0`** — Unsloth optimizes for 0, research shows unreliable for short runs
3. **Enable `train_on_responses_only`** — Mask user inputs in SFT data (+1% accuracy)
4. **Update Unsloth** to v0.1.36-beta — critical Gemma 4 bug fixes
5. **Re-download GGUFs** — April 11 re-upload fixes tokenizer/chat template issues

### 7.2 Training Configuration Update

```python
# Updated Jemma overnight trainer config
QLORA_CONFIG = {
    "r": 32,
    "lora_alpha": 32,           # Changed: alpha = r (conservative) 
    "target_modules": "all-linear",  # Simplified with Unsloth
    "lora_dropout": 0,          # Changed: Unsloth optimized
    "use_rslora": True,         # NEW: rank-stabilized LoRA
}

TRAIN_CONFIG = {
    "max_seq_length": 4096,
    "per_device_train_batch_size": 1,   # Changed: minimize VRAM
    "gradient_accumulation_steps": 8,    # Changed: effective BS=8
    "num_train_epochs": 1,
    "learning_rate": 2e-4,
    "bf16": True,
    "max_steps": 200,
    "optim": "adamw_8bit",               # NEW: explicit 8-bit Adam
    "weight_decay": 0.001,               # NEW: regularization
    "lr_scheduler_type": "linear",       # NEW: for text SFT
    "warmup_steps": 5,                   # NEW: standard warmup
    "use_gradient_checkpointing": "unsloth",  # NEW: 30% VRAM savings
}
```

### 7.3 Benchmark Strategy for Hackathon Submission

1. **Run lm-eval-harness** on base E4B vs fine-tuned E4B for: `mmlu`, `gsm8k`, `hellaswag`, `arc_challenge`, `truthfulqa_mc2`, `ifeval`
2. **Run safety benchmarks**: HarmBench + SafetyBench subset (for Safety & Trust track)
3. **Run domain benchmarks**: Your 14-category civic suite (already built)
4. **Publish results**: Table format comparing base vs fine-tuned, include latency
5. **Create Gemma 4 leaderboard**: No one has done this yet — differentiator

### 7.4 Hackathon Differentiators

- **SafeRBench integration**: First to evaluate Gemma 4 safety across reasoning chains
- **Tri-model stack**: E4B + SAM 3.1 + RAG is unique architecture
- **Civic AI angle**: Real government data, real safety applications
- **Published weights**: Already on HuggingFace as `soumitty/jemma-safebrain-gemma-4-e4b-it`

---

## 8. Open Questions and Uncertainty

| Question | Current Evidence | Confidence |
|----------|-----------------|------------|
| Are new Gemma 4 variants coming before May 18? | No announcements found | Medium — Google may iterate |
| Is rsLoRA strictly better for E4B? | Paper + community says yes, no contradicting evidence | High |
| FA3/FA4 on consumer Blackwell? | Not supported, not planned | High |
| Will Unsloth add DoRA? | Not mentioned in changelog | Low — probably unnecessary |
| Optimal epoch count for civic SFT? | 1-3 per Unsloth, need empirical test | Medium |
| QLoRA vs LoRA quality gap for E4B? | Unsloth says "miniscule" | High |

---

## References

### Documentation & Guides
- Unsloth Gemma 4 Training Guide: https://unsloth.ai/docs/models/gemma-4/train
- Unsloth LoRA Hyperparameters Guide: https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide
- Unsloth Changelog: https://unsloth.ai/docs/new/changelog
- Google Gemma 4 Blog: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
- HuggingFace Gemma 4 Blog: https://huggingface.co/blog/gemma4
- Google Gemma 4 Model Card: https://ai.google.dev/gemma/docs/model-card-4

### Papers
- rsLoRA: arXiv:2312.03732 — Rank-Stabilized LoRA
- GaLore: arXiv:2403.03507 — Gradient Low-Rank Projection
- QLoRA: arXiv:2305.14314 — Efficient Finetuning of Quantized LLMs
- SafeRBench: arXiv (2026) — Safety Assessment for Large Reasoning Models
- HarmBench: mazeika2024harmbench
- SafetyBench: zhang2024safetybench
- TrustLLM: sun2024trustllm

### GitHub Issues (Relevant to Jemma)
- transformers #45242: `use_cache=False` corruption for Gemma 4
- flash-attention #1825: FA3 doesn't support 5090
- flash-attention #2168: Blackwell CUDA errors with FA2
- flash-attention #2376: FA4 SM version support question
- llama.cpp PRs: #21566, #21513, #21488, #21500, #21418, #21390, #21406

### Community Sources
- r/unsloth: Gemma 4 E4B training reports
- r/LocalLLaMA: Gemma 4 release discussion, Ollama benchmarks
- Hacker News: RTX 5090 FA discussion, "Writing Speed-of-Light Flash Attention for 5090 in CUDA C++"
- Medium (AlgoInsights): "I Fine-Tuned Gemma 4 Locally" — practical walkthrough
