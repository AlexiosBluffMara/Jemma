# Jemma — Setup & Launch Guide

**Goal:** Max out free Gemma 4 compute to generate thousands of construction-domain training entries before the free window closes.

---

## 1  What Already Exists (ready to use)

| File | Purpose | Status |
|---|---|---|
| `toolbox/vertex_synth_loop.py` | Main data generation loop ("Ralph Wiggum Loop"). 9 tracks, 122 prompt seeds × 8 variation modes = 976 unique combos. Auto-shutoff before Apr 15 23:00 UTC. | **Ready — needs API key** |
| `toolbox/launch_ralph_wiggum.ps1` | PowerShell launcher with auth instructions | **Ready** |
| `toolbox/merge_synth_data.py` | Merges `datasets/synth/*.jsonl` → single training file, with dedup | **Ready** |
| `datasets/construction-cracks-train.jsonl` | 75 hand-curated expert Q&A entries (seed data) | **Done** |
| `datasets/second-brain-train.jsonl` | 75 entries (mirror of above) | **Done** |
| `datasets/prompts/*.jsonl` | 28 benchmark/safety prompts across 6 files | **Done** |
| `datasets/synth/` | Output directory for generated data | **Empty — waiting for launch** |
| `.venv/` with `google-genai 1.72.0` | Python SDK for Gemini/Gemma API | **Installed** |

---

## 2  What You Need to Get (one API key, takes 2 minutes)

### You need exactly ONE thing: a Google AI API key

| Item | Where to get it | Time |
|---|---|---|
| **Google AI API Key** | https://aistudio.google.com/app/apikey | ~60 seconds |

**Step-by-step:**

1. Open **https://aistudio.google.com/app/apikey** in your browser
2. Sign in with your Google account (any account works)
3. Click **"Create API key"**
4. If prompted, select an existing GCP project OR let it create one for you
5. Copy the key (starts with `AIza...`)
6. Come back here and paste it into this command in your terminal:

```powershell
$env:GOOGLE_API_KEY = "AIzaSy__YOUR_KEY_HERE__"
```

That's it. **No billing setup required. No credit card. No gcloud CLI install.** Gemma 4 is 100% free on the Developer API.

### (Optional) Vertex AI path — only if you want higher rate limits

If you want 3-4x more throughput, you can use Vertex AI instead. This requires more setup:

1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
2. Run: `gcloud auth application-default login`
3. Run: `gcloud config set project YOUR_PROJECT_ID`
4. Set the env var:
   ```powershell
   $env:GOOGLE_CLOUD_PROJECT = "your-project-id"
   ```
5. Make sure the Vertex AI API is enabled in your project Console

**When to use Vertex AI instead:** Only if you're hitting the ~15 RPM / 1,500 RPD ceiling on the free API key path and want to scale up to 60+ RPM.

---

## 3  How to Give the Key to the System

Open any PowerShell terminal in the Jemma project and run:

```powershell
# Set the key for this session
$env:GOOGLE_API_KEY = "AIzaSy__YOUR_KEY_HERE__"

# Verify it's set
echo $env:GOOGLE_API_KEY
```

**To make it permanent** (survives terminal restarts):

```powershell
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "AIzaSy__YOUR_KEY_HERE__", "User")
```

Then restart your terminal.

---

## 4  How to Launch

### Quick start (one command after setting key):

```powershell
$env:GOOGLE_API_KEY = "YOUR_KEY"
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --max-rpm 14
```

### Using the launcher script:

```powershell
$env:GOOGLE_API_KEY = "YOUR_KEY"
.\toolbox\launch_ralph_wiggum.ps1
```

### Dry run (test without API calls):

```powershell
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --dry-run
```

---

## 5  Maximizing Free Usage — All Available Free Lines

Here's every free compute line you can run **simultaneously** to maximize output:

### Line 1: Gemma 4 via API Key (Developer API) — FREE, no expiry

```powershell
# Terminal 1
$env:GOOGLE_API_KEY = "YOUR_KEY"
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --max-rpm 14 --output datasets/synth
```

- **Limits:** ~15 RPM, ~1,500 RPD, ~1M TPM
- **Yield:** ~1,400 entries/day
- **Cost:** $0 forever (Gemma 4 is free-only on Developer API, no paid tier)
- **What it burns:** Gemma 4 26B A4B inference

### Line 2: Gemma 4 via Vertex AI — FREE until Apr 16, 2026

```powershell
# Terminal 2 (only if you set up gcloud)
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --max-rpm 50 --output datasets/synth-vertex --location us-central1
```

- **Limits:** ~60 RPM default, requestable to 300+
- **Yield:** ~43,000-86,000 entries/day
- **Cost:** $0 until Apr 16 2026, then $0.15/M in + $0.60/M out tokens
- **What it burns:** Gemma 4 26B on Vertex AI shared pool

