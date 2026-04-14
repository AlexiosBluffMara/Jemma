# Can We Build a Gemma 4 Embeddings Model? — Research Analysis

> **Author**: Jemma Research Team  
> **Date**: April 13, 2026  
> **Status**: Theoretical feasibility analysis  
> **Confidence calibration**: Each section tagged with 🟢 (high confidence / cited), 🟡 (moderate / interpolated), 🔴 (speculative)

---

## Executive Summary

**Yes, it is theoretically feasible** to build a Gemma 4-based embedding model that improves over EmbeddingGemma (Gemma 3-based, 308M). However, the realistic scope for a hackathon differs sharply from what Google achieved with EmbeddingGemma. The most promising hackathon angle is **not** replicating the EmbeddingGemma recipe (which required encoder-decoder pretraining, billions of training pairs, Bayesian mixture optimization, and model souping), but rather applying **decoder-to-embedder conversion techniques** (LLM2Vec / E5-style) to Gemma 4 E2B, potentially with a **multimodal embedding** differentiator that no open-source Gemma embedding model currently offers.

---

## 1. Previous Gemma Embeddings: EmbeddingGemma (Sep 2025) 🟢

### Architecture
EmbeddingGemma is a **308M parameter encoder-only transformer** derived from the Gemma 3 300M decoder-only model via a multi-stage process:

1. **Encoder-Decoder Initialization** (T5Gemma recipe): The decoder-only Gemma 3 checkpoint is restructured into an encoder-decoder model and further pretrained with UL2 (mixture of denoising objectives) on Gemma 3 pretraining data.
2. **Encoder Extraction**: The encoder half is extracted as the embedding backbone — now with **bidirectional attention** rather than causal.
3. **Projection**: Mean pooling over token embeddings → linear upscale to 3072d → linear projection to 768d output.
4. **Pre-finetuning**: Large-scale unsupervised contrastive training on billions of (query, target) pairs spanning QA, sentence similarity, code retrieval, web search, 100+ languages.
5. **Finetuning**: Higher-quality task-specific data (Gecko + Gemini Embedding datasets). Three mixture groups optimized via Bayesian optimization (task diversity, language diversity, coding).
6. **Model Souping**: Unweighted parameter averaging of checkpoints from different Bayesian-optimized mixture runs.
7. **Matryoshka Representation Learning**: Flexible output dimensions from 768 → 128.
8. **Quantization-Aware Training**: int4/int8/mixed-precision variants with minimal quality loss.

### Key Design Decisions
- **Encoder-decoder init >> decoder-only init**: Their ablation showed encoder-decoder initialization outperformed decoder-only initialization across all task types. This is a critical finding — simply taking the decoder weights and switching to bidirectional attention is inferior to the T5Gemma-style conversion.
- **Mean pooling >> other pooling**: Selected after ablation.
- **Geometric Embedding Distillation + Spread-Out Regularizer**: Novel training objectives to improve robustness and expressiveness.

### Benchmarks (bf16)

| Benchmark | Mean(Task) | Mean(Type) |
|---|---|---|
| MTEB (Multilingual, v2) | 61.15 | 54.31 |
| MTEB (English, v2) | 69.67 | 65.11 |
| MTEB (Code) | 68.76 | — |

**Key claim**: SOTA for models <500M parameters. Comparable to models 2× its size.

### Reference
Vera et al., "EmbeddingGemma: Powerful and Lightweight Text Representations," arXiv:2509.20354, Sep 2025.

---

## 2. Gemma 4 Architectural Advantages for Embeddings 🟡

Gemma 4 introduces several architectural changes over Gemma 3 that have *potential* (but unproven) benefits for embedding quality:

### 2.1 Per-Layer Embeddings (PLE)
- **What**: Each decoder layer has its own small embedding lookup table per token, rather than sharing one embedding matrix.
- **Implication for embeddings**: PLE means the model maintains richer per-layer token representations. When extracting embeddings from hidden states, this could provide more nuanced features at each layer depth. However, PLE primarily inflates total parameter count without increasing effective compute — E2B has 5.1B total params but only 2.3B effective.
- **Uncertainty**: 🟡 No published evidence that PLE specifically helps embedding quality. The benefit is plausible but unverified.

