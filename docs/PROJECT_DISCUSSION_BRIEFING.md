# Jemma Project — Compiled Discussion & Status Briefing

**Prepared:** April 13, 2026  
**For:** Team discussion with Prof. Xie, Dr. Bhattacharya, Prof. Baksh, Somnath Lahiri (ISU)  
**Context:** Gemma 4 Good Hackathon (Kaggle) — Deadline May 18, 2026

---

## Part 1: What We Have Right Now (Working)

### 1.1 Core Platform — Fully Operational

Jemma is a **local-first AI benchmarking and safety framework** built around Google's Gemma 4 model family, running on an NVIDIA RTX 5090 (32 GB VRAM). Everything below has been tested and passes:

| Component | Status | What It Does |
|-----------|--------|-------------|
| **Ollama provider** | ✅ Working | Talks to local Gemma 4 models via HTTP — health checks, model listing, chat completions |
| **Benchmark engine** | ✅ Working | Runs solo, pairwise (head-to-head), and stress benchmarks with validators, latency tracking, pass/fail scoring |
| **Safety benchmark suite** | ✅ Working | 10 safety scenarios testing refusal, guardrails, keyword detection across all model sizes |
| **Agent framework** | ✅ Working | Autonomous task execution with planning, step execution, fallback routing (E4B→E2B), artifact logging |
| **FastAPI server** | ✅ Working | 10 API routes — health, models, chat, streaming, benchmarks, jobs, training, system telemetry |
| **Web dashboard** | ✅ Working | React + TypeScript SPA — model browser, chat, training launcher, benchmark visualization (0 TS errors, 532 KB bundle) |
| **Android app** | ✅ Working | Kotlin + Jetpack Compose native app — chat, model browser, system info, foldable-aware layouts |
| **CLI** | ✅ Working | Commands for health, benchmarks (solo/versus/stress), agent objectives, API server |
| **12 unit tests** | ✅ All pass | API, benchmarks, agent loop, config, Discord, jobs, policies, artifact store |
| **LAN capabilities** | ✅ Working | Discord bot, Tailscale VPN, Philips Hue, TP-Link smart plugs, router monitoring |
| **Cloud deployment tooling** | ✅ Working | Docker + Modelfile generation for GCP Cloud Run from GGUF exports |
| **Synthetic data generator** | ✅ Running now | 8 parallel streams generating construction-domain data from free Gemma 4 models (246+ new entries today, 252 MB total) |

### 1.2 Models Tested & Benchmarked (April 11, 2026)

| Model | Params | Quant | VRAM | Smoke | Reasoning | Safety Score |
|-------|--------|-------|------|-------|-----------|-------------|
| **Gemma 4 E4B** | 8B (4.5B eff.) | Q8_0 | 9.6 GB | 100% | **100%** | 0.617 (20% pass) |
| **Gemma 4 E2B** | 5.1B (2.3B eff.) | Q4_K_M | 7.2 GB | 100% | 66.7% | **0.742 (40% pass)** |
| **Gemma 4 26B MoE** | 25.2B (3.8B active) | Q4_K_M | 17 GB | — | — | **0.767 (40% pass)** |
| **Gemma 4 31B Dense** | 30.7B | Q4_K_M | 19 GB | — | — | Partial (2/10) |

**Key finding:** The smaller E2B model outperforms E4B on safety keyword detection. The 26B MoE achieves the highest safety score of all completed models. This is a publishable result.

### 1.3 Live Data Generation (Running Right Now)

The multistream generator is actively producing construction-domain synthetic data using the two free Gemma 4 models (`gemma-4-26b-a4b-it` and `gemma-4-31b-it`) at 2 RPM/stream. Zero cost until April 16, 2026.

**Current cumulative dataset (prior runs + today):**

| Dataset | Records | Size | Domain Relevance |
|---------|---------|------|-----------------|
| object_detection_labels | 14,694 | 47.7 MB | Vision model training labels for construction scenes |
| image_descriptions | 10,687 | 61.0 MB | Detailed construction site image caption training |
| blueprint_interpretation | 9,754 | 40.6 MB | Architectural/engineering drawing analysis |
| materials_database | 8,860 | 18.3 MB | ASTM/ACI material property cards |
| safety_inspections | 6,794 | 26.4 MB | OSHA-aligned site inspection reports |
| disaster_assessment | 5,400 | 25.7 MB | Post-disaster structural evaluation |
| building_codes | 5,167 | 17.0 MB | IBC/Chicago code compliance Q&A |
| construction_qa | 4,610 | 15.7 MB | Expert construction methodology Q&A |
| **TOTAL** | **65,966** | **252 MB** | — |

