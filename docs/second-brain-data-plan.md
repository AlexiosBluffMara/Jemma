# Licensed Kaggle-only Second Brain plan

## Decision
The best win-oriented direction is **not** a generic offline NotebookLM clone. The strongest rules-safe version is:

## **Jemma SafeBrain**
An **offline, Gemma-4-powered second brain for construction and industrial safety** that can:

- ingest PDFs, manuals, incident reports, and notes,
- answer grounded questions with citations,
- summarize long documents into action items,
- generate risk assessments in a structured format,
- inspect construction images for PPE and obvious safety issues,
- run locally with Gemma 4 + Ollama + Unsloth.

This gives a clearer story, stronger impact, and a better shot at the **Main Track**, **Safety & Trust**, **Global Resilience**, **Ollama**, and **Unsloth**-style prize angles than a broad “does everything” assistant.

## Core principle
Use **fine-tuning only for narrow behaviors** that the base model plus RAG will not reliably do on its own:

1. grounded, citation-heavy answers,
2. structured safety/risk outputs,
3. retrieval-aware responses over injected context.

Do **not** waste training budget on generic summarization, generic chat, or generic document QA. Gemma 4 already does those well enough; use retrieval and prompting there.

## Tight dataset collection
These are the recommended **licensed Kaggle datasets only**, with their exact role in the system.

| Priority | Dataset | Kaggle slug | License | Purpose | Use in project | Why it helps you win |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Industrial Safety & Health Analytics | `ihmstefanini/industrial-safety-and-health-analytics-database` | CC0 | safety-domain grounding | **Primary SFT source** plus a small retrieval corpus | Gives you a real-world, high-impact domain and lets you train domain-specific responses instead of a generic chatbot |
| 2 | Stanford Question Answering Dataset (SQuAD) | `stanfordu/stanford-question-answering-dataset` | CC BY-SA 4.0 | grounded QA benchmark | **Eval only** | Lets you report measurable grounded QA quality instead of making vague claims |
| 3 | CNN/DailyMail summarization | `gowrishankarp/newspaper-text-summarization-cnn-dailymail` | CC0 | summarization benchmark | **Eval and demo content**, not SFT | Shows that your offline system can summarize long inputs well, which is central to a NotebookLM-like pitch |
| 4 | Construction Site Safety Image Dataset | `snehilsanyal/construction-site-safety-image-dataset-roboflow` | CC BY 4.0 | construction safety vision demo | **Demo and optional vision evaluation** | Gives the video pitch a strong visual “wow” moment with site-safety analysis |
| 5 | Safety Helmet Detection | `andrewmvd/hard-hat-detection` | CC0 | PPE detection demo support | **Demo support**, not text SFT | Strengthens the safety story and gives you more robust PPE examples for screenshots/video |
| 6 | arXiv Metadata | `Cornell-University/arxiv` | CC0 | large document-library prototype | **RAG corpus prototype**, not SFT | Proves the product can scale to large offline knowledge libraries and supports a “PDF brain” narrative |
| 7 | Human Conversation Training Data | `projjal1/human-conversation-training-data` | CC0 | optional response-style polish | **Optional tiny SFT supplement** | Low priority fallback if you want to lightly tune tone, but it should not drive the project |

## Exact purpose of each dataset

### 1. Industrial Safety & Health Analytics
**What it is for**
- the main **fine-tuning source**
- a small domain retrieval corpus
- structured risk-assessment examples

**How to use it**
- turn each incident row into several instruction examples:
  - summarize the incident,
  - identify likely root cause,
  - assign a risk level,
  - recommend corrective action,
  - answer a question using the incident text as cited context

**Why it matters**
- this is the dataset that actually gives Gemma a domain specialization
- it makes the demo feel like a real safety assistant rather than a general-purpose LLM
- it directly supports a strong high-impact story for judging

**Use with Unsloth**
- yes, this is the best dataset in the shortlist for **actual LoRA fine-tuning**

### 2. SQuAD
**What it is for**
- grounded question-answering evaluation

**How to use it**
- run retrieval-style QA evaluations
- report metrics in the writeup

**Why it matters**
- judges trust measurable results more than generic claims
- it proves that the system answers from source context rather than hallucinating

**Use with Unsloth**
- **no**
- use it for evaluation only

### 3. CNN/DailyMail
**What it is for**
- summarization evaluation
- long-document demo content

**How to use it**
- benchmark summaries
- show a “turn large source material into concise briefings” workflow
- use sample articles as stand-ins while the PDF ingestion flow is still being built

**Why it matters**
- the NotebookLM-style pitch depends heavily on summarization quality
- this gives you a clean benchmark and demo material quickly

**Use with Unsloth**
- **no**
- Gemma 4 already summarizes well; use this as eval/demo data

### 4. Construction Site Safety Image Dataset
**What it is for**
- image-based construction hazard and PPE demo