### 2.2 Hybrid Attention (Sliding Window + Global)
- **What**: Alternating layers of local (sliding window = 512 for E2B/E4B) and global attention, with the final layer always global.
- **Implication for embeddings**: The final global-attention layer ensures the last hidden states capture full-sequence context, which is exactly what last-token pooling or mean pooling needs. The sliding window layers provide efficient local feature extraction. This is architecturally *well-suited* for embedding extraction.
- **Confidence**: 🟢 This is a genuine advantage. Models with pure causal attention struggle more with embedding extraction.

### 2.3 131K–256K Context Window
- **Implication**: Enables long-document embedding without chunking. EmbeddingGemma only supports 2K tokens. Even E5-mistral caps at ~32K. A Gemma 4-based embedder could handle 131K-token inputs natively.
- **Practical value**: High for document-level retrieval, legal/medical/scientific papers.
- **Confidence**: 🟢 The context window is a clear differentiator, though whether it translates to quality gains on standard MTEB (which uses short passages) is 🟡.

### 2.4 Multimodal Encoders (Vision ~150M, Audio ~300M on E2B/E4B)
- **Implication**: A Gemma 4 E2B/E4B-based embedding model could natively embed text, images, and audio in the same vector space. **This is the single biggest architectural differentiator.**
- **Current landscape**: EmbeddingGemma is text-only. Qwen3-VL-Embedding (2B/8B) handles text+image. Gemini Embedding 2 handles text+image+audio+video but is API-only. **No open-source model embeds text+image+audio.**
- **Confidence**: 🟢 architectural capability exists; 🟡 whether fine-tuning produces competitive cross-modal embeddings is uncertain.

### 2.5 262K Vocabulary
- **Implication**: Broader tokenizer coverage, especially for multilingual and code. More tokens = more precise semantic boundaries, which can improve embedding quality for tail languages and programming languages.
- **Confidence**: 🟡 Marginal benefit, but positive direction.

### 2.6 MoE (26B-A4B only)
- **Implication**: 3.8B active params with 128 experts could theoretically provide diverse, specialized representations. But MoE models are harder to convert to embedding models — the routing mechanism adds complexity, and it's unclear if sparse expert representations are as useful for dense embeddings.
- **Confidence**: 🔴 Speculative. No published work on MoE-to-embedder conversion at this scale.

---

## 3. Decoder-to-Embedder Conversion Techniques 🟢

The field has converged on several established methods:

### 3.1 Last-Token (EOS) Pooling with Causal Attention
**Used by**: E5-mistral-7b-instruct (Wang et al., 2024)

