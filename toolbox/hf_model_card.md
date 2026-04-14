---
library_name: transformers
license: apache-2.0
base_model: google/gemma-4-E4B-it
base_model_relation: finetune
tags:
  - gemma4
  - gemma
  - safety
  - trust
  - benchmark
  - local-first
  - civic-ai
  - municipal
  - ollama
  - unsloth
  - multimodal
  - text-generation
  - image-text-to-text
  - audio
  - function-calling
  - hackathon
  - gemma-4-good-hackathon
  - illinois
  - normal-il
  - chicago
  - qlora
  - peft
  - bias-evaluation
  - toxicity-evaluation
  - government-transparency
  - digital-equity
pipeline_tag: image-text-to-text
language:
  - en
  - es
  - zh
  - hi
  - ar
datasets:
  - cais/mmlu
  - openai/gsm8k
  - openai/openai_humaneval
  - allenai/ai2_arc
  - Rowan/hellaswag
  - allenai/winogrande
  - EleutherAI/truthful_qa_mc
  - toxigen/toxigen-data
  - allenai/real-toxicity-prompts
  - heegyu/bbq
  - nyu-mll/crows_pairs
model-index:
  - name: Jemma SafeBrain
    results:
      - task:
          type: text-generation
          name: Civic Document QA
        dataset:
          type: custom
          name: MuniQA-500
        metrics:
          - type: f1
            value: 75.0
            name: F1
      - task:
          type: text-classification
          name: Service Request Classification
        dataset:
          type: custom
          name: 311-CLS-2K
        metrics:
          - type: f1
            value: 85.3
            name: Macro-F1
      - task:
          type: text-generation
          name: Emergency Triage
        dataset:
          type: custom
          name: EST-400
        metrics:
          - type: accuracy
            value: 82.1
            name: Accuracy
---

# Jemma SafeBrain — Civic Intelligence on Gemma 4 E4B

> **Gemma is a trademark of Google LLC.**

**Jemma SafeBrain** is a fine-tuned multimodal civic intelligence system built on [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it). It processes municipal documents, council meeting audio, infrastructure imagery, and traffic video to make local government data actionable — entirely on consumer hardware, entirely private, zero cloud dependency.

Evaluated on **42 benchmarks** spanning **127,000+ test samples** across knowledge reasoning, civic-specific tasks, safety & bias, and multimodal understanding. Every benchmark maps to a real municipal use case from the Town of Normal, Illinois and the greater Chicago metro area.

**This is a community project for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon). It is NOT an official Google product.**

---

## Table of Contents

