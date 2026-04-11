# Jemma Runtime: RTX 5090 Inference Deep Dive

## Technical Research Report — Ollama/llama.cpp Stack Analysis & Optimization for Gemma 4

**Author**: Jemma Research  
**Date**: April 2026  
**Confidence Level**: High on architecture/theory, Medium on specific benchmark numbers (hardware-dependent)

---

## Table of Contents
1. [llama.cpp Inference Deep Dive](#1-llamacpp-inference-deep-dive)
2. [Memory Bandwidth Analysis](#2-memory-bandwidth-analysis)
3. [Custom Inference Alternatives](#3-custom-inference-alternatives)
4. [GGUF Format Analysis](#4-gguf-format-analysis)
5. [Speculative Decoding](#5-speculative-decoding)
6. [Practical Recommendation](#6-practical-hackathon-recommendation)

---

## 1. llama.cpp Inference Deep Dive

### 1.1 Architecture Overview

Ollama is a Go wrapper (63.8% Go, 29.5% C) around llama.cpp. The relationship is:

```
User Request → Ollama (Go HTTP server)
    → cgo FFI boundary
    → llama.cpp C library (libllama.a, statically linked)
    → GGML tensor library
    → CUDA backend (ggml-cuda/)
    → GPU kernels
```

Ollama adds: model management, Modelfile abstraction, HTTP API, template rendering, model pulling, and multi-model scheduling. **It adds NO inference logic** — every computation is delegated to llama.cpp.

### 1.2 Single Token Generation: CUDA Kernel Execution Flow

For autoregressive decode (batch size 1), a single token generation in llama.cpp follows this path:

```
1. GGML Graph Construction (CPU)
   ├─ Build computation graph for one forward pass
   ├─ Nodes: embedding lookup, RMSNorm, attention, FFN, final logits
   └─ Graph is a DAG of tensor operations

2. CUDA Graph Dispatch (GPU)
   ├─ Since 2024: CUDA Graphs enabled by default for BS=1
   ├─ First pass: capture stream → instantiate graph
   ├─ Subsequent passes: update KV cache params → replay graph
   └─ Eliminates per-kernel launch overhead (~20% speedup on fast GPUs)

3. Per-Layer Execution (repeated for each transformer layer):
   │
   ├─ RMSNorm Kernel
   │   └─ Fused normalization, ~O(d_model) bandwidth
   │
   ├─ QKV Projection (THE BOTTLENECK)
   │   ├─ Quantized matmul: dequantize weights → FP16 → tensor core GEMV
   │   ├─ Uses MMQ kernels (ggml-cuda/mmq.cuh) for quantized types
   │   ├─ OR cuBLAS GEMM for FP16/FP32 (selected at compile time)
   │   └─ For Q4_K_M: loads 4-bit blocks, dequant to FP16, multiply
   │
   ├─ Attention Computation
   │   ├─ Without Flash Attention: standard softmax(QK^T/√d)V
   │   ├─ With Flash Attention (--flash-attn): fused FA2 kernel
   │   ├─ KV Cache read from VRAM (grows with context length)
   │   └─ Sliding window: only attend to last W tokens in cache
   │
   ├─ Output Projection (quantized GEMV)
   │
   ├─ RMSNorm Kernel
   │
   └─ FFN / MoE Block
       ├─ Dense models: Gate+Up projection → SiLU → Down projection
       └─ MoE models: Router → TopK selection → Sparse expert dispatch
   
4. Final RMSNorm → Logits Projection (GEMV against vocab embedding)

5. Sampling (CPU)
   ├─ Transfer logits GPU→CPU
   ├─ Temperature, top-p, top-k filtering
   └─ Token selection → append to KV cache → next iteration
```

### 1.3 Quantized Matrix Multiplication (Q4_K_M, Q8_0)

llama.cpp uses two CUDA kernel families for quantized inference:

**MMQ Kernels (`ggml-cuda/mmq.cuh`)** — custom quantized matmul:
- Purpose-built for dequantize-and-multiply in a single fused kernel
- Loads quantized weight blocks from VRAM, dequantizes to FP16 in registers/shared memory, performs dot products
- Avoids the overhead of a separate dequantization pass
- Optimized for GEMV (matrix × vector) which dominates autoregressive decode

**cuBLAS Path** — for larger batch sizes:
- Dequantize weights to FP16 first, then call cuBLAS GEMM
- Better for prompt processing (prefill) where batch size > 1
- Uses Tensor Cores for FP16 GEMM

**Q4_K_M block structure** (K-quant, Mixed):
- Super-block: 256 weights
- Sub-blocks: 8 groups of 32 weights each
- Each sub-block has its own 6-bit scale and 4-bit minimum
- Super-block has FP16 master scale and master minimum
- Each weight stored as 4 bits
- Effective bits per weight: ~4.58
- **Critical**: attention layers and output layers use higher precision (Q6_K) automatically — this is the "M" (mixed) in Q4_K_M

**Q8_0 block structure**:
- Block: 32 weights, each stored as 8 bits (signed int8)
- One FP16 scale factor per block
- Effective bits per weight: ~8.5
- Simple dequantize: `w_fp16 = scale * int8_value`
- Faster dequantization but 2x the bandwidth of Q4_K_M

### 1.4 KV Cache Management with Sliding Window Attention

llama.cpp's KV cache for Gemma 4:

```
Standard full attention (no sliding window):
  KV cache size = 2 × n_layers × n_kv_heads × d_head × context_length × sizeof(dtype)

Gemma 4 E4B (512 sliding window):
  KV cache capped at 512 tokens per layer
  Size = 2 × L × n_kv × d × 512 × 2 bytes (FP16)
  Much smaller than full context KV cache

Gemma 4 26B MoE (1024 sliding window):
  KV cache capped at 1024 tokens per layer

Gemma 4 31B Dense (1024 sliding window):  
  KV cache capped at 1024 tokens per layer
```

**Implementation**: llama.cpp uses a ring buffer for sliding window — once the window is full, new KV entries overwrite the oldest. The position embedding is absolute (RoPE), but attention masking restricts to the window. This was merged relatively recently and provides ~75% VRAM reduction for long contexts vs. full-context cache.

**UNCERTAINTY**: Whether Ollama v0.20.5 fully exposes sliding window optimization as a tunable or whether it falls back to full attention in some configurations. The PR (#15214) adding Gemma 4 support should handle this from the model's metadata, but edge cases may exist.

### 1.5 Flash Attention Integration

llama.cpp supports Flash Attention 2 via `--flash-attn` / `-fa` flag:

- **Prefill (prompt processing)**: Massive speedup. FA2 is $O(N)$ memory instead of $O(N^2)$ for the attention matrix. Critical for long prompts.
- **Decode (token generation)**: Minimal impact at batch size 1 because attention is Q(1×d) × K(N×d), which is already a GEMV. FA2's tiling doesn't help much here.
- **Ollama**: Flash attention was enabled via PR #15378. In Ollama, set `OLLAMA_FLASH_ATTENTION=1` or pass in Modelfile.

**For Gemma 4 with sliding window**: Flash Attention is most beneficial during prefill of long prompts (the initial context processing), where the sliding window still requires attending to up to 512/1024 previous tokens per position.

### 1.6 MoE Expert Routing in llama.cpp

For Gemma 4 26B (128 routed experts, 2 active + 1 shared):

```
MoE Forward Pass:
1. Router: Linear(d_model → 128) → Sigmoid → TopK(2)           [TINY: 128 outputs]
2. Selected expert indices: [e_i, e_j] per token
3. Load expert weights for e_i, e_j from VRAM                   [BANDWIDTH BOTTLENECK]
4. Execute Gate+Up+Down MLP for each selected expert
5. Weighted sum of expert outputs (using router scores)
6. Add shared expert output (always computed)
```

**Key bottleneck for single-token decode**: All 128 expert weight matrices live in VRAM (~48GB in BF16), but only 2 are used per token. This means:
- VRAM is occupied by inactive experts
- But memory *bandwidth* is only spent on 2 experts × 3 matrices × GEMV
- Compute is equivalent to ~3.8B dense model

**llama.cpp's MoE handling**:
- `--n-gpu-layers` offloads layers to GPU (including all experts per layer)
- `--n-cpu-moe` flag allows keeping MoE expert layers on CPU while dense layers stay on GPU
- For RTX 5090 with 32GB: Q4_K_M 26B MoE fits entirely in VRAM (~16GB weights + KV cache)
- All expert weights loaded to GPU; routing selects indices; only selected experts participate in GEMV

**UNCERTAINTY**: llama.cpp does NOT appear to have a specialized "expert reduce" CUDA kernel that fuses routing + sparse dispatch + aggregation into a single kernel launch. Each expert's MLP is computed sequentially with separate kernel calls, which is suboptimal. There was a PR for a CUDA expert reduce kernel that caused regressions on ROCm, suggesting this is still unstable.

---

## 2. Memory Bandwidth Analysis

### 2.1 The Roofline Model for LLM Inference

Autoregressive LLM decode is **memory-bandwidth bound**, not compute-bound. The arithmetic intensity is:

$$\text{AI} = \frac{\text{FLOPs per token}}{\text{Bytes loaded per token}} \approx 1 \text{ FLOP/byte (at BS=1)}$$

The RTX 5090's compute/bandwidth ratio:

$$\text{Ridge point} = \frac{100 \text{ TFLOPS FP16}}{1.792 \text{ TB/s}} \approx 56 \text{ FLOP/byte}$$

At AI ≈ 1, we are **~56× below the ridge point**. The GPU's compute units are >98% idle during autoregressive decode. **Only memory bandwidth matters.**

### 2.2 Theoretical Maximum tok/s (Bandwidth-Limited)

The fundamental equation for bandwidth-limited decode:

$$\text{tok/s}_{\max} = \frac{\text{Memory Bandwidth (bytes/s)}}{\text{Model Size (bytes)}}$$

This is because each generated token requires loading all model weights once (for the GEMV operations).

**RTX 5090**: 1,792 GB/s memory bandwidth

| Model | Quant | Weight Size | Theoretical Max tok/s | Notes |
|-------|-------|-------------|----------------------|-------|
| **E2B** (~2B params) | Q4_K_M | ~1.2 GB | **~1,493** | Tiny model, CUDA overhead dominates |
| **E2B** | Q8_0 | ~2.2 GB | **~815** | |
| **E4B** (~4B params) | Q4_K_M | ~2.5 GB | **~717** | |
| **E4B** | Q8_0 | ~4.3 GB | **~417** | |
| **26B MoE** (3.8B active) | Q4_K_M | ~16 GB total, ~2.0 GB active | **~896**† | Only active expert weights matter for BW |
| **26B MoE** | Q8_0 | ~28 GB total, ~3.5 GB active | **~512**† | |
| **26B MoE** | FP8 | ~30 GB total, ~3.8 GB active | **~471**† | |
| **31B Dense** | Q4_K_M | ~18 GB | **~100** | Barely fits 32GB with KV cache |
| **31B Dense** | Q8_0 | ~33 GB | **DNF** | Does not fit in 32GB VRAM |

†**MoE bandwidth calculation is subtle**: The theoretical max assumes you only load active expert weights per token. In practice, llama.cpp loads entire expert weight matrices via pointer indexing (the weights are *resident* in VRAM, same as dense), so the bandwidth cost is indeed ≈ active expert weights only. But the router, shared expert, attention layers, and embeddings are all dense and add to the per-token load.

**More precise MoE calculation for 26B Q4_K_M**:
- Attention layers (~30% of total params, all dense): ~4.8 GB → loaded fully each token
- MoE layers (2/128 experts active): ~11.2 GB total, ~0.18 GB active per token  
- Embeddings, norms, etc.: ~0.5 GB
- **Effective per-token load**: ~5.5 GB
- **Adjusted theoretical max**: 1,792 / 5.5 ≈ **326 tok/s**

### 2.3 Observed Performance vs. Theoretical

From community benchmarks on RTX 5090:

| Model | Quant | Observed tok/s | Theoretical Max | Efficiency |
|-------|-------|---------------|-----------------|------------|
| Gemma 4 26B MoE | Q6_K | ~190 | ~250 (est.) | ~76% |
| Gemma 3 12B Dense | Q4_K_M | ~85 | ~150 (est.) | ~57% |
| 8B class models | Various | 185–213 | ~300+ | ~60-70% |

**Efficiency gaps explained**:
- **CUDA kernel launch overhead**: ~5-10% (mitigated by CUDA Graphs)
- **CPU-side GGML graph construction**: ~5-10% (the GPU sits idle between tokens while CPU builds next graph)
- **Memory access patterns**: Quantized dequantize kernels don't achieve peak bandwidth due to non-sequential access patterns and bank conflicts in shared memory
- **KV cache reads**: Additional bandwidth for reading KV cache during attention (not counted in model-weight-only calculation)
- **CPU↔GPU synchronization**: Logits transfer, sampling, token embedding lookup
- **Ollama overhead**: cgo FFI boundary, Go HTTP server, template processing — minimal but nonzero per-token

**Key finding**: llama.cpp achieves roughly **60-76% of theoretical memory bandwidth utilization** on modern GPUs. This is actually quite good for a general-purpose engine.

---

## 3. Custom Inference Alternatives

### 3.1 Bottlenecks in llama.cpp

Ordered by impact:

1. **No FP8/NVFP4 Tensor Core support** (HIGH impact)
   - llama.cpp's quantized kernels use CUDA cores, not Tensor Cores (for quantized types)
   - Tensor Cores on Blackwell support FP8 (E4M3/E5M2) natively
   - NVFP4 (Blackwell-native 4-bit) delivers 1.6× over BF16 via Tensor Cores
   - llama.cpp's Q4_K_M dequantizes to FP16 then does dot products on CUDA cores — **misses the new hardware entirely**

2. **CPU-bound graph construction** (MEDIUM impact)
   - GGML graph is rebuilt every token on CPU
   - GPU sits idle during this phase
   - Being actively worked on (GitHub issue #7456)

3. **No continuous batching** (MEDIUM impact for multi-user)
   - llama.cpp processes one request at a time (or simple static batching)
   - No PagedAttention for memory-efficient multi-request serving
   - vLLM's continuous batching delivers 35-44× throughput at high concurrency

4. **Sequential expert execution in MoE** (LOW-MEDIUM impact)  
   - Each active expert's MLP launches separate CUDA kernels
   - Could be fused into a single batched sparse GEMM kernel

5. **No speculative decoding built-in** (MEDIUM impact)
   - Must be implemented externally or use llama.cpp's experimental `--draft` mode

### 3.2 Alternative: TensorRT-LLM with FP8/NVFP4

**Advantages**:
- Native FP8 (E4M3) Tensor Core kernels designed for Blackwell
- NVFP4 support: 4-bit weights with hardware dequantization on Tensor Cores
- Benchmarks show **1.6× throughput over BF16** with NVFP4 (2-4% quality loss)
- Optimized MoE dispatch with fused expert kernels
- In-flight batching (continuous batching)
- Paged KV cache

**Disadvantages**:
- Complex build process (TensorRT engine compilation per model)
- Linux-only for production (Windows support limited)
- Slower iteration — model changes require re-compilation
- NVIDIA-proprietary, closed-source kernel implementations
- **Gemma 4 support status**: Uncertain. TensorRT-LLM has supported Gemma 2; Gemma 4's new architecture (MoE with 128 experts, sliding window) may not have optimized kernels yet.

**Expected speedup on RTX 5090**: 1.5-2× over llama.cpp for single-stream decode via FP8 Tensor Cores. Larger gains (3-5×) for batched/concurrent inference.

### 3.3 Alternative: vLLM with PagedAttention

**Advantages**:
- PagedAttention: virtual memory-style KV cache management, near-zero waste
- Continuous batching: dynamically batch multiple requests
- At high concurrency: **35-44× throughput over llama.cpp** (cited benchmarks)
- NVFP4 support on Blackwell GPUs (vLLM 0.12+)
- Speculative decoding built-in
- Python ecosystem: easy to extend

**Disadvantages**:
- Single-user latency is **worse** than llama.cpp: benchmarks show 83 tok/s vLLM vs 185-213 tok/s llama.cpp for 8B models at concurrency=1
- Heavy dependencies (PyTorch, CUDA toolkit, etc.)
- Higher VRAM overhead from framework itself
- Windows support is poor/nonexistent

**When to choose vLLM**: If Jemma serves multiple concurrent users or needs to batch requests. For single-agent single-stream (our hackathon use case), **llama.cpp is faster**.

### 3.4 Alternative: CUTLASS/cuDNN Custom Kernels

**CUTLASS** (CUDA Templates for Linear Algebra Subroutines):
- NVIDIA's open-source template library for efficient GEMM/GEMV
- Supports FP8, INT8, INT4 on Tensor Cores
- Could write custom Gemma 4-specific MoE dispatch kernels

**cuDNN** (CUDA Deep Neural Network library):
- Fused attention backends (FlashAttention-style)
- Optimized for specific attention patterns

**Feasibility for hackathon**: **Very low**. Writing custom CUTLASS kernels requires:
- Deep understanding of GPU memory hierarchy
- Weeks of tuning for a single kernel
- Testing across edge cases
- This is what TensorRT-LLM already does internally

### 3.5 Custom MoE Routing Kernels

For Gemma 4 26B's 128-expert MoE, a custom kernel could:

```
Fused MoE Kernel:
1. Router: compute all 128 scores in one warp (tiny operation)
2. TopK: parallel reduction to find top-2 experts
3. Permute: gather tokens for same expert into contiguous memory
4. Batched sparse GEMM: compute selected expert MLPs
5. Reduce: weighted sum back to original token order
```

**Existing implementations**:
- Megablocks (Stanford): sparse MoE with block-sparse matrix operations
- vLLM's Marlin MoE kernels: fused expert dispatch for quantized models
- NVIDIA's MoE kernels in TensorRT-LLM

**Speedup potential**: 1.3-1.5× on MoE layers specifically. Since MoE layers are ~70% of Gemma 4 26B, this translates to ~1.2-1.3× overall.

**Hackathon feasibility**: Zero. Use an existing engine that has fused MoE kernels (vLLM or TensorRT-LLM).

---

## 4. GGUF Format Analysis

### 4.1 GGUF File Structure

GGUF (GGML Universal Format) is a binary container:

```
┌──────────────────────────────────────┐
│ Magic: "GGUF" (4 bytes)             │
│ Version: 3 (uint32)                  │
│ Tensor Count (uint64)                │
│ Metadata KV Count (uint64)           │
├──────────────────────────────────────┤
│ Metadata Key-Value Pairs             │
│  ├─ "general.architecture": "gemma4" │
│  ├─ "general.name": "..."           │
│  ├─ "gemma4.context_length": 131072  │
│  ├─ "gemma4.embedding_length": ...   │
│  ├─ "gemma4.block_count": ...        │
│  ├─ "tokenizer.ggml.model": "..."    │
│  └─ ... (all model hyperparameters)  │
├──────────────────────────────────────┤
│ Tensor Info Array                    │
│  ├─ Tensor name (string)             │
│  ├─ Dimensions (uint32[])            │
│  ├─ Data type (enum: Q4_K_M, etc.)   │
│  └─ Offset into data section         │
├──────────────────────────────────────┤
│ [Alignment Padding]                  │
├──────────────────────────────────────┤
│ Tensor Data (bulk of the file)       │
│  ├─ blk.0.attn_q.weight [Q4_K_M]    │
│  ├─ blk.0.attn_k.weight [Q4_K_M]    │
│  ├─ ...                              │
│  └─ output.weight [Q6_K]            │
└──────────────────────────────────────┘
```

### 4.2 Quantization Block Layout

**Q4_K_M super-block (256 weights)**:
```
[FP16 scale_master][FP16 min_master]  ← 4 bytes
[8 × (6-bit scale, 4-bit min)]        ← 12 bytes (96 bits for scales+mins)
[256 × 4-bit weights]                  ← 128 bytes
Total: 144 bytes for 256 weights = 4.50 bits/weight
(With mixed precision on attention/output layers → effective ~4.58 bpw)
```

**Q8_0 block (32 weights)**:
```
[FP16 scale]           ← 2 bytes
[32 × int8 weights]    ← 32 bytes
Total: 34 bytes for 32 weights = 8.50 bits/weight
```

### 4.3 Could We Create a Better Format for Gemma 4?

**Problems with GGUF for RTX 5090**:

1. **No FP8 quantization type**: GGUF supports Q4, Q5, Q6, Q8, FP16, FP32 — but not FP8 (E4M3/E5M2). Blackwell's Tensor Cores can natively process FP8, which would be both faster AND higher-quality than Q8_0.

2. **No NVFP4 type**: NVIDIA's Blackwell-specific 4-bit format (FP4 E2M1 with per-group scale in FP8) is not represented in GGUF. This format is hardware-accelerated on RTX 5090 Tensor Cores.

3. **Block sizes not optimized for Tensor Cores**: GGUF's 32/256-weight blocks don't align with Tensor Core tile sizes (16×16, 32×32, etc.).

4. **No per-layer mixed-precision metadata**: A Gemma 4-optimized format could specify: "attention Q/K/V in FP8, MoE experts in NVFP4, shared expert in FP8, embeddings in FP16" — maximizing quality/speed tradeoff per component.

**Would a custom format help?**: Marginally. The real bottleneck is the *kernel* that processes the format, not the format itself. FP8 and NVFP4 support in llama.cpp (when it arrives) would be the correct fix. A custom format without custom kernels is pointless.

**UNCERTAINTY**: There are active discussions in the llama.cpp community about adding FP8 support (issue #18864 about generalizing MMQ for floating-point data). Timeline unclear.

---

## 5. Speculative Decoding

### 5.1 How E2B (Draft) + 26B (Target) Would Work

```
Speculative Decoding Loop:
  
  1. Draft phase (E2B, ~2B params):
     for i in 1..γ:  (γ = speculation length, typically 4-8)
       draft_token[i] = E2B.generate_one()
     → Fast: E2B at Q4_K_M ≈ 1000+ tok/s on RTX 5090
     → Cost: γ × (one E2B forward pass) ≈ γ × 1ms

  2. Verify phase (26B MoE, target):
     logits[1..γ] = 26B.forward_batch(prefix + draft_tokens[1..γ])
     → One forward pass over γ tokens in parallel
     → Cost: ≈ same as single-token decode (memory bandwidth bound)
     → The key insight: verifying γ tokens costs ≈ 1 token decode

  3. Accept/reject:
     for i in 1..γ:
       if random() < P_target(draft_token[i]) / P_draft(draft_token[i]):
         accept token[i]
       else:
         reject token[i], sample from adjusted distribution
         break
     → Guarantees output distribution matches target exactly

  4. Net tokens per round: 1 + (expected accepted tokens)
     → With α=0.7, γ=5: τ = (1-0.7^6)/(1-0.7) ≈ 2.8 tokens/round
```

### 5.2 Expected Acceptance Rate

The acceptance rate $\alpha$ depends on how well E2B's distribution matches 26B's:

**Favorable factors for E2B→26B**:
- Same model family (Gemma 4), same tokenizer, same training data distribution
- E2B was likely distilled from larger Gemma models
- For "easy" tokens (common patterns, function words): α ≈ 0.8-0.9
- Same-family draft models typically achieve α ≈ 0.6-0.8

**Unfavorable factors**:
- 26B MoE has far richer representations than 2B dense
- Complex reasoning tokens will be rejected frequently
- Vision/audio modality differences may cause distribution mismatch
- Temperature > 0 generally lowers acceptance rate

**Estimated acceptance rate**: $\alpha \approx 0.60\text{–}0.75$ for typical text generation tasks.

### 5.3 Expected Speedup

Using the theoretical formula $\tau = \frac{1 - \alpha^{\gamma+1}}{1 - \alpha}$:

| α | γ | τ (tokens/round) | Theoretical speedup | Practical speedup |
|---|---|-------------------|--------------------|--------------------|
| 0.60 | 4 | 2.27 | 2.27× | ~1.6-1.8× |
| 0.60 | 6 | 2.43 | 2.43× | ~1.7-2.0× |
| 0.70 | 5 | 2.85 | 2.85× | ~2.0-2.3× |
| 0.75 | 5 | 3.16 | 3.16× | ~2.2-2.5× |
| 0.80 | 6 | 3.69 | 3.69× | ~2.5-3.0× |

**Practical speedup ≈ 70-80% of theoretical** because:
- Draft model execution is not free (adds ~1ms per draft token)
- Verify pass with γ tokens is slightly more expensive than single-token (KV cache operations)
- GPU must context-switch between two models (or both must fit in VRAM simultaneously)

**VRAM requirement**: Both models must be resident simultaneously:
- E2B Q4_K_M: ~1.2 GB
- 26B MoE Q4_K_M: ~16 GB
- KV caches: ~1-2 GB
- **Total**: ~19 GB → fits comfortably in 32 GB RTX 5090

### 5.4 llama.cpp Speculative Decoding Support

llama.cpp has experimental speculative decoding via `--draft` and `--model-draft`:

```bash
llama-cli -m gemma4-26b-q4km.gguf \
          --model-draft gemma4-e2b-q4km.gguf \
          --draft 6 \
          -ngl 99
```

**Current limitations**:
- Marked as experimental
- May not be fully optimized for MoE target models
- Ollama does NOT expose speculative decoding through its API (as of v0.20.5)

---

## 6. Practical Hackathon Recommendation

### 6.1 What's Achievable in 2-3 Days

**Tier 0: Use Ollama as-is (0 hours, baseline)**
- E4B Q8_0: ~300-400 tok/s (estimated)
- E2B Q4_K_M: ~800-1000 tok/s (estimated)  
- 26B MoE Q4_K_M: ~120-190 tok/s (estimated, based on Q6_K ~190 tok/s benchmarks)
- 31B Q4_K_M: ~80-100 tok/s (estimated, tight VRAM)

**Tier 1: Optimize Ollama Configuration (2-4 hours)**
- Enable flash attention: `OLLAMA_FLASH_ATTENTION=1`
- Set `OLLAMA_NUM_PARALLEL=1` (disable multi-request, maximize single-stream)
- Set `OLLAMA_GPU_OVERHEAD=0` to maximize VRAM for model
- Pin `OLLAMA_MAX_LOADED_MODELS` to keep models hot
- Use Q4_K_M for 26B MoE (fits with headroom for KV cache)
- Benchmark with `ollama run` and system prompt to find sweet spot

**Tier 2: Direct llama.cpp (bypassing Ollama) (4-8 hours)**
- Build llama.cpp from source with CUDA 12.9, SM_120 target
- Use `llama-server` directly (eliminates cgo/Go overhead)
- Enable: `--flash-attn --ctx-size 8192 --n-gpu-layers 99`
- Expected improvement: 5-15% over Ollama (removing Go overhead)
- **Recommended for demo**: run `llama-server` and point Jemma's HTTP client at it

**Tier 3: Speculative Decoding with llama.cpp (8-16 hours)**
- Build latest llama.cpp with speculative decoding support
- E2B as draft, 26B MoE as target: `--model-draft` + `--draft 5`
- Expected: 1.6-2.3× speedup on 26B generation
- **Risk**: Experimental feature, may have bugs with Gemma 4 MoE models
- **Fallback**: If spec decode breaks, fall back to Tier 2

**Tier 4: vLLM with NVFP4 (16-24 hours, Linux required)**
- Install vLLM 0.12 with CUDA 12.9
- Load Gemma 4 26B MoE with NVFP4 quantization
- Expected: 1.5-2× improvement over llama.cpp Q4_K_M via Tensor Core NVFP4
- Benchmarked at 411 tok/s for RAG-8k workloads on RTX 5090 (Qwen3-8B reference)
- **Blocker**: Requires Linux. If workstation is Windows, need WSL2 with GPU passthrough
- **Risk**: Gemma 4 NVFP4 support in vLLM may be incomplete

**Tier 5: TensorRT-LLM with FP8 (24+ hours, NOT recommended for hackathon)**
- Highest potential performance (2× over llama.cpp)
- But: build process is painful, Gemma 4 MoE support uncertain, linux-only
- Save this for post-hackathon optimization

### 6.2 Recommended Path for Jemma Hackathon

```
Day 1:  Tier 1 (Ollama config) → establish baselines
        Tier 2 (raw llama.cpp) → if measurably faster, switch
        → All feature development uses whichever is faster

Day 2:  Feature development on SafeBrain agent
        Tier 3 (speculative decoding) → attempt during testing breaks
        → If it works: use for demo. If not: no time lost.

Day 3:  Demo polish, video recording
        → Use whatever stack is most stable and fast
```

### 6.3 Expected Performance Envelope

| Configuration | E2B tok/s | E4B tok/s | 26B MoE tok/s | 31B tok/s |
|--------------|-----------|-----------|---------------|-----------|
| Ollama default | ~800 | ~350 | ~130 | ~80 |
| Ollama optimized | ~900 | ~400 | ~150 | ~90 |
| llama.cpp direct | ~1000 | ~430 | ~170 | ~95 |
| llama.cpp + spec decode | N/A | N/A | ~280-350† | N/A |
| vLLM NVFP4 (Linux) | ~1200 | ~600 | ~300 | N/A‡ |

†Using E2B as draft model  
‡31B exceeds 32GB in most quantizations

**UNCERTAINTY on all numbers**: These are estimates based on extrapolation from available benchmarks (Gemma 3, Gemma 4 26B Q6_K, other 8B models on 5090). Actual performance should be benchmarked empirically.

### 6.4 The Real Answer

For a hackathon demo, the bottleneck is **not inference speed**. Even Ollama's default E4B at ~350 tok/s is imperceptibly fast for a human watching a demo. The 26B MoE at ~130 tok/s is also more than fast enough for interactive use (~2-3× human reading speed).

**The right investment is**:
1. 2 hours: Ollama flash-attention + config tuning
2. Remaining time: Agent features, demo scenario, video production
3. Post-hackathon: Build proper "Jemma Runtime" benchmarking suite with Tier 3-5 options

---

## Appendix A: Key Uncertainty Register

| Claim | Confidence | Basis |
|-------|-----------|-------|
| llama.cpp achieves ~60-76% memory BW utilization | **High** | Multiple independent benchmarks + NVIDIA blog |
| GGUF lacks FP8/NVFP4 types | **High** | Format spec review, confirmed by ongoing PRs |
| vLLM 35-44× throughput at high concurrency | **High** | Published benchmarks |
| Speculative decode E2B→26B α ≈ 0.60-0.75 | **Medium** | Extrapolation from same-family draft model literature |
| NVFP4 delivers 1.6× over BF16 on Blackwell | **High** | Multiple independent studies |
| TensorRT-LLM supports Gemma 4 MoE | **Low** | Not confirmed; Gemma 2 support exists |
| Specific tok/s numbers in the table | **Medium** | Extrapolated from partial benchmarks |
| CUDA Graphs active for Ollama's llama.cpp build | **High** | Default since mid-2024 |
| llama.cpp sequential expert execution in MoE | **Medium** | Inferred from architecture; fused kernel is experimental |
| Sliding window fully optimized in Ollama v0.20.5 | **Medium** | PR merged, but edge cases possible |

## Appendix B: Key Source Code Files in llama.cpp

For anyone wanting to trace the execution flow:

```
ggml/src/ggml-cuda/
├── mmq.cuh          — Custom quantized matmul kernels (Q4_K_M, Q8_0, etc.)
├── fattn*.cuh       — Flash Attention CUDA kernels
├── dequantize.cuh   — Weight dequantization routines
├── mmvq.cuh         — Matrix-vector product for quantized weights
├── softmax.cuh      — Fused softmax kernels
├── rope.cuh         — Rotary position embedding
├── norm.cuh         — RMSNorm kernel
└── ggml-cuda.cu     — Main CUDA backend, graph dispatch, CUDA Graphs

src/
├── llama.cpp        — Model loading, GGUF parsing, graph construction
├── llama-context.cpp — KV cache management, sliding window logic
└── llama-sampling.cpp — Token sampling (CPU-side)

common/
└── speculative.cpp  — Speculative decoding implementation
```

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **GEMV** | General Matrix-Vector multiply. Dominates autoregressive decode. |
| **GEMM** | General Matrix-Matrix multiply. Dominates prompt processing (prefill). |
| **MMQ** | llama.cpp's custom Mixed-precision Matrix multiplication for Quantized data |
| **NVFP4** | NVIDIA FP4 (E2M1 + FP8 scale), hardware-accelerated on Blackwell Tensor Cores |
| **PagedAttention** | Virtual memory-style KV cache allocation used by vLLM |
| **CUDA Graphs** | Pre-recorded sequences of GPU operations replayed with minimal overhead |
| **Ridge Point** | The arithmetic intensity where a workload transitions from memory-bound to compute-bound |
| **cgo** | Go's mechanism for calling C code; how Ollama invokes llama.cpp |