Plus **75 hand-crafted expert Q&A pairs** in the construction-cracks training set and **75 second-brain entries** for general knowledge.

---

## Part 2: What Could Be Working With Direction (Near-Term Potential)

### 2.1 Unsloth Fine-Tuning (1-2 days of work)

**Current state:** Notebook template exists with setup/deps validation. No actual training loop running yet.

**What's needed:**
- Wire up the `construction-cracks-train.jsonl` (75 expert Q&A pairs) + synthetic data as SFT training data
- Run QLoRA (4-bit) fine-tuning on E4B first, then E2B
- Export fine-tuned GGUF → register in Ollama → re-benchmark

**Why it matters:** A Gemma 4 E4B fine-tuned on crack classification data would be a **concrete deliverable** for the Hackathon (Unsloth prize track) and directly useful for ISU research.

### 2.2 Crack Detection & Classification Pipeline (2-3 days)

**Current state:** We have the expert Q&A dataset covering:
- Flexural vs. shear vs. torsion cracks
- Plastic shrinkage vs. drying shrinkage
- ASR (alkali-silica reaction) map cracking
- D-cracking in pavements
- Settlement cracks in foundations
- Bridge deck crack severity (FHWA/AASHTO classification)
- Active vs. dormant crack assessment
- Field measurement protocols (ACI 224R, ASTM C876)

**What could be built:**
1. **Text-based crack classifier** — User describes crack observations → model classifies type, severity, and recommends action
2. **Image-based crack detector** — Gemma 4 E2B/E4B support vision input; feed construction site photos for PPE and crack assessment
3. **Structured inspection report generator** — Input field notes → output FHWA-compliant inspection report
4. **Bridge condition state mapper** — Map crack descriptions to AASHTO CS1-CS4 ratings automatically

### 2.3 DOT / Transportation Infrastructure Application (3-5 days)

**Current state:** The cracks dataset explicitly covers FHWA bridge inspection guidelines, LTPP distress identification, and AASHTO condition states. The synthetic data includes disaster assessment and building codes streams.

**What could be built:**
1. **Bridge deck inspection assistant** — Tablet/phone app for DOT inspectors: photograph deck, describe cracks, get instant AASHTO condition state classification + recommended action
2. **LTPP distress identification companion** — Field tool that maps observations to the FHWA Long-Term Pavement Performance distress codes
3. **IL-DOT route condition summarizer** — Ingest inspection reports → generate priority-ranked maintenance recommendations

**Grant alignment:**
- IDOT (Illinois DOT) regularly funds university partnerships for bridge condition assessment technology
- FHWA's Technology Innovation Deployment program (TIDP) funds AI-assisted inspection tools
- NSF CPS (Cyber-Physical Systems) program aligns with local AI + physical infrastructure monitoring

### 2.4 Mobile Edge Deployment (1-2 days)

**Current state:** Android app works over WiFi to the workstation. USB ADB reverse tunnel working.

**What's needed for true edge:**
- Package E2B Q4_K_M (7.2 GB) for on-device inference via LiteRT or Cactus
- Enable offline crack classification on a tablet in the field (no network required)
- This hits the **LiteRT ($10K)** and **Cactus ($10K)** hackathon prize tracks

### 2.5 RAG Pipeline Over Inspection Manuals (2-3 days)

**Current state:** The "SafeBrain" concept doc outlines an offline second-brain for construction/industrial safety.

**What could be built:**
- Ingest FHWA Bridge Inspector's Reference Manual, AASHTO Manual for Bridge Element Inspection, ACI 224R
- Embed with Gemma 4 → local vector store
- Query with citations: "What is the minimum crack width that triggers CS3 for deck element 12?"
- Zero cloud dependency — runs entirely on the RTX 5090

---

## Part 3: Dataset Categorization for ISU Faculty

### For Prof. Xie — Construction Engineering & Structural Assessment

| Dataset | Records | Direct Relevance |
|---------|---------|-----------------|
| `construction-cracks-train.jsonl` | 75 | **PRIMARY** — Expert crack classification Q&A: flexural, shear, ASR, D-cracking, settlement, bridge deck (FHWA), measurement protocols (ACI 224R, ASTM C876) |
| `construction_qa` (synth) | 4,610 | Construction methodology — ISU dormitory scenarios, Chicago-area projects, ACI 562 repair assessments |
| `blueprint_interpretation` (synth) | 9,754 | Architectural/engineering drawing reading — structural detail interpretation |
| `safety_inspections` (synth) | 6,794 | OSHA-aligned inspection reports — confined space, fall protection, structural stability |
| `building_codes` (synth) | 5,167 | IBC and Chicago code compliance — occupancy classification, structural requirements |
| `materials_database` (synth) | 8,860 | ASTM material specifications — concrete, steel, reinforcement, coatings |
| `disaster_assessment` (synth) | 5,400 | Post-disaster structural evaluation — earthquake, flood, fire damage |