**How to use it**
- show Gemma analyzing job-site images
- pair image observations with text output like:
  - missing helmet,
  - unsafe area,
  - suggested follow-up action

**Why it matters**
- it gives your project a memorable visual differentiator
- it makes the pitch feel broader than “offline PDF chatbot”

**Use with Unsloth**
- usually **not** for this first pass
- use it in the demo and evaluation pipeline first

### 5. Safety Helmet Detection
**What it is for**
- extra PPE-focused visual examples

**How to use it**
- support the construction image demo
- create stronger video and screenshot artifacts

**Why it matters**
- improves storytelling and confidence in the safety use case

**Use with Unsloth**
- **no** for text fine-tuning

### 6. arXiv Metadata
**What it is for**
- large-scale offline library prototype
- “bring your own document universe” story

**How to use it**
- use as a stand-in large corpus for indexing, retrieval, clustering, and topic exploration
- position it as the scale proof for the PDF-second-brain architecture

**Why it matters**
- shows your system is not limited to a tiny safety database
- supports the “NotebookLM but offline” narrative

**Use with Unsloth**
- **no**
- this is retrieval/indexing data, not SFT data

### 7. Human Conversation Training Data
**What it is for**
- minor conversational cleanup only

**How to use it**
- only if needed for response style polish after domain tuning

**Why it matters**
- low impact compared with the safety domain data

**Use with Unsloth**
- optional, low priority

## What should actually be fine-tuned
Keep the SFT scope tight.

### Fine-tune on
- **Industrial Safety & Health Analytics** transformed into:
  - grounded QA pairs,
  - incident summaries,
  - risk classification outputs,
  - corrective-action recommendations,
  - citation-style answers

### Do not fine-tune on
- SQuAD
- CNN/DailyMail
- construction image datasets
- arXiv metadata

Those should be used for **evaluation, retrieval, and demo content**, not for LoRA training.

## Best product concept

### **Top choice: Jemma SafeBrain**
**Pitch:** an offline second brain for safety-critical work. Feed it manuals, reports, PDFs, and site images; it returns grounded answers, summaries, risk assessments, and safety observations.

### Why this beats the alternatives
- **Construction / engineering** has a stronger impact story than a generic MBA tutor
- **Offline PDF + notes + image reasoning** is closer to a differentiated NotebookLM replacement
- **Safety** gives a better human-centered and socially useful story for hackathon judging
- it aligns naturally with local inference, Unsloth fine-tuning, and a vivid demo

## Backup concepts

### Backup 1: Offline academic paper brain
Use:
- `Cornell-University/arxiv`
- `stanfordu/stanford-question-answering-dataset`
- `gowrishankarp/newspaper-text-summarization-cnn-dailymail`

This is simpler and cleaner, but it is less emotionally compelling and weaker on the visual side.

### Backup 2: Offline teaching and briefing assistant
Use:
- `gowrishankarp/newspaper-text-summarization-cnn-dailymail`
- `stanfordu/stanford-question-answering-dataset`
- `projjal1/human-conversation-training-data`

This can support business or teaching-style demos, but it is much less distinctive and probably less competitive.

## Why MBA/teaching is not the top recommendation
Right now, the strongest **licensed Kaggle-only** path is the construction/safety angle. It has:

- clearer real-world value,
- better demo visuals,
- better alignment with “offline AI that helps people in the field,”
- stronger multi-prize overlap.

An MBA-student tutor can still be built, but it is likely to feel more generic unless you later find a high-quality, clearly licensed Kaggle business-teaching corpus that materially improves the story.

## Exact win-oriented dataset bundle

### Must use
1. `ihmstefanini/industrial-safety-and-health-analytics-database`
2. `stanfordu/stanford-question-answering-dataset`
3. `gowrishankarp/newspaper-text-summarization-cnn-dailymail`
4. `snehilsanyal/construction-site-safety-image-dataset-roboflow`

### Strong add-on
5. `andrewmvd/hard-hat-detection`

### Optional scale demo
6. `Cornell-University/arxiv`

## Compliance filter
Only use Kaggle datasets that have:

- a clearly stated license,
- acceptable attribution requirements,
- no obvious personal-data issues,
- terms consistent with training, retrieval, embeddings, and public demo use.

Maintain a ledger for every chosen dataset with:

- Kaggle URL,
- license,
- attribution requirements,
- whether it is used for **SFT**, **RAG**, **eval**, or **demo only**,
- whether embeddings and public demos are acceptable.

## Exact training recommendation for the current notebook
For `gemma4-31b-unsloth-local-5090.ipynb`, the best first training run is:

1. build a curated JSONL from **Industrial Safety & Health Analytics**,
2. create around **1,000-2,000** high-quality instruction examples,
3. train only on those safety-domain examples,
4. leave summarization and general document QA to the base model plus retrieval,
5. use the other datasets for evaluation and the pitch demo.

That is the tightest, most rules-safe, and most competition-friendly plan from the current licensed Kaggle options.