### Line 3: Multiple API keys (separate projects) — FREE

You can create multiple GCP projects, each with its own API key. Rate limits are **per project**, not per account.

```powershell
# Terminal 3 — second API key from a different project
$env:GOOGLE_API_KEY = "YOUR_SECOND_KEY"
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --max-rpm 14 --output datasets/synth-key2
```

To create additional API keys on separate projects:
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Click **"Create API key in new project"** (important — new project = separate quota)
4. You now have an independent 15 RPM / 1,500 RPD quota

### Line 4: Gemini 2.5 Flash-Lite for safety/benchmark data — FREE

The free tier also gives you Gemini 2.5 Flash-Lite at no cost. You could run a parallel loop generating safety benchmark data:

```powershell
# Terminal 4
$env:GOOGLE_API_KEY = "YOUR_KEY"
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --model gemini-2.5-flash-lite --max-rpm 14 --output datasets/synth-flash-lite
```

- Different model = potentially separate rate limit bucket
- Still free on the free tier
- Useful for generating safety/benchmark scenarios instead of just construction data

### Line 5: Local Ollama (E4B/E2B) — FREE, runs on your RTX 5090

Your local GPU can generate data in parallel with zero API costs:

```powershell
# Terminal 5 — uses your local 5090, no cloud calls
# (would need a small wrapper script calling Ollama at 127.0.0.1:11434)
```

This doesn't use the Ralph Wiggum script (which targets the cloud API) but could be a parallel local generation loop hitting your Ollama models.

---

## 6  Optimal Configuration Summary

| Scenario | RPM Setting | Expected Entries/Day | Terminals Needed |
|---|---|---|---|
| **Minimum (1 API key only)** | `--max-rpm 14` | ~1,400 | 1 |
| **Medium (1 API key + Vertex AI)** | 14 + 50 | ~44,400 | 2 |
| **Maximum (2 API keys + Vertex AI + Flash-Lite)** | 14+14+50+14 | ~56,000+ | 4 |
| **Maximum + local Ollama** | above + unlimited local | 56K+ cloud + local | 5 |

### Recommended `--max-rpm` settings

| Auth method | Safe RPM | Why |
|---|---|---|
| API key (free tier) | `14` | Hard limit is ~15 RPM; stay 1 under to avoid wasted 429 retries |
| Vertex AI (default quota) | `50` | Default ~60 RPM; leave headroom |
| Vertex AI (after quota increase) | `250` | Request via GCP Console; approved usually within hours |

---

## 7  After Generation — Merging Data

Once you have data in `datasets/synth/`, merge it:

```powershell
# Check what was generated
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/merge_synth_data.py --stats-only

# Merge into a single clean training file
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/merge_synth_data.py
```

Output goes to `datasets/construction-full-train.jsonl` (original 75 + all synthetic, deduplicated).

---

## 8  Safety Rails (already built in)

- **Auto-shutoff:** Script stops before Apr 15 23:00 UTC (1 day before free period ends)
- **Post-free budget cap:** $50/day max after the free period
- **Rate limiting:** Built-in sleep between requests, backs off 2x on errors
- **Dedup:** SHA-256 content hashing against all existing data
- **No lockout risk:** 429 errors are normal rate-limit responses, not bans. Google's abuse monitoring only flags ToS violations (spam, harmful content), not legitimate data generation.

---

## 9  Quick Reference — Copy-Paste Commands

```powershell
# ── ONE-TIME SETUP ──
$env:GOOGLE_API_KEY = "PASTE_YOUR_KEY_HERE"

# ── DRY RUN (verify everything works) ──
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --dry-run

# ── LAUNCH (leave running) ──
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/vertex_synth_loop.py --max-rpm 14

# ── CHECK PROGRESS (in another terminal) ──
Get-Content datasets/synth/generation_stats.jsonl -Tail 1 | ConvertFrom-Json

# ── COUNT ENTRIES ──
(Get-Content datasets/synth/*.jsonl | Measure-Object -Line).Lines

# ── MERGE WHEN DONE ──
d:/JemmaRepo/Jemma/.venv/Scripts/python.exe toolbox/merge_synth_data.py
```

---

## 10  What's NOT Set Up Yet (and doesn't need to be for this to work)

| Item | Status | Needed? |
|---|---|---|
| gcloud CLI | Not installed | **No** — API key works without it |
| Vertex AI API enabled | Unknown | **No** — only needed for Vertex AI path |
| Billing account | Not linked | **No** — Gemma 4 is free without billing |
| Service account JSON | None | **No** — API key is simpler |
| Local Ollama generation wrapper | Doesn't exist | **Optional** — parallel local generation |
| Unsloth fine-tuning | Template only | **Later** — use generated data for training |

---

**TL;DR:** Get an API key from https://aistudio.google.com/app/apikey, paste it, run the script. Everything else is already built.
