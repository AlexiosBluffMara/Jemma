---
description: "Generate a Kaggle competition writeup for the Gemma 4 Good Hackathon"
agent: "KaggleCompetitor"
argument-hint: "Which tracks to emphasize (Main, Safety, Ollama, Unsloth, Global Resilience)"
tools: [read, search, web]
---
Generate a competition writeup (≤1,500 words) for the Gemma 4 Good Hackathon submission.

Requirements:
- Title and subtitle that capture the project's impact
- Clear problem statement: what real-world problem Jemma solves
- Technical approach: Gemma 4 model usage, fine-tuning, deployment stack
- Results: benchmark scores, demo capabilities, deployment evidence
- Impact narrative: how this advances safety, trust, and local AI

Evaluation rubric to optimize for:
- Impact & Vision (40 pts): compelling problem + tangible potential
- Video Pitch & Storytelling (30 pts): exciting narrative
- Technical Depth & Execution (30 pts): innovative Gemma 4 usage

References:
- `docs/COMPETITION_STRATEGY.md` for positioning
- `docs/HACKATHON_ASSESSMENT.md` for track alignment
- `docs/BENCHMARK_RESULTS.md` for performance data
- `toolbox/hf_model_card.md` for model details

Target tracks: {{input}}
