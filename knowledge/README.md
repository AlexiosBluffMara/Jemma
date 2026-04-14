# Jemma Knowledge Base

This directory contains curated markdown knowledge documents that feed into Jemma's GraphRAG system.

## Structure

- `civic/` — Town of Normal, ISU, Chicago civic data summaries
- `models/` — Gemma 4 model specifications, benchmarks, capabilities
- `safety/` — Safety policies, refusal guidelines, threat models
- `hardware/` — GPU specs, cost analysis, deployment configurations
- `techniques/` — QLoRA, RAG, GraphRAG, MoE, KV cache techniques

## Usage

```bash
# Build GraphRAG index from these files
python pipeline/graphrag.py build

# Query the knowledge base
python pipeline/graphrag.py query "What is E4B's VRAM requirement?"
```