- Append `[EOS]` token; extract its final-layer hidden state as the embedding
- Under causal attention, `[EOS]` attends to all prior tokens → acts like `[CLS]` in encoders
- Fine-tune with contrastive loss (InfoNCE) + in-batch negatives
- **Pros**: Simplest approach, preserves causal architecture, works with LoRA
- **Cons**: Causal attention limits token interactions (later tokens can't inform earlier ones)

**E5-mistral recipe**: Mistral-7B → LoRA fine-tuning on synthetic contrastive data (generated by GPT-4) with task-specific instructions → achieves strong MTEB results with minimal LoRA params.

### 3.2 Bidirectional Attention Conversion (LLM2Vec)
**Used by**: LLM2Vec (BehnamGhader et al., 2024)

Three steps:
1. **Enable bidirectional attention**: Remove causal mask
2. **Masked Next-Token Prediction (MNTP)**: Retrain briefly with combined next-token prediction + masking
3. **SimCSE unsupervised contrastive learning**: Self-supervised contrastive fine-tuning via dropout augmentation

- **Pros**: Enables full bidirectional context; unsupervised (no labeled data needed)
- **Cons**: Requires architectural modification; training is more complex than E5-style

### 3.3 Latent Attention Pooling (NV-Embed)
**Used by**: NV-Embed-v2 (Lee et al., 2024, NVIDIA)

- Bidirectional attention + novel latent attention layer over final hidden states + mean pooling
- Instruction-tuned with task-specific prefixes
- Held #1 on MTEB for extended period
- **Pros**: Highest quality among decoder-based approaches
- **Cons**: Complex architecture; large model (7B)

### 3.4 Unified Embedding + Generation (GRITLM)
**Used by**: GRITLM-7b (Muennighoff et al., 2024)

- Single model handles both embedding (bidirectional) and generation (causal) via different attention masks
- **Pros**: One model for both tasks; reduces infrastructure
- **Cons**: Training complexity; may compromise embedding quality vs. specialized model

### 3.5 Instruction-Tuned Embedding
**Used by**: E5-mistral, GTE-Qwen2, NV-Embed, Qwen3-Embedding

- Prefix instructions like "Represent this sentence for retrieval:" or "query:" / "passage:"
- Dramatically improves task-specific performance
- **Confidence**: 🟢 This is now standard practice.

### 3.6 Matryoshka Representation Learning (MRL)
**Paper**: Kusupati et al., NeurIPS 2022

- Train with loss computed at multiple truncated dimensions (768, 512, 256, 128, 64)
- Model front-loads important information in early dimensions
- Enables flexible dimension reduction at inference time
- **Supported in**: sentence-transformers via `MatryoshkaLoss`
- **Practical**: 🟢 Easy to add to any training pipeline; no architecture changes needed.

---

## 4. Multimodal Embeddings Angle — The Differentiator 🟡

### 4.1 Current Landscape

| Model | Text | Image | Audio | Video | Open-Source | MTEB Eng |
|---|:---:|:---:|:---:|:---:|:---:|---|
| EmbeddingGemma (308M) | ✅ | ❌ | ❌ | ❌ | ✅ | 69.67 |
| Qwen3-VL-Embedding-8B | ✅ | ✅ | ❌ | ❌ | ✅ | ~70+ |
| Qwen3-Embedding-8B | ✅ | ❌ | ❌ | ❌ | ✅ | ~70+ |
| Gemini Embedding 2 | ✅ | ✅ | ✅ | ✅ | ❌ (API) | ~68 |
| Cohere embed-v4 | ✅ | ✅ | ❌ | ❌ | ❌ (API) | ~65 |
| CLIP / SigLIP | ✅ | ✅ | ❌ | ❌ | ✅ | N/A* |

*CLIP-family models aren't designed for general text embedding tasks.

### 4.2 The Opportunity
**No open-source model currently embeds text + image + audio in a unified vector space.**

Gemma 4 E2B/E4B has native text, image, and audio encoders already aligned in the same latent space (they all feed into the shared decoder). A Gemma 4-based embedding model could:

1. Extract unified representations from the decoder's hidden states after processing any combination of modalities
2. Enable cross-modal retrieval: "find images matching this audio clip" or "find audio matching this text"
3. Differentiate from every existing open-source embedding model

### 4.3 Technical Approach for Multimodal Embeddings
1. Feed multimodal input (text, image, audio) through E2B/E4B
2. Extract hidden states from the final global-attention layer
3. Apply mean pooling (or learned attention pooling) over all tokens (including vision/audio tokens)
4. Project to fixed embedding dimension
5. Train with multimodal contrastive loss:
   - Text-to-text pairs (standard NLI/retrieval data)
   - Text-to-image pairs (e.g., CC3M, LAION subset)
   - Text-to-audio pairs (e.g., AudioCaps, Clotho)
   - Cross-modal hard negatives

### 4.4 Risk Assessment
- 🟡 **Alignment quality**: The vision/audio encoders are pretrained for *generation* tasks (captioning, ASR), not for *retrieval*. Fine-tuning may be needed to align modality representations for similarity search.
- 🟡 **Embedding dimension vs. information**: Multimodal tokens are numerous (image: up to 1024 tokens, audio: ~25 tok/sec × 30s = 750 tokens). Pooling these into a single 768d vector may lose too much modal-specific information.
- 🟢 **Data availability**: MS MARCO (text), CC3M/COCO (image-text), AudioCaps (audio-text) are all available.

---

## 5. Practical Feasibility Assessment 🟢/🟡

### 5.1 Approach A: EmbeddingGemma-Style (Full Recipe)
**Verdict: ❌ Not feasible for hackathon**

Requirements:
- Encoder-decoder pretraining with UL2 on full pretraining corpus → weeks of compute on TPU pods
- Billions of (query, target) pairs with Bayesian mixture optimization
- Model souping across multiple training runs
- Google's proprietary Gecko + Gemini Embedding training data

This is Google-scale engineering. Not reproducible in a hackathon.

### 5.2 Approach B: E5-Style LoRA Fine-Tuning on Gemma 4 E2B
**Verdict: ✅ Feasible — this is the recommended hackathon path**

Recipe:
1. **Base model**: Gemma 4 E2B (2.3B effective params, ~9.6 GB bf16 / 3.2 GB QLoRA)
2. **Pooling**: Last-token (EOS) pooling with causal attention — simplest, no arch changes
3. **LoRA/QLoRA**: r=16–64, target attention layers, ~10–50M trainable params
4. **Training data**:
   - MS MARCO passage retrieval (~500K pairs) — freely available
   - AllNLI (SNLI + MultiNLI, ~940K pairs) — freely available
   - Synthetic contrastive pairs from Gemma 4 itself (self-distillation)
   - Optional: MIRACL (multilingual retrieval), CodeSearchNet (code)
5. **Loss**: MultipleNegativesRankingLoss (InfoNCE) + MatryoshkaLoss wrapper
6. **Training time**: ~4-8 hours on single RTX 5090 with QLoRA
7. **Evaluation**: MTEB English v2 subset (retrieval, STS, classification)

**Expected MTEB range**: 🟡 55–65 on English v2 (competitive with models in the 1–3B class, likely below EmbeddingGemma's 69.67 which had massive training data advantage).

### 5.3 Approach C: LLM2Vec Conversion
**Verdict: ⚠️ Feasible but risky**

- Requires modifying Gemma 4's attention mask to bidirectional
- Need to retrain with MNTP — ~1–2 hours
- Then SimCSE fine-tuning — ~1 hour
- Then task-specific contrastive fine-tuning — ~4 hours
- **Risk**: Gemma 4's hybrid attention (sliding window + global) may not behave well when converted to fully bidirectional. The PLE mechanism was trained with causal attention assumptions.

### 5.4 Approach D: Multimodal Embedding (The Hackathon Differentiator)
**Verdict: ✅ Feasible as a demo, ⚠️ for competitive benchmarks**

Recipe:
1. **Base model**: Gemma 4 E2B (has all three encoders)
2. **Extract hidden states** from last decoder layer after processing multimodal input
3. **Mean pool** over all tokens → project to 768d
4. **Contrastive fine-tuning**:
   - COCO Captions (118K image-text pairs)
   - AudioCaps (~50K audio-text pairs)
   - MS MARCO subset (text-text pairs)
5. **Training time**: ~6-12 hours on RTX 5090 with QLoRA
6. **Evaluation**: Custom cross-modal retrieval benchmarks + MMEB-V2 subset

### 5.5 Compute Budget Summary

| Approach | VRAM | Training Time | Data Volume | Hackathon Feasible? |
|---|---|---|---|---|
| A: Full EmbeddingGemma | 100+ GB TPU | Weeks | Billions pairs | ❌ |
| B: E5-style LoRA | 5 GB (QLoRA) | 4-8 hrs | ~1.5M pairs | ✅ |
| C: LLM2Vec conversion | 10 GB | 6-8 hrs | ~1.5M pairs | ⚠️ |
| D: Multimodal embedding | 5-10 GB | 6-12 hrs | ~300K pairs | ✅ (demo-quality) |
| **B+D combined** | **10 GB** | **12-20 hrs** | **~1.8M pairs** | **✅ Recommended** |

---

## 6. Competitive Analysis: Would It Actually Be an Improvement? 🟡

### 6.1 Comparison Table (MTEB English v2, approximate)

| Model | Params | MTEB Eng v2 | Multimodal | Open-Source | Context |
|---|---|---|---|---|---|
| **Gemini Embedding 001** | Unknown | **68.32** | Text+Img+Audio+Video | ❌ API | 8K |
| **Qwen3-Embedding-8B** | 8B | ~70+ | Text only | ✅ | 32K |
| **Microsoft Harrier-27B** | 27B | ~74.3 (v2) | Text only | ✅ MIT | — |
| **NV-Embed-v2** | 7B | ~69-72 | Text only | ✅ | 32K |
| **EmbeddingGemma** | 308M | **69.67** | Text only | ✅ | 2K |
| **E5-mistral-7b** | 7B | ~66-68 | Text only | ✅ | 32K |
| **Cohere embed-v4** | Unknown | ~65.2 | Text+Image | ❌ API | 128K |
| **BGE-M3** | 568M | ~63 | Text only | ✅ MIT | 8K |
| text-embedding-3-large | Unknown | ~65.96 | Text only | ❌ API | 8K |
| **Hypothetical Jemma-Embed-E2B** | 2.3B | **~58-65** 🟡 | **Text+Img+Audio** | ✅ | **131K** |

### 6.2 Honest Assessment

**Would we beat EmbeddingGemma on pure text MTEB?** 

Almost certainly **no** with a hackathon effort. EmbeddingGemma benefits from:
- Encoder-decoder pretraining (proven superior to decoder-only init in their ablations)
- Billions of training pairs including Google's proprietary data
- Bayesian-optimized mixture rates + model souping
- Geometric embedding distillation from larger teacher models

A LoRA-finetuned decoder-only E2B with ~1.5M public training pairs would be at a fundamental data and training recipe disadvantage, despite having 7.5× more parameters.

**Where we COULD win:**

1. **Multimodal**: No open-source Gemma embedding handles images or audio. This is a **genuine first** — the first open-source Gemma-family multimodal embedder.
2. **Long context**: 131K tokens vs. EmbeddingGemma's 2K. For document-level retrieval tasks, this is a massive advantage.
3. **Retrieval-specific tasks**: On narrow retrieval benchmarks (especially domain-specific like civic/safety data), a fine-tuned 2.3B model can outperform a 308M general model.
4. **Hackathon story**: "First multimodal Gemma embedding model" + "131K context embedding" is a compelling narrative.

### 6.3 Theoretical Ceiling

If one had unlimited compute and data, a Gemma 4-based embedding model *should* be able to exceed EmbeddingGemma because:

- 🟢 Gemma 4 has more pretraining data and improved pretraining than Gemma 3
- 🟢 Larger model capacity (2.3B effective vs. 308M) captures more semantic nuance
- 🟢 Multimodal pretraining provides richer cross-domain representations
- 🟡 PLE and hybrid attention are architecturally more expressive

The **theoretical ceiling** of a well-trained Gemma 4 E2B embedder is likely **MTEB Eng v2 ~68-72** (based on the empirical observation that 2-3B parameter models with good training achieve this range — see Qwen3-Embedding-0.6B already hitting competitive scores). With the 4B E4B variant and full training, ~70-73 is plausible.

---

## 7. Hackathon Strategy: Minimum Viable Approach 🟢

### Recommended Plan: "Jemma-Embed" — First Multimodal Gemma Embedder

**Phase 1 (Day 1-2): Text Embedding Baseline**
1. Load Gemma 4 E2B from Unsloth checkpoint
2. Add EOS-pooling + linear projection head (768d output)
3. QLoRA fine-tune on MS MARCO + AllNLI with MatryoshkaLoss
4. Evaluate on MTEB English retrieval subset
5. Target: competitive with BGE-M3 (~63)

**Phase 2 (Day 3-4): Multimodal Extension**
1. Extend to accept image inputs through E2B's vision encoder
2. Fine-tune on COCO Captions with cross-modal contrastive loss
3. Extend to accept audio inputs through E2B's audio encoder
4. Fine-tune on AudioCaps
5. Demo: cross-modal retrieval (text→image, text→audio, audio→text)

**Phase 3 (Day 5): Polish and Publish**
1. Matryoshka dimension support (768/512/256/128)
2. Benchmark on available MTEB tasks + custom multimodal retrieval eval
3. Publish to HuggingFace: `soumitty/jemma-embed-gemma-4-e2b`
4. Write model card with benchmarks, architecture diagram, demo notebook

### Key Deliverables for Hackathon Judges
1. **Technical novelty**: First open-source multimodal Gemma embedding model (text+image+audio)
2. **Safety angle**: Multimodal embeddings enable content safety classification across modalities
3. **Civic application**: Embed civic documents, images, audio recordings in unified search index
4. **Efficiency**: Runs on consumer GPU (5 GB with QLoRA)
5. **131K context**: Embed full documents without chunking

### Required Training Data (All Freely Available)

| Dataset | Size | Modality | Use |
|---|---|---|---|
| MS MARCO Passage | 500K+ pairs | Text-Text | Retrieval |
| AllNLI (SNLI + MultiNLI) | 940K pairs | Text-Text | Similarity |
| COCO Captions | 118K images, 5 caps each | Image-Text | Cross-modal |
| AudioCaps | ~50K clips | Audio-Text | Cross-modal |
| CodeSearchNet | 2M+ pairs | Code-Text | Code retrieval |

### Implementation Skeleton

```python
import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM
from sentence_transformers import SentenceTransformer
from peft import LoraConfig, get_peft_model

# Load Gemma 4 E2B
model = AutoModelForMultimodalLM.from_pretrained(
    "unsloth/gemma-4-E2B-it", dtype=torch.bfloat16, device_map="auto"
)
processor = AutoProcessor.from_pretrained("unsloth/gemma-4-E2B-it")

# Add LoRA
lora_config = LoraConfig(
    r=32, lora_alpha=64, target_modules=["q_proj", "v_proj", "k_proj"],
    task_type="FEATURE_EXTRACTION"
)
model = get_peft_model(model, lora_config)

# Embedding extraction (conceptual)
def get_embedding(model, inputs, dim=768):
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
        last_hidden = outputs.hidden_states[-1]  # Final layer
        # Mean pool over non-padding tokens
        attention_mask = inputs["attention_mask"].unsqueeze(-1)
        pooled = (last_hidden * attention_mask).sum(1) / attention_mask.sum(1)
        # Project + normalize
        embedding = pooled[:, :dim]  # Matryoshka truncation
        return torch.nn.functional.normalize(embedding, p=2, dim=-1)
```

---

## 8. Key Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Text MTEB score below EmbeddingGemma | High | Medium | Frame as "multimodal" rather than "text-only competitor" |
| Multimodal alignment poor | Medium | High | Use instruction tuning + more contrastive pairs |
| Training instability with QLoRA | Low | Medium | Use conservative LR (2e-5), gradient checkpointing |
| VRAM exceeds single GPU | Low | Medium | E2B at int4 fits in 3.2 GB; even with training overhead, fits RTX 5090 |
| Hackathon judges don't value embeddings | Medium | High | Integrate into Jemma's RAG pipeline as live demo |

---

## 9. Key Paper References

1. **EmbeddingGemma**: Vera et al., "EmbeddingGemma: Powerful and Lightweight Text Representations," arXiv:2509.20354, Sep 2025.
2. **E5-Mistral**: Wang et al., "Improving Text Embeddings with Large Language Models," arXiv:2401.00368, Jan 2024.
3. **LLM2Vec**: BehnamGhader et al., "LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders," arXiv:2404.05961, Apr 2024.
4. **NV-Embed**: Lee et al., "NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models," arXiv:2405.17428, May 2024.
5. **GRITLM**: Muennighoff et al., "Generative Representational Instruction Tuning," arXiv:2402.09906, Feb 2024.
6. **Matryoshka RL**: Kusupati et al., "Matryoshka Representation Learning," NeurIPS 2022, arXiv:2205.13147.
7. **T5Gemma**: Zhang et al., 2025 (referenced in EmbeddingGemma paper — encoder-decoder init from decoder-only).
8. **Gecko**: Lee et al., "Gecko: Versatile Text Embeddings Distilled from Large Language Models," arXiv:2403.20327, Mar 2024.
9. **Qwen3-Embedding**: Qwen Team, "Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models," 2025.
10. **Qwen3-VL-Embedding**: Qwen Team, "Qwen3-VL-Embedding and Qwen3-VL-Reranker," arXiv:2601.04720, Jan 2026.

---

## 10. Bottom Line

| Question | Answer |
|---|---|
| Can we build it? | **Yes** — decoder-to-embedder techniques are well-established |
| Would it beat EmbeddingGemma on text MTEB? | **Unlikely** with hackathon resources (data/compute gap) |
| Would it be novel? | **Yes** — first open-source multimodal Gemma embedder |
| Is it feasible in hackathon timeline? | **Yes** — E5-style QLoRA fine-tuning takes ~8-20 hours |
| Best differentiator? | **Multimodal (text+image+audio)** + **131K context** |
| Recommended base model? | **Gemma 4 E2B** (smallest, has all encoders) |
| Recommended approach? | **E5-style EOS pooling + QLoRA + MatryoshkaLoss** |
| Estimated MTEB Eng v2? | **~58-65** (honest range) |
| Hackathon narrative? | "First open-source trimodal Gemma embedding model" |
