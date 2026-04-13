# Jemma Competition Strategy: Multimodal Raw Stack

> **Branch**: `feat/multimodal-raw-stack`
> **Date**: April 13, 2026
> **Hardware**: RTX 5090 (32GB GDDR7) + Pixel phone (E2B)

---

## Executive Summary

Jemma is a **local-first multimodal civic intelligence system** that processes text, images, audio, and video from the Town of Normal, Illinois — entirely on consumer hardware, entirely private. This document records every architectural choice, why it was made, and how it positions us to win the Gemma 4 Good Hackathon.

**Total prize exposure: up to $80K** across Main Track ($50K), Ollama ($10K), Digital Equity ($10K), Safety & Trust ($10K).

---

## 1. Track Targeting & Win Conditions

### Tier 1: Dual-Prize Targets

| Track | Prize | Why We Win | Key Demo |
|---|---|---|---|
| **Main Track** | $50K | No competitor will demonstrate all 4 modalities on real civic data running locally. Most build chatbots. We build a civic intelligence system. | Live dashboard processing Town of Normal budget PDFs, meeting audio, infrastructure photos, traffic video |
| **Ollama Technology** | $10K | We literally run E4B + 31B locally via Ollama on RTX 5090 with intelligent routing. Most competitors demo cloud API calls. | Dual-model routing with real latency numbers visible |

### Tier 2: Impact Tracks

| Track | Prize | Angle |
|---|---|---|
| **Digital Equity** | $10K | "Civic data is public in theory but private in practice. Jemma makes it actually public." Budget PDFs → plain language, meetings → 3-bullet summaries, permits → "what's being built next door" |
| **Safety & Trust** | $10K | Zero-cloud architecture. PII in building permits and meeting recordings never leaves the municipality's network. Every output grounded with source citations. |

### Tier 3: Stretch

| Track | Prize | Angle |
|---|---|---|
| **Global Resilience** | $10K | Offline civic data processing during disaster. RTX 5090 + Pixel E2B = field-deployable civic continuity system. Normal is a template for 10,000+ intermediary cities worldwide. |

---

## 2. Model Architecture Choices

### Why E4B as Primary (Not 31B)

