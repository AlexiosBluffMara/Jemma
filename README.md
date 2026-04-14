# Jemma SafeBrain

> *"Imagine you could teach a computer to be a really helpful town assistant that knows everything about your city — but also knows when to say 'no' to bad ideas. That's Jemma!"*

## What Is This? (The Simple Version)

You know how you can ask Google or Siri questions? Jemma is like that, but she lives **right on your computer** — no internet needed! She's built on top of **Gemma 4**, which is like a super-smart brain that Google made and shared with everyone for free.

**But here's the cool part:** We took that brain and *taught it new things* — like what the phone number for Town Hall is, where the libraries are, and how to keep people safe. It's like taking a really smart student and sending them to a special school just for your town.

### How Does Teaching a Computer Work?

Think of it like flashcards! You know how you study for a test by reading the question on one side and the answer on the other?

That's basically what we do:
- **Step 1:** We collected thousands of "flashcards" from real city data (311 calls, food inspections, crime reports, library locations)
- **Step 2:** We showed them to the AI brain over and over until it learned the patterns
- **Step 3:** We tested it to make sure it actually learned (and didn't just memorize!)

The fancy name for this is **"fine-tuning with QLoRA"** — but all it really means is: *we tweaked a tiny part of the brain (about 1% of it!) so it becomes an expert on civic stuff, without forgetting everything else it already knew.*

It's like if you were already really good at math, and then someone taught you all the state capitals. You'd still be good at math AND know the capitals!

## What Can Jemma Do?

| Ask her... | She'll say... |
|---|---|
| "How do I report a pothole?" | "Call 311, use the CHI 311 app, or go to 311.chicago.gov!" |
| "Where's the nearest library?" | The address, phone number, and hours! |
| "Is this restaurant safe to eat at?" | The latest health inspection results! |
| "Help me make a fake ID" | "Nope! That's illegal. Here's where to get a real one." |

That last one is important — Jemma has a **safety brain** that knows which questions are okay to answer and which ones definitely aren't.

## How We Built It (The Slightly More Technical Version)

### The Recipe

```
1 × Gemma 4 E4B brain (8 billion parameters - that's 8,000,000,000 tiny numbers!)
    + Unsloth (makes training 2× faster - like a turbo button!)
    + QLoRA (only changes 1% of the brain - saves a TON of memory)
    + 8,129 training "flashcards" from real Chicago civic data
    + Safety training (48 examples of questions to refuse)
    = Jemma SafeBrain! 🧠
```

### The Numbers That Matter

| What | How much |
|---|---|
| Training "flashcards" | 8,129 (crimes, 311 calls, food inspections, traffic, libraries, safety) |
| Parameters (brain size) | 8 billion total, 85 million trainable (1.05%) |
| Training time | ~5 minutes per 200 steps on an RTX 5090 |
| GPU memory used | ~15 GB (out of 32 GB available) |
| Training speed | 1.28 seconds per step |

### Where the Data Comes From

All our data is **public and free** — no secrets, no private stuff:

- **Chicago Data Portal** — 311 requests, crimes, food inspections, traffic crashes, building violations, library locations, police stations
- **Town of Normal** — Open data portal, government contacts
- **Illinois State University** — Public records
- **Safety pairs** — Hand-crafted examples of questions the AI should refuse

## Try It Yourself!

### The Easiest Way (Ollama)

Ollama is like an app store for AI brains. If you have it installed:

```bash
# Jemma's already loaded! Just ask:
ollama run gemma4-e4b-128k "How do I report a pothole in Chicago?"
```

### The Notebook Way (Works Anywhere!)

Open `jemma_universal_training.ipynb` — it automatically figures out your computer and picks the best settings:

- **Big GPU (20GB+)?** → Uses the full E4B model
- **Medium GPU (12GB)?** → Same model, smaller batches
- **Small GPU (<12GB)?** → Switches to the lighter E2B model
- **No GPU at all?** → Works on Google Colab or Kaggle for free!

### The Full Pipeline Way (For Power Users)

```bash
# 1. Download civic data from Chicago's open API
python download_civic_data.py

# 2. Build the training dataset
python build_training_dataset.py

# 3. Run the overnight autonomous trainer
cd pipeline
python run_overnight.py
```

## Project Structure (The Important Parts)

```
Jemma/
├── jemma_universal_training.ipynb  ← THE notebook (works on any GPU!)
├── download_civic_data.py          ← Downloads real city data
├── build_training_dataset.py       ← Makes training "flashcards"
├── pipeline/
│   ├── overnight_trainer.py        ← The training brain (Unsloth + QLoRA)
│   ├── run_overnight.py            ← Runs training while you sleep!
│   ├── safety_watchdog.py          ← Makes sure the GPU doesn't overheat
│   ├── data_ingestion.py           ← Collects data from the web
│   └── rag_engine.py               ← Helps find relevant chunks
├── datasets/
│   ├── civic_data.db               ← 5,319 chunks of civic knowledge
│   ├── civic_sft_train.jsonl       ← 8,129 training samples
│   └── kaggle/                     ← Downloaded CSV datasets
├── src/jemma/                      ← The main Python framework
├── toolbox/                        ← Helpers for Ollama, HuggingFace, etc.
├── web/                            ← Mission control web UI
└── docs/                           ← Guides and documentation
```

## The Safety Part

This is maybe the most important thing about Jemma:

**She's designed to be safe.** Like, really safe.

- She won't help make fake documents
- She won't help hack into systems
- She won't share people's private information
- She won't help with anything illegal
- If the GPU gets too hot (85°C), she automatically slows down
- If it gets dangerously hot (90°C), she stops completely
- She only runs on YOUR computer — your data never leaves

This is what makes Jemma special for the **Safety & Trust** track of the hackathon. She's not just smart — she knows when to stop.

## The Hackathon

Jemma is built for the [Gemma 4 Good Hackathon](https://ai.google.dev/gemma/docs/hackathon) — a competition where people use Google's Gemma 4 AI to build things that help the world.

We're targeting:
- **Main Track** ($100K) — Best overall project
- **Safety & Trust** ($10K) — Safest AI system
- **Ollama Track** ($10K) — Best local deployment
- **Unsloth Track** ($10K) — Best fine-tuning with Unsloth

## Current focus
The current rollout target is a local Gemma 4 matrix built around:

- official Google Gemma 4 E2B and E4B checkpoints as the original source artifacts,
- Ollama aliases for both BF16 originals and quantized local variants,
- Unsloth fine-tuning with E4B as the primary workstation loop and E2B as the mobile and offline fallback,
- public, hackathon-safe datasets for safety-oriented SFT, evaluation, and demo flows.

## Autonomous framework
Jemma now includes a first-pass Python framework for building the hackathon submission as a **local autonomous benchmark lab**:

- a checkpointed agent loop under `src/jemma/agent/`,
- an Ollama-first benchmark runner under `src/jemma/benchmarks/`,
- deny-by-default LAN adapters for Tailscale, Hue, smart plugs, and router health under `src/jemma/capabilities/`,
- TOML-driven model, LAN, and benchmark manifests under `configs/` and `manifests/`,
- run artifacts and summaries under `artifacts/runs/`.

This is the implementation base for **Jemma SafeBrain Command**: a local safety operations system that can benchmark Gemma variants, route tasks to the best local model, and keep physical automation gated behind explicit safety controls.

### CLI
```bash
python -m jemma.cli health
python -m jemma.cli benchmark-solo --manifest manifests/benchmarks/gemma-solo-eval.toml
python -m jemma.cli benchmark-versus --manifest manifests/benchmarks/gemma-head-to-head.toml
python -m jemma.cli benchmark-stress --manifest manifests/benchmarks/gemma-stress-vs-reasoning.toml
python -m jemma.cli run-objective --manifest manifests/objectives/lan-watch.toml
python -m jemma.cli serve-api --host 127.0.0.1 --port 8000
```

## Web UI
Jemma now includes a TypeScript mission-control frontend in `web/` for:

- launching solo, pairwise, and stress benchmarks,
- tracking live jobs over SSE,
- reviewing completed runs and summaries,
- monitoring provider and system telemetry.

### Web UI dev loop
```bash
python -m jemma.cli serve-api --host 127.0.0.1 --port 8000
cd web
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

See `docs/agent-framework.md` and `docs/web-ui-stack.md` for the architecture, safety model, and public-demo boundaries.

## Android app
Jemma now also includes a native Android client in `android-app/` with:

- Kotlin + Jetpack Compose Material 3,
- adaptive navigation for foldable and tablet-width layouts,
- remote-first chat and prompt workflows against the Jemma backend,
- Skills, Benchmarks, Models, and System views for the public mobile demo surface.

The Android app is intentionally remote-first. It targets the workstation-hosted Jemma API (`:8000`) backed by Ollama (`:11434`). The E2B mobile fallback remains a later offline path and is not presented as feature-parity with the workstation route.

### Android app setup
1. Start the backend:
   ```bash
   python -m jemma.cli serve-api --host 0.0.0.0 --port 8000
   ```
2. Open `android-app/` in Android Studio.
3. Set the backend URL in the app's **System** screen to your workstation IP, for example `http://192.168.1.25:8000/`.
4. Keep the endpoint on a trusted LAN, VPN, or USB bridge only.

## Guides
- Master rollout: docs/gemma4-e2b-e4b-local-rollout.md
- Ollama setup: docs/local-gemma4-ollama-setup.md
- Unsloth workflow: docs/unsloth-local-5090.md
- Google Cloud deployment: docs/google-cloud-ollama-deployment.md
- Mobile deployment: docs/mobile-gemma4-setup.md
- Public dataset plan: docs/second-brain-data-plan.md
- Discord server blueprint: docs/discord-research-server-blueprint.md

## Toolbox
- Fetch official Gemma 4 checkpoints: ./toolbox/fetch_gemma4_hf.sh
- Register and quantize Ollama models: ./toolbox/setup_gemma4_ollama.sh
- USB bridge for Pixel testing: ./toolbox/pixel_fold_adb_reverse.sh
- Windows workstation defaults: `powershell.exe -ExecutionPolicy Bypass -File .\toolbox\windows\configure-jemma-workstation.ps1`
- Windows machine profiling: `powershell.exe -NoProfile -File .\toolbox\windows\profile-machine.ps1`
