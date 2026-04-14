# QLoRA, MoE, KV Cache & Fine-Tuning Techniques

## QLoRA (Quantized Low-Rank Adaptation)
- Quantizes base model to 4-bit (NF4/FP4), trains low-rank adapters in bf16/fp16
- Only adapter weights are updated; base model frozen
- Jemma config: rank=32, alpha=64, targets q/k/v/o/gate/up/down projections
- Trainable params: ~85M / 6B total (1.4% of E4B)
- VRAM for training: ~12-14GB on E4B 4-bit (fits RTX 5090 easily)
- Key paper: Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs" (2023)
- Jemma training: 200 steps, batch 2, grad accum 8, lr 2e-4, warmup 20, cosine schedule

## LoRA Variants
- **LoRA**: Original low-rank decomposition (Hu et al., 2021)
- **QLoRA**: LoRA + NF4 quantization (Dettmers et al., 2023)
- **DoRA**: Weight-decomposed LoRA, separates magnitude/direction (Liu et al., 2024)
- **PiSSA**: Principal Singular Values adaptation (Meng et al., 2024)
- **rsLoRA**: Rank-stabilized LoRA with scaled init (Kalajdzievski, 2024)

## Mixture of Experts (MoE)
- Gemma 4 26B-A4B uses MoE: 26B total params, ~4B active per token
- Router selects top-k experts per token from pool of ~8-16 experts
- Advantage: Near-large-model quality at small-model inference cost
- Disadvantage: Full model weights still consume VRAM (~17GB at Q4)
- Training MoE: Typically done at pre-training, not fine-tuning
- Fine-tuning MoE: Apply QLoRA to shared layers + selected expert layers

## KV Cache Optimization
- During autoregressive generation, KV cache stores past key-value pairs
- Memory: O(batch × layers × heads × seq_len × head_dim)
- E4B at 131K context: KV cache can reach ~8-12GB at bf16
- Optimization strategies:
  1. **Quantized KV cache**: FP8 or INT8 KV values (50% memory reduction)
  2. **Sliding window attention**: Gemma uses local + global attention patterns
  3. **GQA (Grouped Query Attention)**: Gemma 4 uses GQA — fewer KV heads than Q heads
  4. **PagedAttention**: vLLM-style virtual memory paging for KV cache
  5. **KV cache sharing**: Multiple requests share prefix KV cache (common system prompt)

## KV Cache Sharing (Prompt Caching)
- When multiple queries share the same system prompt / context prefix
- Cache the KV values for the shared prefix once
- Subsequent queries skip recomputation of prefix tokens
- Ollama supports this natively for system prompts
- Reduces first-token latency by 30-60% for RAG workloads
- Critical for Jemma: all civic queries share the same system prompt + RAG docs

## Unsloth Optimizations
- Custom CUDA kernels for attention, RoPE, cross-entropy
- 2x faster training, 60% less VRAM vs standard HuggingFace
- Flash Attention 2 integration (falls back to Xformers on Windows)
- Gradient checkpointing: recompute activations to save VRAM
- Fused optimizers: AdamW with fused param updates

## AutoResearch / Self-Improvement Pattern
- Inspired by Karpathy's AutoResearch concept
- Loop: Generate questions → Answer with model → Score answers → Re-train on good answers
- Each iteration expands the training dataset with verified high-quality samples
- Requirements:
  1. A scoring function (automated benchmark or LLM-as-judge)
  2. A way to generate diverse questions (topic sampling, curriculum)
  3. A training pipeline that can incrementally add data (append to JSONL)
  4. A comparison mechanism (track score across iterations)

## GraphRAG
- Standard RAG: chunk → embed → vector search → generate
- GraphRAG: chunk → embed → extract entities → build knowledge graph → graph-aware retrieval
- Benefits: Better multi-hop reasoning, handles "what relates to X?" queries
- Implementation: NetworkX or SQLite graph, entity co-reference edges, hierarchical edges
- Jemma's GraphRAG: pipeline/graphrag.py with three retrieval strategies (vector, graph, hybrid)