| Factor | E4B | 31B | Decision |
|---|---|---|---|
| **Audio** | Native ASR/AST | None | E4B wins — council meetings are audio |
| **Video** | Native at 1fps | Frame extraction only | E4B wins — traffic analysis needs native video |
| **Image** | ✅ (150M vision encoder) | ✅ (550M encoder) | 31B slightly better for complex docs |
| **Text** | 128K context | 256K context | 31B wins for full budget documents |
| **VRAM@bf16** | 15 GB | 58.3 GB (doesn't fit) | E4B is the only bf16-capable option |
| **VRAM@4bit** | 5 GB | 17.4 GB | Both fit at 4-bit simultaneously |
| **Speed** | Fast (4.5B effective) | Slow (30.7B) | E4B 6-7x faster |

**Conclusion**: E4B handles all 4 modalities. 31B adds deep document reasoning when needed. **E4B at bf16 is the primary workhorse.**

### Quantization Strategy

**E4B at bf16 (15 GB)** — maximum quality for all multimodal tasks. On 32GB VRAM:
- Weights + encoders: 16.7 GB committed
- Remaining: 15.3 GB for KV cache + activations
- Full 128K context KV cache: only ~2.3 GB (hybrid attention makes this efficient)
- **Result**: Can process 128K-token documents with 12+ GB headroom

**31B loaded on-demand via hot-swap** — when E4B finishes multimodal work, unload it, load 31B at int4 (17.4 GB) for heavy text reasoning. Swap time: ~3-5s.

### Why NOT Unsloth for Multimodal

Unsloth optimizes text-only QLoRA. For multimodal fine-tuning (vision + audio), we **must** use the raw stack:
- `transformers` (AutoModelForMultimodalLM + AutoProcessor)
- `trl` (SFTTrainer)
- `peft` (LoraConfig)
- `bitsandbytes` (4-bit quantization)

This is Google's officially documented approach for Gemma 4 multimodal fine-tuning.

---

## 3. Hardware Maximization Strategy

### VRAM Budget (32 GB Total)

```
E4B@bf16 weights:     15.0 GB
Vision encoder:         0.15 GB
Audio encoder:          0.30 GB
CUDA context:           0.80 GB
─────────────────────
Committed:             16.25 GB
Available:             15.75 GB
  └─ KV cache@128K:    2.30 GB
  └─ Activations:      ~2.20 GB
  └─ Headroom:         11.25 GB  ← for batching, images, audio, video
```

### Throughput Targets (E4B@bf16, RTX 5090)

| Modality | Task | Items/Hour |
|---|---|---|
| Images | Classify (budget=70, batch=64) | 18,000–24,000 |
| Images | Caption (budget=280, batch=16) | 3,000–5,000 |
| Images | OCR (budget=1120, batch=4) | 500–900 |
| Audio | Transcribe (30s chunks) | 1,400–2,400 (~12-20x realtime) |
| Video | Summarize (60s, 1fps) | 400–720 |
| Text | Summarize (4K tokens, batch=32) | 4,000–6,000 |
| **Mixed** | **General ingestion** | **2,000–4,000** |

### Attention Optimization

```python
# RTX 5090 Blackwell optimal config
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.set_float32_matmul_precision("high")

# SDPA backend (reliable on Windows; flash-attn optional)
torch.backends.cuda.enable_flash_sdp(True)
torch.backends.cuda.enable_mem_efficient_sdp(True)
torch.backends.cuda.enable_cudnn_sdp(True)
```

### KV Cache at 128K

E4B uses hybrid attention: ~9 global layers (full context) + ~27 sliding window layers (512 tokens). Only global layers store full-context KV:

| Context | KV Cache (bf16) | KV Cache (int8) |
|---|---|---|
| 4,096 tokens | 99 MB | 50 MB |
| 32,768 tokens | 603 MB | 302 MB |
| 128,000 tokens | **2,277 MB** | **1,139 MB** |

**128K context costs only ~2.3 GB** thanks to hybrid attention.

---

## 4. Data Pipeline: Town of Normal

### Text Sources → 31B (256K context)

| Source | Processing | Competition Value |
|---|---|---|
| Annual Budget PDFs (FY2021-2027) | Full document → structured JSON → plain-English summary | "It read the 200-page budget and told me where money goes" |
| Municipal Code | Semantic search + ordinance summarization | Searchable law database in plain English |
| Council Agendas/Minutes | Extract motions, votes, action items | Decision timeline with responsible parties |

### Image Sources → E4B (vision)

| Source | Processing | Competition Value |
|---|---|---|
| Infrastructure photos | Condition classification: good/fair/poor/critical | Prioritized maintenance report |
| GIS/zoning maps (ArcGIS portal) | Zone boundary extraction, land use identification | Natural-language zoning per parcel |
| Building permit site plans | Floor plan interpretation | "3-story mixed-use, 25K sqft, 40 parking" |

### Audio Sources → E4B (native audio encoder)

| Source | Processing | Competition Value |
|---|---|---|
| Council meeting recordings | 30s chunks → ASR → combine → summarize | Full transcript + extracted motions/votes |
| Public comment periods | Transcribe + topic-classify | Resident concerns database |

### Video Sources → E4B (native video)

| Source | Processing | Competition Value |
|---|---|---|
| Traffic camera clips | 1fps count vehicles, pedestrians, near-misses | Intersection safety report |
| Construction progress | Frame-by-frame progress tracking | Automated public works updates |

---

## 5. Research Framing

*(PhDResearcherScientistProfessor analysis)*

### Academic Position: "Local-First Civic Multimodal Intelligence"

Sits at the intersection of Open Government Data, Edge AI, and Multimodal Document Understanding. **Avoid** "Smart City" (vendor-associated) and "Digital Twin" (implies full spatial simulation).

### Key Arguments

1. **Legal requirement**: Illinois BIPA means processing council meeting audio through a cloud API arguably requires written biometric consent from every speaker. Local processing is a **compliance architecture**.

2. **Underserved market**: 19,100 of 19,502 US municipalities are under 50K population. Every existing civic AI product targets cities >250K. Normal represents the long tail no vendor serves.

3. **Privacy by design**: Zero data exfiltration. All processing on local hardware. PII never transmitted. Full audit trail.

4. **Evaluation rigor**: Document processing (CER, WER, table F1), safety (compliance rate, hallucination rate), operational (FOIA response time reduction), comparative (E2B vs. E4B, local vs. cloud, vision OCR vs. Tesseract).

### Unique Differentiators vs. API Competitors

| Factor | API Competitors | Jemma (Local) |
|---|---|---|
| Privacy | Civic PII sent to cloud | Never leaves city hall |
| Cost | $0.01-0.10/call × millions | One-time hardware, $0 marginal |
| Offline | Fails without internet | Works anywhere |
| Auditability | Black box | Full local logs |
| Multimodal | Single model per call | Intelligent E4B+31B routing |

**Killer line**: *"Every other submission sends your data to the cloud. Jemma keeps your city's data in your city."*

---

## 6. Installation Stack

### Raw Multimodal Stack (NOT Unsloth)

```powershell
# PyTorch 2.7+ for Blackwell SM_120
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Core ML
pip install "transformers>=4.52.0" "accelerate>=1.6.0" "bitsandbytes>=0.45.0"
pip install "peft>=0.15.0" "trl>=0.18.0" sentencepiece protobuf

# Multimodal dependencies
pip install "Pillow>=10.0" "librosa>=0.10.0" soundfile "av>=13.0" opencv-python-headless

# Monitoring + data
pip install nvidia-ml-py3 psutil "datasets>=3.0" pandas pyarrow
```

### Version Compatibility

| Package | Min Version | Reason |
|---|---|---|
| PyTorch | 2.7.0 | Blackwell SM_120 support |
| transformers | 4.52.0 | Gemma 4 AutoModelForMultimodalLM |
| accelerate | 1.6.0 | device_map with multimodal |
| bitsandbytes | 0.45.0 | 4-bit quantization stability |
| peft | 0.15.0 | LoRA with ensure_weight_tying |
| trl | 0.18.0 | SFTTrainer multimodal collator |

---

## 7. Demo Plan

### Must-Have Demos (5 modality tests)

1. **Text + Thinking**: Load E4B → system prompt → enable thinking → civic question → structured response
2. **Image Understanding**: Load local image → ask about content → get description with bounding boxes
3. **Audio ASR**: Load 30s WAV clip → transcribe → output text
4. **Video Understanding**: Load short video → describe scene → extract information
5. **Function Calling**: Define civic tools → ask question → model generates tool call → execute → final response

### Killer Demo: "What Changed This Month"

Automated civic digest from all modalities — new permits, budget changes, meeting decisions, infrastructure assessments. Process real Town of Normal data through all 4 modality pipelines and produce a unified report.

---

## 8. Submission Artifacts

1. **Live Web Dashboard** (Streamlit/Gradio) — no login required
2. **3-minute video** — hook → problem → demo → architecture → impact → CTA
3. **Kaggle writeup** (≤1,500 words) — problem → solution → architecture → demo → impact → privacy
4. **Clean GitHub repo** — one-command setup, architecture diagram, README
5. **Published HuggingFace model** — fine-tuned E4B with benchmarks

---

## Agent Attribution

This strategy document incorporates analysis from:
- **KaggleCompetitor**: Track targeting, demo artifacts, video structure, scoring optimization, risk mitigation
- **GoogleMLScientist**: VRAM budgets, quantization strategy, throughput estimates, KV cache math, installation commands
- **PhDResearcherScientistProfessor**: Academic framing, legal analysis (BIPA), evaluation metrics, ethical considerations, ISU connection
