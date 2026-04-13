# Jemma SafeBrain — Comprehensive Hackathon Assessment & Writeup

**Date**: April 11, 2026  
**Hardware**: RTX 5090 (32 GB GDDR7, 1,792 GB/s bandwidth, SM 120 Blackwell)  
**Target**: Gemma 4 Good Hackathon (Kaggle)

---

## 1. Gemma 4 Model Matrix (Ground Truth from Ollama)

| Model | Total Params | Effective | Architecture | Modalities | Context | Q4 VRAM | Q8 VRAM | BF16 VRAM | Ollama Tag |
|-------|-------------|-----------|-------------|------------|---------|---------|---------|-----------|------------|
| E2B | 5.1B | 2.3B | Dense | Text+Vision+Audio | 128K | 7.2 GB | 8.1 GB | 10 GB | gemma4:2b |
| E4B | 8B | 4.5B | Dense | Text+Vision+Audio | 128K | 9.6 GB | 12 GB | 16 GB | gemma4:latest |
| 27B MoE | 25.2B | 3.8B active | MoE (128/8+1) | Text+Vision | 256K | 18 GB | 28 GB | 52 GB | gemma4:27b |
| 31B Dense | 30.7B | 30.7B | Dense | Text+Vision | 256K | 20 GB | 34 GB | 63 GB | gemma4:31b |

**Critical**: There is NO 12B Gemma 4 model. Any previous plans referencing 12B are invalid.

### RTX 5090 Dual-Model Combos

| Combo | Total VRAM | Fits? | Use Case |
|-------|-----------|-------|----------|
| E2B Q4 + 27B Q4 | 25.2 GB | ✅ Best | Speculative decoding (draft+target) |
| E2B Q4 + E4B Q8 | 19.2 GB | ✅ | Fast+quality pair |
| E4B Q4 + 27B Q4 | 27.6 GB | ⚠️ Tight | MoE reasoning |
| Any triple | >30 GB | ❌ | Never fits |

---

## 2. Ollama Architecture (GoogleMLScientist Report)

- **Tech stack**: Go (63.8%) + C (29.5%), MIT licensed
- **Backend**: llama.cpp compiled as static C library, linked via cgo (~0.2% overhead)
- **NOT a subprocess**: Direct in-process inference via C FFI
- **Recent Gemma 4 work**:
  - PR #15214: Add gemma4 support
  - PR #15378: Enable flash attention for gemma4
  - PR #15490: Update gemma4 Jinja renderer
- **Latest version**: v0.20.5

### Performance Characteristics (PhDResearcher Report)

- llama.cpp achieves **60-76% of theoretical memory bandwidth** on RTX 5090
- **Biggest gap**: llama.cpp does NOT use Tensor Cores for quantized inference. Dequantizes to FP16 and uses CUDA cores. RTX 5090's FP8/NVFP4 Tensor Core paths are completely unused.
- **Theoretical max**: Gemma 4 27B MoE Q4_K_M → ~326 tok/s. Observed: ~190 tok/s.
- For hackathon demo: **Ollama's default speed is more than sufficient** (130-350 tok/s depending on model)

### Speculative Decoding

- E2B (draft) → 27B (target): **1.6-2.3× speedup**, acceptance rate α ≈ 0.60-0.75
- Both fit in VRAM (~25.2 GB total)
- Ollama doesn't expose this — requires raw llama.cpp server
- **Recommendation**: Research mention only, don't implement for hackathon

---

## 3. WebUI Architecture (Implemented)

### Design System
- **Google Material Design 3** dark theme matching AI Studio aesthetic
- **Google Sans** font family (400/500/600/700)
- Tone-based surfaces: `#131314` → `#1e1f20` → `#252627` → `#2d2e2f` → `#383a3b`
- Primary: `#a8c7fa` (Google Blue), Tertiary: `#7fcfcf` (Teal/Safety)

### Four-Tab SPA

1. **Models** — Gemma 4 model cards with VRAM bars, modality chips, status badges (loaded/available), Ollama command hints. Shows both catalog and registered config models.

2. **Chat** — Streaming chat via Ollama (SSE), multimodal image upload (base64), model selector, abort control. Falls back to non-streaming `/api/chat` if Ollama stream is unreachable. Vite proxy routes `/ollama/*` to `localhost:11434`.

3. **Train** — Split layout: sidebar config (model, dataset, method, hyperparams) + main area (metrics dashboard, progress bar, training log). Polls `/api/training/status` every 3s. Can start/stop training via FastAPI endpoints that manage a background subprocess.

4. **Bench** — Full benchmark suite: stress, solo, pairwise. Live job events via SSE. Results visualization with recharts bar charts. Jobs/runs tables.

### Stack
- React 18.3 + TypeScript 5.6 + Vite 5.4
- recharts (charting), @radix-ui/react-tabs, @radix-ui/react-dialog
- Zero TypeScript compile errors

---

## 4. Backend Implementation

### Existing (14 tasks from prior session)
- `src/jemma/providers/llamacpp.py` — llama.cpp provider (OpenAI-compatible API)
- `src/jemma/providers/registry.py` — Multi-provider support (Ollama + llama.cpp)
- `toolbox/import_gguf_to_ollama.py` — GGUF → Ollama import automation
- Safety benchmarks: `datasets/prompts/safety-benchmark.jsonl`, `safety-reasoning.jsonl`
- 3 benchmark manifests for safety domain evaluation
- Launch scripts: `launch_llamacpp_server.sh`, `launch_llamacpp_server.ps1`