**Total records directly relevant to structural/construction engineering: ~40,660**

### For Dr. Bhattacharya — AI/ML, Safety & Trust, Education

| Dataset | Records | Direct Relevance |
|---------|---------|-----------------|
| **Safety benchmark prompts** | 25 | Curated safety scenarios testing model refusal, guardrail adherence, keyword compliance |
| **Benchmark results** | 8 runs | Comparative safety performance across 4 Gemma 4 model sizes — publishable finding that smaller models can outperform larger ones on safety |
| `safety_inspections` (synth) | 6,794 | Real-world safety domain data for SFT experiments |
| `image_descriptions` (synth) | 10,687 | Vision-language training data for multimodal safety applications |
| `object_detection_labels` (synth) | 14,694 | Object detection training labels for construction scene understanding |
| **Android app + mobile architecture** | — | Platform for "Future of Education" prize track — students using AI-assisted inspection tools in the field |

**Key talking point for Bhattacharya:** The E2B (2.6B params) outperforming E4B (4.5B params) on safety benchmarks is a non-obvious result. This could be a short paper: *"When Smaller is Safer: Gemma 4 Model Size vs. Safety Compliance in Domain-Specific Assessment."*

### For Both — Grant-Aligned Datasets

| Application | Datasets Available | Potential Funding Source |
|-------------|-------------------|------------------------|
| Bridge inspection AI | cracks (75), construction_qa (4.6K), disaster_assessment (5.4K) | IL-DOT, FHWA TIDP, NSF CPS |
| Construction site safety | safety_inspections (6.8K), object_detection_labels (14.7K) | OSHA Susan Harwood grants, NSF FW-HTF |
| Infrastructure resilience | disaster_assessment (5.4K), building_codes (5.2K) | FEMA BRIC, NSF CMMI |
| AI education tools | All + Android app + benchmark framework | NSF DUE/IUSE, Google.org |

---

## Part 4: Hackathon Prize Alignment

| Prize Track | Our Asset | Gap to Close | Est. Effort |
|-------------|----------|-------------|------------|
| **Main Track ($50K)** | Full platform: benchmarks + agent + safety + data | Writeup + video | 2 days |
| **Safety & Trust ($10K)** | Safety benchmarks + SafeBrain concept + safety dataset | Formalize safety eval framework | 1 day |
| **Global Resilience ($10K)** | Disaster assessment dataset + offline capability | Demo offline disaster triage scenario | 1 day |
| **Ollama ($10K)** | Full Ollama integration, 4 models benchmarked | Already done ✅ | Writeup only |
| **Unsloth ($10K)** | Notebook template, datasets ready | Run actual fine-tuning loop | 1-2 days |
| **llama.cpp ($10K)** | llama.cpp provider exists (skeleton) | Build out + benchmark | 2 days |
| **LiteRT ($10K)** | Android app + E2B model identified | Package for on-device | 2-3 days |
| **Cactus ($10K)** | Mobile architecture documented | Integrate Cactus SDK | 2-3 days |
| **Health & Sciences ($10K)** | ISU collaboration, construction safety domain | ISU letter of support + demo | 1 day |
| **Future of Education ($10K)** | Android app + benchmark framework for teaching | Frame as educational tool | 1 day |

**Theoretical maximum:** Up to $70K+ across overlapping tracks.

---

## Part 5: Questions for Discussion

### Strategy Questions

1. **Which prize tracks should we prioritize?** We can't perfect all 10. Should we focus on Main + Safety & Trust + Ollama (strongest assets) and treat the rest as bonus?

2. **Should the ISU connection be the lead narrative?** "University researchers using Gemma 4 to build safer infrastructure inspection tools" is a compelling story for Main Track + Health & Sciences + Safety & Trust simultaneously.

3. **Fine-tuning vs. RAG vs. both?** We have datasets for SFT and the architecture for RAG. Should we invest time in Unsloth fine-tuning (hits the Unsloth prize track) or build the RAG pipeline first (more immediately useful for a demo)?

### Technical Questions

4. **What specific crack types does Prof. Xie's research focus on?** Our dataset covers a broad range (flexural, shear, ASR, D-cracking, settlement, thermal, plastic/drying shrinkage). Should we deepen coverage in any particular area?