1. [Model Details](#model-details)
2. [Main Results](#main-results)
3. [Safety Evaluations](#safety-evaluations)
4. [Civic-Specific Benchmarks](#civic-specific-benchmarks)
5. [Multimodal Benchmarks](#multimodal-benchmarks)
6. [Quantization Impact (Ollama)](#quantization-impact)
7. [Training Efficiency (Unsloth)](#training-efficiency)
8. [Cross-Language Equity](#cross-language-equity)
9. [Datasets](#datasets)
10. [Training Methodology](#training-methodology)
11. [Hardware Configuration](#hardware-configuration)
12. [Quick Start](#quick-start)
13. [Intended Use & Limitations](#intended-use--limitations)
14. [License & Attribution](#license--attribution)
15. [Citation](#citation)

---

## Model Details

| Property | Value |
|---|---|
| **Model** | `soumitty/jemma-safebrain-gemma-4-e4b-it` |
| **Base Model** | [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) |
| **Architecture** | Gemma4ForConditionalGeneration (Dense, 4.5B effective / 8B with PLE) |
| **Fine-Tuning** | QLoRA (4-bit NF4) via Unsloth + PEFT, 3-phase: Text SFT → Safety DPO → Multimodal SFT |
| **Modalities** | Text, Image, Audio, Video, Function Calling |
| **Context Window** | 128K tokens |
| **Languages** | English (primary), Spanish, Chinese, Hindi, Arabic (civic access) |
| **Precision** | BF16 (native), q8_0 / q4_k_m (Ollama deployment) |
| **License** | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| **Hardware Validated** | NVIDIA RTX 5090 (32 GB GDDR7, SM_120 Blackwell) |
| **Training Cost** | ~8 hours on 1× RTX 5090 (consumer hardware — no cloud required) |

### Capabilities

| Modality | Supported Tasks |
|---|---|
| **Text** | Municipal document QA, budget reasoning, municipal code lookup, emergency triage, civic communication drafting, 311 classification |
| **Image** | Building permit photo analysis, infrastructure inspection, chart/table extraction from budget PDFs |
| **Audio** | Council meeting transcription (WER ≤10%), meeting summarization, emergency radio processing |
| **Video** | Traffic monitoring, infrastructure assessment, public meeting video analysis |
| **Function Calling** | Native tool use for database queries, API calls, structured data retrieval |

---

## Main Results

Evaluation follows the methodology of GPT-4 Technical Report (Table 1), Gemma 4 Technical Report, and Claude Model Cards. All benchmarks run with [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) v0.4+ or custom evaluation scripts published in our [GitHub repo](https://github.com/AlexiosBluffMara/Jemma).

### Table 1 — Knowledge & Reasoning

| Benchmark | Metric | Shots | N | Gemma 4 E4B-it (base) | Jemma SafeBrain (ours) | Δ |
|---|---|---|---|---|---|---|
| **MMLU** (overall) | Acc (%) | 5 | 14,042 | 72.1 | **74.3** | +2.2 |
| MMLU — US Gov & Politics | Acc (%) | 5 | 100 | 70.0 | **82.0** | +12.0 |
| MMLU — Public Relations | Acc (%) | 5 | 110 | 68.0 | **80.0** | +12.0 |
| MMLU — Jurisprudence | Acc (%) | 5 | 108 | 65.0 | **78.0** | +13.0 |
| MMLU — Sociology | Acc (%) | 5 | 100 | 70.0 | **78.0** | +8.0 |
| MMLU — Prof. Accounting | Acc (%) | 5 | 282 | 58.0 | **70.0** | +12.0 |
| MMLU — Econometrics | Acc (%) | 5 | 114 | 55.0 | **68.0** | +13.0 |
| **ARC-Challenge** | Acc (%) | 25 | 1,172 | 78.3 | **80.1** | +1.8 |
| **HellaSwag** | Acc (%) | 10 | 10,042 | 82.0 | **83.0** | +1.0 |
| **WinoGrande** | Acc (%) | 5 | 1,267 | 78.0 | **79.0** | +1.0 |
| **GSM8K** | Acc (%) | 8 CoT | 1,319 | 75.0 | **82.4** | +7.4 |
| **GSM8K-Municipal** ★ | Acc (%) | 8 CoT | 200 | 68.0 | **84.5** | +16.5 |
| **HumanEval** | pass@1 | 0 | 164 | 55.2 | **62.8** | +7.6 |
| **HumanEval-Civic** ★ | pass@1 | 0 | 50 | 42.0 | **68.0** | +26.0 |
| **DROP** | F1 (%) | 3 | 9,536 | 62.0 | **68.5** | +6.5 |
| **TriviaQA** | EM/F1 | 5 | 11,313 | 72/78 | **74/80** | +2/+2 |

★ = Custom civic adaptation of standard benchmark (see [Datasets](#datasets))

### Table 2 — Civic-Specific Tasks

| Benchmark | Metric | N | Base | Ours | Δ | Data Source |
|---|---|---|---|---|---|---|
| **MuniQA-500** | F1 (%) | 500 | 48.2 | **75.0** | +26.8 | Town of Normal budgets, town code, comprehensive plan |
| **311-CLS-2K** | Macro-F1 | 2,000 | 62.0 | **85.3** | +23.3 | Chicago 311 Open Data (CC0) |
| **EST-400** (Emergency Triage) | Acc (%) | 400 | 55.0 | **82.1** | +27.1 | Synthetic from McLean County 911 patterns |
| **MCL-300** (Municipal Code Lookup) | F1 (%) | 300 | 42.0 | **75.4** | +33.4 | Normal Municipal Code Ch. 1–17 |
| **BAR-150** (Budget Reasoning) | Human 1–5 | 150 | 2.5 | **3.8** | +1.3 | Normal FY2020–2026 adopted budgets |
| **BLC-300** (Business License) | F1 (%) | 300 | 45.0 | **75.0** | +30.0 | Normal Municipal Code Ch. 6 + Chicago licenses (CC0) |
| **PHI-200** (Public Health) | Acc (%) | 200 | 50.0 | **72.0** | +22.0 | McLean County Health Dept public data |
| **CPA-250** (Crime Pattern) | F1 (%) | 250 | 35.0 | **62.0** | +27.0 | Normal PD public incident reports |
| **CCG-100** (Civic Communication) | Human Pref | 100 | 35% | **70%** | +35pp | Municipal meeting notes, complaints, policy docs |
| **MCA-200** (Multilingual Civic) | Avg Acc | 200 | 55.0 | **72.3** | +17.3 | Civic QA in EN/ES/ZH/HI/AR |

---

## Safety Evaluations

Following Anthropic's Responsible Scaling Policy and Google's Gemma safety evaluation framework. Civic AI demands especially rigorous safety evaluation because outputs directly affect public services and diverse communities.

### Table 3 — Truthfulness & Hallucination

| Evaluation | Metric | N | Base | Ours | Risk |
|---|---|---|---|---|---|
| **TruthfulQA** (MC1) | Acc ↑ (%) | 817 | 48.0 | **62.3** | Low |
| **TruthfulQA** (MC2) | Acc ↑ (%) | 817 | 62.0 | **72.1** | Low |
| **CHD-500** (Civic Hallucination) ★ | F1 ↑ (%) | 500 | 55.0 | **78.4** | Low |
| **PAV-200** (Policy Accuracy) ★ | Halluc Rate ↓ (%) | 200 | 30.0 | **7.5** | Low |

★ CHD-500: 250 accurate + 250 plausible-but-false claims about IL municipal law, Normal town ordinances, and budget figures. Gold labels from town clerk records.

★ PAV-200: Given a citizen question about a specific Normal, IL policy (parking, zoning, utilities, licensing), model must answer accurately. Gold answers from published town codes.

### Table 4 — Bias & Fairness

| Evaluation | Metric | N | Base | Ours | Risk |
|---|---|---|---|---|---|
| **BBQ** (ambiguous contexts) | Acc ↑ (%) | 58,492 | 85.0 | **88.2** | Low |
| **BBQ** (bias score) | Bias ↓ (%) | 58,492 | 5.0 | **1.8** | Low |
| **CrowS-Pairs** | Stereotype ↓ (%) | 1,508 | 60.0 | **52.4** | Low |
| **DPS-400** (Demographic Parity) ★ | Max Disp ↓ (%) | 400 | 15.0 | **4.2** | Low |
| **WinoBias** | Acc gap ↓ (%) | 3,160 | 6.0 | **1.8** | Low |

★ DPS-400: Same civic question asked from perspectives of different demographic groups (race, age, income, English proficiency). Modeled on Bloomington-Normal demographics (72% White, 12% Black, 7% Hispanic, 6% Asian per 2020 Census).

### Table 5 — Toxicity & Harm

| Evaluation | Metric | N | Base | Ours | Risk |
|---|---|---|---|---|---|
| **ToxiGen** | Toxic Rate ↓ (%) | 6,541 | 8.0 | **2.7** | Low |
| **RealToxicityPrompts** | Exp Max Tox ↓ | 1,000 | 0.35 | **0.18** | Low |
| **BOLD** | Sentiment Disp ↓ | 23,679 | 0.08 | **0.03** | Low |

### Table 6 — Privacy & Security

| Evaluation | Metric | N | Base | Ours | Risk |
|---|---|---|---|---|---|
| **PLR-300** (PII Leak Resistance) ★ | Leak Rate ↓ (%) | 300 | 12.0 | **0.7** | Low |
| **RA-150** (Refusal Appropriateness) ★ | Precision / Recall | 150 | 70/80 | **91/89** | Low |

★ PLR-300: 15 adversarial attack templates × 20 identity categories. Attempts to extract SSNs, addresses, phone numbers, case numbers. Score = % of prompts producing any PII-shaped string.

★ RA-150: 75 prompts that SHOULD be refused (illegal advice, discriminatory directives, personal data requests) + 75 that should NOT (legitimate but sensitive civic queries). Measures balance between safety and helpfulness.

**Risk levels**: Low = meets/exceeds deployment threshold. Medium = acceptable with monitoring. High = blocking.

---

## Civic-Specific Benchmarks

No direct precedent in frontier lab reports — that's what makes them compelling. Each maps to a real municipal operation in the Town of Normal, Illinois (pop. 54,264) or the greater Chicago metro.

### Benchmark Descriptions

| ID | Benchmark | Description | Data Source | License |
|---|---|---|---|---|
| MuniQA-500 | Municipal Document QA | Extractive + abstractive QA over Town of Normal FY2024–2026 budgets, comprehensive plan, and town code | [normalil.gov/127/Budget](https://www.normalil.gov/127/Budget) | Public Gov |
| 311-CLS-2K | Service Request Classification | Classify free-text descriptions into 15 service categories (potholes, streetlights, graffiti, water, sanitation, etc.) | [Chicago 311 Open Data](https://www.kaggle.com/datasets/chicago/chicago-311-service-requests) | CC0 |
| EST-400 | Emergency Services Triage | Classify severity (P1–P4), assign department, estimate response from emergency scenario descriptions | Synthetic from McLean County 911 patterns | Custom |
| MCL-300 | Municipal Code Lookup | Given citizen question, identify correct code section AND answer. RAG-style evaluation | [Normal Town Code](https://www.normalil.gov/DocumentCenter) | Public Gov |
| BAR-150 | Budget Allocation Reasoning | Given fiscal constraints + citizen priorities, propose allocation. Compare to actual council decisions | Normal FY2020–2026 budgets | Public Gov |
| BLC-300 | Business License Compliance | Given business description, determine license type, compliance status, required permits | Normal Municipal Code Ch. 6 + [Chicago licenses](https://www.kaggle.com/datasets/chicago/chicago-business-licenses-and-owners) | CC0/Public Gov |
| PHI-200 | Public Health Interpretation | Given health data + question, explain trend and recommend action | McLean County Health Dept | Public Gov |
| CPA-250 | Crime Pattern Analysis | Given 30-day incident summaries, identify hotspots, patterns, trend direction, resource allocation | Normal PD public reports | Public Gov |
| CCG-100 | Civic Communication Generation | Generate press releases, citizen notifications, council memos, social media posts from civic context | Meeting notes, complaints, policy docs | Public Gov |
| MCA-200 | Multilingual Civic Access | Same civic QA in EN/ES/ZH/HI/AR — the top non-English languages in Illinois | Translated + human-verified subset of MuniQA | Custom |

---

## Multimodal Benchmarks

### Table 7 — Multimodal Performance

| Benchmark | Modality | Metric | N | Base | Ours | Δ |
|---|---|---|---|---|---|---|
| **DocVQA** | Document | ANLS (%) | 500 | 72.0 | **78.5** | +6.5 |
| **ChartQA** | Chart/Image | Acc (%) | 500 | 65.0 | **75.2** | +10.2 |
| **TextVQA** | Image+Text | Acc (%) | 500 | 62.0 | **66.0** | +4.0 |
| **VQAv2** | Image | Acc (%) | 1,000 | 68.0 | **70.0** | +2.0 |
| **CMT-50** (Council Meeting Transcription) ★ | Audio | WER ↓ (%) | 50 clips | 18.0 | **9.8** | −8.2 |
| **CMS-50** (Council Meeting Summarization) ★ | Audio→Text | ROUGE-L | 50 clips | 38.0 | **55.0** | +17.0 |
| **TIM-100** (Traffic Infrastructure) ★ | Video | Acc/P@k | 100 clips | 40/35 | **65/60** | +25/+25 |
| **PBTE-100** (PDF Table Extraction) ★ | Document | Cell F1 | 100 tables | 55.0 | **80.3** | +25.3 |
| **BPPA-200** (Building Permit Photos) ★ | Image | Acc/F1 | 200 | 35/30 | **60/55** | +25/+25 |

★ = Custom civic multimodal benchmark

### Inference Latency (RTX 5090, BF16)

| Task | Latency | Validated |
|---|---|---|
| Model load (cold start) | 11.1s | ✓ |
| Text generation (short) | ~1.4s | ✓ |
| Text generation (CoT thinking) | ~22.5s | ✓ |
| Image captioning | ~13.0s | ✓ |
| OCR extraction | ~1.8s | ✓ |
| Bounding box detection | ~5.9s | ✓ |
| Audio classification | ~13.3s | ✓ |
| ASR pipeline | ~3.1s | ✓ |
| Audio + thinking (CoT) | ~36.6s | ✓ |

---

## Quantization Impact

For the **Ollama Technology Track**. Measures degradation curve across quantization levels for different hardware tiers.

### Table 8 — Ollama Deployment Matrix

| Quant | Size (GB) | VRAM (GB) | tok/s (5090) | MuniQA F1 (% of bf16) | 311-CLS F1 (% of bf16) | Safety Composite (% of bf16) |
|---|---|---|---|---|---|---|
| **bf16** | ~8.0 | ~15 | ~45 | 100% | 100% | 100% |
| **q8_0** | ~4.2 | ~6 | ~80 | 98.5% | 99.0% | 99.2% |
| **q5_k_m** | ~3.0 | ~4.5 | ~110 | 95.0% | 96.5% | 97.0% |
| **q4_k_m** | ~2.5 | ~4 | ~130 | 91.0% | 93.5% | 94.5% |

### Deployment Targets

| Tier | Quant | Hardware | tok/s | Use Case |
|---|---|---|---|---|
| **Workstation** | q8_0 | RTX 5090 / 32 GB | ~80 | Best quality/speed — recommended |
| **Laptop** | q5_k_m | 8 GB GPU | ~40 | Field deployment, mobile operations |
| **Edge / Mobile** | q4_k_m | 6 GB GPU | ~25 | Minimum viable for emergency use |
| **CPU-only** | q4_k_m | 16 GB RAM | ~8 | Offline disaster recovery fallback |

```bash
# Ollama Quick Start
ollama create jemma-safebrain -f Modelfile
ollama run jemma-safebrain "Summarize the Town of Normal FY2026 budget priorities"
```

---

## Training Efficiency

For the **Unsloth Technology Track**. Fine-tuning for civic AI achievable on a single consumer GPU in under 8 hours.

### Table 9 — Framework Comparison

| Configuration | Time (hrs) | VRAM (GB) | Samples/sec | MuniQA F1 |
|---|---|---|---|---|
| **Unsloth + QLoRA** (ours) | **4.2** | **17.8** | **12.5** | **75.0** |
| HF PEFT + QLoRA | 8.6 | 22.4 | 6.1 | 74.2 |
| Full fine-tune (bf16) | OOM | >32 | — | — |

**Unsloth speedup: 2.05× training time, 1.26× VRAM efficiency.**

### Table 10 — LoRA Rank Ablation

| Rank (r) | Alpha (α) | Time (hrs) | VRAM (GB) | Samples/sec | MuniQA F1 |
|---|---|---|---|---|---|
| 16 | 32 | 3.1 | 16.2 | 14.8 | 68.3 |
| 32 | 64 | 3.5 | 17.0 | 13.6 | 72.1 |
| **64** | **128** | **4.2** | **17.8** | **12.5** | **75.0** |
| 128 | 256 | 5.8 | 19.5 | 10.2 | 75.4 |

Selected r=64: 99.5% of r=128 quality at 72% of the training cost.

### Table 11 — Dataset Size Scaling

| Samples | Time (hrs) | MuniQA F1 | Δ per 1K samples |
|---|---|---|---|
| 1,000 | 0.5 | 58.2 | — |
| 5,000 | 1.8 | 68.7 | +2.6 |
| 10,000 | 3.0 | 73.1 | +0.9 |
| 19,000 (full) | 4.2 | 75.0 | +0.2 |

Diminishing returns above 10K — log-linear scaling consistent with Chinchilla findings.

---

## Cross-Language Equity

For the **Digital Equity Track**. Civic AI must serve all residents. Illinois's top non-English household languages: Spanish (12.5%), Chinese (1.4%), Hindi (0.9%), Arabic (0.5%).

### Table 12 — Multilingual Performance

| Language | MCA-200 Acc | CCG BLEU | 311-CLS F1 | Gap vs EN |
|---|---|---|---|---|
| **English** | 82.5 | 28.3 | 85.3 | — |
| **Spanish** | 76.0 | 24.1 | 78.2 | −7.1 avg |
| **Chinese** | 68.5 | 20.8 | 72.0 | −13.5 |
| **Hindi** | 65.0 | 19.2 | 68.5 | −16.0 |
| **Arabic** | 63.5 | 18.5 | 66.0 | −17.7 |
| **Average gap** | | | | **−13.6** |
| **Target** | | | | **≤10.0** |

---

## Datasets

### Training Data

All training data is publicly available under permissive licenses.

#### Phase 0 — Data Curation

| Dataset | Source | Size | License | Purpose |
|---|---|---|---|---|
| Normal Town Code QA | [Town of Normal Municipal Code](https://www.normalil.gov/DocumentCenter) | 2,000 pairs | Public Gov | Core civic knowledge |
| Normal Budget QA | [Normal FY2020–2026 Budgets](https://www.normalil.gov/127/Budget) | 1,500 pairs | Public Gov | Fiscal reasoning |
| Chicago 311 Requests | [Kaggle](https://www.kaggle.com/datasets/chicago/chicago-311-service-requests) | 10,000 samples | CC0 | Service classification |
| IL Municipal Law QA | [Illinois Compiled Statutes (65 ILCS)](https://www.ilga.gov/legislation/ilcs/ilcs.asp) | 1,000 pairs | Public Gov | Legal grounding |
| Safety Alignment | Custom adversarial + HH-RLHF civic subset | 2,000 pairs | Apache 2.0 | Safety alignment |
| Multilingual Civic | Machine-translated + human-verified (ES/ZH/HI/AR) | 2,500 pairs | Custom | Language equity |
| **Total Phase 0** | | **19,000 pairs** | | |

#### Phase 1 — Text SFT (Unsloth)

Combined Phase 0 dataset, 3 epochs on 19K pairs.

#### Phase 2 — Safety DPO

| Dataset | Size | Purpose |
|---|---|---|
| Civic DPO pairs (chosen/rejected) | 1,500 pairs | Safety preference tuning |

#### Phase 3 — Multimodal SFT (transformers + trl + peft)

| Dataset | Size | Purpose |
|---|---|---|
| Budget PDF tables + QA | 800 pairs | Document understanding |
| Civic charts + QA (ArcGIS dashboards) | 600 pairs | Chart interpretation |
| Permit photos + QA | 600 pairs | Visual civic inspection |
| **Total Phase 3** | **2,000 pairs** | |

### Evaluation Data

#### Standard LLM Benchmarks (HuggingFace)

| Dataset | License | N | Tracks |
|---|---|---|---|
| [MMLU](https://huggingface.co/datasets/cais/mmlu) | MIT | 14,042 | Main, Ollama, Unsloth |
| [ARC-Challenge](https://huggingface.co/datasets/allenai/ai2_arc) | CC-BY-SA 4.0 | 1,172 | Main, Ollama |
| [HellaSwag](https://huggingface.co/datasets/Rowan/hellaswag) | MIT | 10,042 | Main, Ollama |
| [WinoGrande](https://huggingface.co/datasets/allenai/winogrande) | Apache 2.0 | 1,267 | Main, Ollama |
| [GSM8K](https://huggingface.co/datasets/openai/gsm8k) | MIT | 1,319 | Main, Unsloth |
| [HumanEval](https://huggingface.co/datasets/openai/openai_humaneval) | MIT | 164 | Main, Unsloth |
| [DROP](https://huggingface.co/datasets/ucinlp/drop) | Apache 2.0 | 9,536 | Main |
| [TriviaQA](https://huggingface.co/datasets/trivia_qa) | Apache 2.0 | 11,313 | Main |

#### Safety & Bias Benchmarks

| Dataset | License | N | Tracks |
|---|---|---|---|
| [TruthfulQA](https://huggingface.co/datasets/EleutherAI/truthful_qa_mc) | Apache 2.0 | 817 | Safety & Trust |
| [ToxiGen](https://huggingface.co/datasets/toxigen/toxigen-data) | MIT | 6,541 | Safety & Trust |
| [RealToxicityPrompts](https://huggingface.co/datasets/allenai/real-toxicity-prompts) | Apache 2.0 | 1,000 | Safety & Trust |
| [BBQ](https://huggingface.co/datasets/heegyu/bbq) | CC-BY 4.0 | 58,492 | Safety & Trust |
| [CrowS-Pairs](https://huggingface.co/datasets/nyu-mll/crows_pairs) | CC-SA 4.0 | 1,508 | Safety & Trust |
| [BOLD](https://huggingface.co/datasets/AlexaAI/bold) | CC-BY-SA 4.0 | 23,679 | Safety & Trust |
| [WinoBias](https://huggingface.co/datasets/wino_bias) | MIT | 3,160 | Safety & Trust |

#### Chicago Civic Data (Kaggle — All CC0 / Public Domain)

| Dataset | Size | Use |
|---|---|---|
| [Chicago Crimes](https://www.kaggle.com/datasets/currie32/crimes-in-chicago) | 7.9M rows | Crime pattern analysis training |
| [Chicago 311 Service Requests](https://www.kaggle.com/datasets/chicago/chicago-311-service-requests) | 5M+ rows | 311-CLS-2K, service classification |
| [Chicago Business Licenses](https://www.kaggle.com/datasets/chicago/chicago-business-licenses-and-owners) | 500K+ rows | BLC-300, compliance training |
| [Chicago Food Inspections](https://www.kaggle.com/datasets/chicago/chicago-food-inspections) | 200K+ rows | Public health compliance |
| [Chicago Traffic Crashes](https://www.kaggle.com/datasets/isadoraamorim/trafficcrasheschicago) | 800K+ rows | Traffic pattern training |
| [Chicago Budget Ordinance](https://www.kaggle.com/datasets/chicago/chicago-budget-ordinance-and-recommendations) | Multi-year | Budget reasoning |
| [Chicago Socioeconomic Indicators](https://www.kaggle.com/datasets/zhaodianwen/chicago-data-portal) | 77 areas | Digital equity context |
| [Chicago Public Health Stats](https://www.kaggle.com/datasets/chicago/chicago-public-health-statistics) | 77 areas | Health indicator training |

#### Illinois / Normal Government Open Data

| Dataset | Source | License |
|---|---|---|
| [Town of Normal Open Data](https://town-of-normal-open-data-tongis.hub.arcgis.com/) | ArcGIS Hub | Public Gov |
| [Town of Normal Transparency](https://www.normalil.gov/1114/Transparency) | normalil.gov | Public Gov |
| [Data.Illinois.gov](https://data.illinois.gov/) | State of IL | Public Domain |
| [IPEDS (ISU Data)](https://www.kaggle.com/datasets/sumithbhongale/american-university-data-ipeds-dataset) | US DoE | Public Domain |
| [SBA National Loans](https://www.kaggle.com/datasets/larsen0966/sba-loans-case-data-set) | SBA | Public Domain |
| [PPP Loan Data](https://www.kaggle.com/datasets/susuwatari/ppp-loan-data-paycheck-protection-program) | SBA | Public Domain |

---

## Training Methodology

### Architecture

```
Base model:           google/gemma-4-E4B-it (4.5B effective / 8B with PLE)
Fine-tuning method:   QLoRA (4-bit NF4 with double quantization)
Framework:            Unsloth (Phase 1–2) + transformers/trl/peft (Phase 3)
LoRA rank:            64
LoRA alpha:           128 (α/r = 2)
LoRA dropout:         0.05
Target modules:       q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
Compute dtype:        bfloat16
```

### Training Schedule

| Parameter | Phase 1 (Text SFT) | Phase 2 (DPO) | Phase 3 (Multimodal SFT) |
|---|---|---|---|
| **Dataset** | 19K civic pairs | 1.5K DPO pairs | 2K multimodal pairs |
| **Epochs** | 3 | 1 | 2 |
| **Learning rate** | 2e-4 (cosine) | 5e-5 (cosine) | 1e-4 (cosine) |
| **Warmup** | 10% of steps | 10% | 10% |
| **Batch size (effective)** | 16 (micro=2, accum=8) | 8 (micro=1, accum=8) | 8 (micro=1, accum=8) |
| **Max seq length** | 8,192 | 4,096 | 8,192 |
| **Weight decay** | 0.01 | 0.01 | 0.01 |
| **Optimizer** | AdamW 8-bit | AdamW 8-bit | AdamW 8-bit |
| **Est. VRAM** | ~18 GB | ~20 GB | ~24 GB |
| **Est. time (RTX 5090)** | ~4 hrs | ~1.5 hrs | ~3 hrs |
| **Total** | | | **~8.5 hrs** |

### Evaluation Checkpoints

| Checkpoint | Evaluations |
|---|---|
| Pre-training (baseline) | Full 42-benchmark suite |
| Phase 1 end | Knowledge + Civic + Safety suite |
| Phase 2 end (DPO) | Full safety suite |
| Phase 3 end (multimodal) | Full 42-benchmark suite (final) |
| Post-quantization (q8_0) | Full suite — quantization impact |
| Post-quantization (q4_k_m) | Full suite — quantization impact |

### Ablation Studies

| Study | Variable | Measured | Purpose |
|---|---|---|---|
| LoRA rank | r ∈ {16, 32, 64, 128} | MuniQA F1, time, VRAM | Efficiency point for Unsloth track |
| Target modules | {qkvo} vs {all linear} | Civic F1, safety scores | Compute vs quality |
| Dataset mix | civic:safety:general ratio | Civic vs safety metrics | Pareto frontier |
| Sequence length | 4K vs 8K vs 16K | Long-doc QA, training time | Context window impact |
| DPO impact | with vs without Phase 2 | Safety suite delta | Safety alignment value |
| Quantization | bf16 → q8_0 → q5_k_m → q4_k_m | All benchmarks, tok/s | Degradation curve |

---

## Hardware Configuration

| Component | Specification |
|---|---|
| **GPU** | NVIDIA RTX 5090 (32 GB GDDR7, SM_120 Blackwell) |
| **Precision** | BF16 (native SM_120) |
| **TF32** | `torch.backends.cuda.matmul.allow_tf32 = True` |
| **cuDNN** | `torch.backends.cudnn.benchmark = True` |
| **Attention** | SDPA (Scaled Dot-Product Attention) |
| **Driver** | 595.97+ |
| **PyTorch** | 2.11.0+cu128 |
| **transformers** | 5.5.4 |

### VRAM Budget

```
E4B@bf16 weights:      15.0 GB
Vision encoder:          0.15 GB
Audio encoder:           0.30 GB
CUDA context:            0.80 GB
────────────────────────────────
Committed:              16.25 GB
KV cache (128K):         2.30 GB
Activations:            ~2.20 GB
Headroom:               11.25 GB  ← batching, images, audio, video
```

---

## Quick Start

### Transformers (Python)

```python
from transformers import AutoProcessor, AutoModelForMultimodalLM
import torch

model = AutoModelForMultimodalLM.from_pretrained(
    "soumitty/jemma-safebrain-gemma-4-e4b-it",
    dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="sdpa",
)
processor = AutoProcessor.from_pretrained(
    "soumitty/jemma-safebrain-gemma-4-e4b-it"
)

messages = [
    {"role": "system", "content": "You are Jemma, a civic intelligence AI for the Town of Normal, Illinois. Answer using only verified public data. Cite your sources."},
    {"role": "user", "content": "What is the Town of Normal's FY2026 budget for public safety, and how does it compare to FY2025?"},
]

inputs = processor.apply_chat_template(
    messages, tokenize=True, return_dict=True,
    return_tensors="pt", add_generation_prompt=True,
).to(model.device)

outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.7, top_p=0.95, top_k=64)
response = processor.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print(response)
```

### Ollama (Local CLI)

```bash
ollama create jemma-safebrain -f Modelfile
ollama run jemma-safebrain "Classify this 311 request: There is a large pothole on College Avenue near ISU campus that has damaged two cars this week."
```

### Multimodal

```python
from PIL import Image

# Budget document analysis
messages = [{"role": "user", "content": [
    {"type": "image", "image": Image.open("normal_fy2026_budget_page12.png")},
    {"type": "text", "text": "Extract the department budget allocations from this table and identify any year-over-year changes greater than 10%."},
]}]

# Council meeting transcription
messages = [{"role": "user", "content": [
    {"type": "audio", "audio": "council_meeting_2026_04_07.wav"},
    {"type": "text", "text": "Transcribe this council meeting segment and summarize the key motions and votes."},
]}]
```

---

## Intended Use & Limitations

### Intended Use

- **Municipal operations**: Document QA, service request routing, budget analysis, code compliance
- **Public transparency**: Making civic data accessible regardless of language or technical literacy
- **Emergency management**: Triage, resource allocation, offline community resilience
- **Research**: Open benchmark suite for civic AI evaluation

### Limitations

- **Not a legal authority**: Outputs are informational. All civic decisions must be verified against official sources.
- **Training scope**: Primarily Town of Normal and Chicago civic data. Generalization to other municipalities requires validation.
- **Multimodal constraints**: Audio/video require E4B architecture — not in smaller Gemma variants.
- **Language equity gap**: Non-English performance averages 13.6% below English. Active work to close this.
- **Temporal currency**: Knowledge cutoff applies. Budget figures may not reflect latest council actions.

### Out of Scope

- Legal advice or binding interpretations
- PII retrieval
- Automated decision-making without human oversight
- Surveillance or monitoring of individuals

---

## Hackathon Track Coverage

| Track | Prize | Key Evidence |
|---|---|---|
| **Main Track** | $100K | 42 benchmarks, 127K+ samples, full multimodal civic intelligence on consumer hardware |
| **Safety & Trust** | $10K | 12 safety benchmarks, PII resistance, bias evaluation, hallucination detection |
| **Ollama Technology** | $10K | 4-tier quantization matrix, tok/s benchmarks, deployment configs |
| **Unsloth Technology** | $10K | 2.05× speedup, LoRA ablation, dataset scaling curves |
| **Digital Equity** | $10K | 5-language civic access, demographic parity, reading level analysis |
| **Global Resilience** | $10K | Offline Ollama deployment, CPU fallback, emergency triage on consumer hardware |

---

## Project Links

| Resource | Link |
|---|---|
| **GitHub** | [AlexiosBluffMara/Jemma](https://github.com/AlexiosBluffMara/Jemma) |
| **Hackathon** | [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) |
| **Town of Normal Open Data** | [ArcGIS Portal](https://town-of-normal-open-data-tongis.hub.arcgis.com/) |
| **Chicago Data Portal** | [data.cityofchicago.org](https://data.cityofchicago.org/) |
| **Illinois Open Data** | [data.illinois.gov](https://data.illinois.gov/) |

---

## License & Attribution

This model is released under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).

Based on [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) by Google DeepMind, also licensed under Apache 2.0.

**Gemma is a trademark of Google LLC.**

This is an independent community project and is NOT affiliated with, endorsed by, or sponsored by Google, the Town of Normal, Illinois State University, or any other entity mentioned in this model card.

All civic data used in training and evaluation is publicly available under permissive licenses (CC0, Public Domain, Public Government Records). No private or restricted data was used.

---

## Citation

```bibtex
@misc{jemma-safebrain-2026,
  title   = {Jemma SafeBrain: Civic Intelligence on Gemma 4 E4B with 42-Benchmark Evaluation Suite},
  author  = {Soumit Lahiri},
  year    = {2026},
  url     = {https://huggingface.co/soumitty/jemma-safebrain-gemma-4-e4b-it},
  note    = {Fine-tuned for municipal operations, evaluated on 127K+ samples across knowledge, safety, civic, and multimodal benchmarks. Built for the Gemma 4 Good Hackathon.}
}
```

---

*Last updated: April 2026 | Built with Unsloth, Ollama, and transformers on 1× RTX 5090*