### New (this session)
- `src/jemma/api/routes/training.py` — Training control API:
  - `GET /api/training/status` — Poll training state
  - `POST /api/training/start` — Start training subprocess
  - `POST /api/training/stop` — Terminate training
- Registered in `app.py` alongside existing 9 route modules

### Unsloth Notebook
- `gemma4-31b-unsloth-local-5090.ipynb` — Fixed and aligned:
  - `lora_alpha` 16 → 8 (correct 1:4 ratio with rank 32)
  - `standardize_data_formats()` for data normalization
  - `train_on_completions()` (renamed from deprecated API)
  - HF Hub push support via `JEMMA_PUSH_TO_HUB=1`
  - Chat template: `gemma-4` (not gemma-4-thinking)

---

## 5. Prize Targeting Strategy (FleetCommander Report)

| Prize | Feasibility | Action |
|-------|------------|--------|
| **Main Track** ($50K 1st) | HIGH | Core submission — safety framework + WebUI |
| **Safety & Trust** ($10K) | HIGH | Natural fit — safety benchmarking IS the product |
| **Ollama Prize** ($10K) | HIGH | Fully integrated, model cards, streaming chat |
| **Unsloth Prize** ($10K) | MEDIUM | Need one complete fine-tune run on safety data |
| **llama.cpp Prize** ($10K) | MEDIUM | Provider exists, add one benchmark run |
| **LiteRT / Cactus** | CUT | No realistic path |

**Realistic ceiling**: $80K (1st + prizes) or $40K (2nd/3rd + prizes)

---

## 6. Critical Path (FleetCommander Execution Plan)

### Phase A: Foundation Lock (Days 1-5)
- [x] Corrected model matrix propagated through configs
- [x] WebUI shipped (Models + Chat + Train + Bench tabs)
- [ ] One complete Unsloth fine-tune: E4B on safety data, QLoRA 4-bit
- [ ] Full safety benchmark suite run: E2B Q4, E4B Q8, 27B Q4

### Phase B: Demo Pipeline (Days 6-15)
- [ ] Import fine-tuned checkpoint via GGUF → Ollama
- [ ] Benchmark pre vs post fine-tuning
- [ ] Draft writeup outline with evidence mapping

### Phase C: Narrative & Polish (Days 16-28)
- [ ] Write full writeup ≤1500 words with benchmark evidence
- [ ] Record 3-min demo video
- [ ] Code cleanup, README, reproducibility check

### Phase D: Submission Sprint (Days 29-37)
- [ ] Writeup revision
- [ ] Video polish
- [ ] Submit to Kaggle

---

## 7. What Was Cut (and Why)

1. **Speculative decoding implementation** — Research-only. Mention in writeup as future work.
2. **LiteRT / Cactus edge deployment** — No implementation started. Would dilute focus.
3. **Live training API driving real GPU training** — Replaced with notebook-driven training + status monitoring UI. The notebook IS the training interface.
4. **31B Dense as a primary target** — Keep E2B, E4B, 27B MoE. 31B adds marginal value during demo.
5. **BF16 baselines in demo** — Offline validation only, not featured in video.

---

## 8. Agent Conflict Resolution

| Conflict | Resolution |
|----------|-----------|
| llama.cpp vs Ollama for demo | **Ollama wins**. llama.cpp provider exists as prize track checkbox. |
| Live training API vs notebook | **Notebook wins**. Train tab shows status/logs, not a full training UI. |
| Speculative decoding priority | **Writeup mention only**. Zero implementation time. |
| E4B vs 27B as primary model | **E4B for chat, 27B for reasoning benchmarks**. Both demonstrated. |

---

## 9. File Inventory

### Created This Session
- `web/src/styles.css` — Google MD3 dark theme (complete rewrite)
- `web/src/types.ts` — Expanded types + Gemma 4 model catalog
- `web/src/api.ts` — Streaming chat, training endpoints, URL encoding
- `web/src/App.tsx` — 4-tab SPA (Models/Chat/Train/Bench)
- `src/jemma/api/routes/training.py` — Training control API

### Modified This Session
- `web/vite.config.ts` — Added Ollama proxy (/ollama → :11434)
- `src/jemma/api/app.py` — Registered training router

### Created Prior Session
- `src/jemma/providers/llamacpp.py`
- `toolbox/import_gguf_to_ollama.py`
- `datasets/prompts/safety-benchmark.jsonl`
- `datasets/prompts/safety-reasoning.jsonl`
- `benchmarks/manifests/safety-solo.toml`
- `benchmarks/manifests/safety-pairwise-ollama-llamacpp.toml`
- `benchmarks/manifests/safety-stress.toml`
- `scripts/launch_llamacpp_server.sh`
- `scripts/launch_llamacpp_server.ps1`

---

## 10. Open Questions

1. **Unsloth compatibility**: Does the latest Unsloth support Gemma 4 E4B with audio encoder? Need to verify before the fine-tune run.
2. **VRAM monitoring**: The WebUI VRAM bar currently shows static data. Could poll `nvidia-smi` via the system endpoint for live values.
3. **Ollama multimodal**: Does Ollama's `/api/chat` properly handle the `images` array for Gemma 4's vision encoder? Need to test with the chat tab.
4. **Training script**: `scripts/run_training.py` doesn't exist yet. The training API gracefully falls back to a notebook suggestion, but a headless training script would enable the full WebUI training flow.