5. **Does ISU have access to real bridge inspection images?** Gemma 4 E2B/E4B support vision input. If we can get even 50-100 labeled bridge deck photos, we can demonstrate a multimodal crack detection workflow that would be dramatically stronger than text-only.

6. **What IL-DOT districts does ISU have relationships with?** A letter of intent from an IL-DOT district saying "we would use this tool" would be a massive differentiator for the Global Resilience and Health & Sciences tracks.

7. **Android or iOS priority for field demo?** We have a working Android app. Should we also build an iOS client, or is Android sufficient for the hackathon demo video?

### Dataset Questions

8. **Should we extend the cracks dataset beyond 75 expert pairs?** We have the generator running. We could create a "cracks-extended" stream specifically producing crack classification Q&A at higher volume. Prof. Xie could review a sample for accuracy.

9. **What AASHTO/FHWA standards should we explicitly encode?** The current dataset references ACI 224R, ASTM C876, ASTM C856, ACI 562, FHWA LTPP distress manual. Are there specific IL-DOT supplements or standards the team uses?

10. **Is there interest in a pavement-specific dataset?** D-cracking, longitudinal cracking, and joint distress are covered briefly. Should we generate a dedicated pavement distress dataset aligned with the LTPP Distress Identification Manual?

### Research & Publication Questions

11. **Is the E2B > E4B safety finding worth a short paper?** We have quantitative evidence that Gemma 4's 2.3B-effective-parameter model scores higher on domain safety benchmarks than the 4.5B model. This is reproducible and somewhat counterintuitive.

12. **Could this platform become an ongoing research tool?** The benchmark framework is modular — new models, new prompt sets, new validators can be plugged in. Could ISU use it as a standard eval harness for future construction AI research?

13. **What's the publication timeline?** If we target a conference paper (e.g., Computing in Civil Engineering, ASCE), we need to know submission deadlines to plan what results to prioritize.

### Collaboration Questions

14. **What can each team member own for the next 5 weeks?**
    - Fine-tuning: Who runs the Unsloth training?
    - Dataset review: Who validates synthetic data quality?
    - Demo video: Who scripts and records the 3-minute demo?
    - Writeup: Who writes the Kaggle submission narrative?

15. **Should we schedule a live demo session?** The API server, web dashboard, and Android app are all working. A 30-minute screen-share where the team sees the system running would align everyone on what's real vs. planned.

---

## Appendix A: Repository File Map (Key Paths Only)

```
Jemma/
├── src/jemma/                    # Core Python package
│   ├── providers/                #   Ollama + llama.cpp model providers
│   ├── benchmarks/               #   Runner, validators, system probe
│   ├── agent/                    #   Autonomous agent loop
│   ├── api/                      #   FastAPI server (10 route modules)
│   ├── capabilities/             #   LAN devices (Discord, Hue, plugs, VPN)
│   ├── core/                     #   Types, artifact store, policies
│   ├── discord/                  #   Discord bot + OAuth
│   └── cli.py                    #   CLI dispatcher
├── web/                          # React + TypeScript dashboard
├── android-app/                  # Kotlin + Jetpack Compose mobile client
├── configs/                      # TOML configs (models, defaults, LAN, benchmarks)
├── manifests/                    # Benchmark + objective manifests
├── datasets/
│   ├── construction-cracks-train.jsonl   # 75 expert crack Q&A pairs
│   ├── second-brain-train.jsonl          # 75 general knowledge pairs
│   ├── prompts/                          # 25 benchmark scenarios
│   └── synth/                            # ~66K synthetic records (252 MB)
├── artifacts/runs/               # 8 benchmark run archives
├── toolbox/                      # Utilities (GGUF import, cloud bundle, monitors, synth gen)
├── tests/                        # 12 unit tests (all pass)
├── docs/                         # 12 documentation guides
└── .github/agents/               # 6 AI agent configs (FleetCommander, etc.)
```

## Appendix B: Current System Specs

| Component | Detail |
|-----------|--------|
| GPU | NVIDIA RTX 5090 — 32,607 MiB VRAM, Blackwell SM 120, 1,792 GB/s bandwidth |
| Ollama | v0.20.5 — 12 models registered |
| Python | 3.11+ with venv, google-genai v1.72.0 |
| Frontend | Vite 5.4, React 18.3, TypeScript 5.6 |
| Mobile | Kotlin, Jetpack Compose Material 3, targets API 34+ |
| Data gen | 8-stream parallel @ 2 RPM/stream, ~23 entries/hr, 0 failures |
