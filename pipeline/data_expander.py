#!/usr/bin/env python3
"""
Jemma Multi-Terminal Data Expander
====================================
Spawns parallel worker processes, each generating training data from
different civic domains using Ollama. Workers coordinate via a shared
queue file to avoid duplicate work.

Architecture:
  Coordinator → Worker 1 (food safety)
              → Worker 2 (building codes)
              → Worker 3 (traffic/transport)
              → Worker 4 (public health)
              → Worker 5 (emergency services)

Each worker generates Q&A pairs, self-scores, and appends to its own
output file. The coordinator merges results periodically.
"""
import json
import logging
import multiprocessing as mp
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger("data_expander")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(levelname)s %(message)s",
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL = "gemma4:e4b"
OUTPUT_DIR = Path("datasets/expanded")
MERGED_OUTPUT = Path("datasets/civic_sft_expanded_multi.jsonl")
MIN_QUALITY = 0.65
PAIRS_PER_WORKER = 30

SYSTEM_PROMPT = (
    "You are Jemma SafeBrain, a civic AI assistant. "
    "Provide accurate, specific answers about civic services, "
    "public safety, and municipal operations."
)

# Domain-specific worker configurations
WORKER_DOMAINS = [
    {
        "name": "food_safety",
        "topics": [
            "restaurant inspection procedures in Chicago",
            "food safety violation categories and penalties",
            "health department inspection frequency",
            "food handler certification requirements",
            "critical vs non-critical food violations",
            "temporary food permit process",
        ],
    },
    {
        "name": "building_codes",
        "topics": [
            "building permit application process",
            "zoning variance requests",
            "residential vs commercial building codes",
            "occupancy certificate requirements",
            "fire safety code compliance",
            "ADA accessibility requirements for buildings",
        ],
    },
    {
        "name": "public_safety",
        "topics": [
            "police non-emergency service requests",
            "crime reporting procedures for citizens",
            "neighborhood watch program setup",
            "traffic incident reporting requirements",
            "domestic violence resource services",
            "community policing strategies",
        ],
    },
    {
        "name": "public_health",
        "topics": [
            "public health clinic services and locations",
            "vaccination program availability",
            "lead testing for residential properties",
            "mental health crisis services",
            "WIC and SNAP benefit applications",
            "environmental health complaints",
        ],
    },
    {
        "name": "infrastructure",
        "topics": [
            "pothole repair request process",
            "street light outage reporting",
            "water main break response",
            "snow removal priority routes",
            "sidewalk repair responsibility",
            "tree trimming service requests",
        ],
    },
]


# ---------------------------------------------------------------------------
# Worker function
# ---------------------------------------------------------------------------
def ollama_chat(messages: list[dict], temperature: float = 0.7,
                max_tokens: int = 768) -> str:
    """Chat with Ollama."""
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def generate_qa_pair(topic: str) -> dict | None:
    """Generate one Q&A pair for a topic."""
    import re

    # Generate question
    q_resp = ollama_chat([
        {"role": "system", "content": "Generate one specific, factual civic question. Output ONLY the question."},
        {"role": "user", "content": f"Generate a specific question about: {topic}"},
    ], temperature=0.9, max_tokens=100)

    question = q_resp.strip()
    if not question or len(question) < 15 or "[ERROR" in question:
        return None

    # Clean formatting
    question = re.sub(r"^\d+[\.\)]\s*", "", question)
    question = question.strip('"\'')

    # Generate answer
    answer = ollama_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ], temperature=0.3, max_tokens=768)

    if not answer or len(answer) < 30 or "[ERROR" in answer:
        return None

    # Score quality
    score_text = ollama_chat([
        {"role": "system", "content": "Rate quality 0.0-1.0. Respond with ONLY a number."},
        {"role": "user", "content": (
            f"Rate this civic Q&A quality (0.0-1.0):\n"
            f"Q: {question}\nA: {answer[:500]}"
        )},
    ], temperature=0.1, max_tokens=10)

    try:
        numbers = re.findall(r"(\d+\.?\d*)", score_text)
        quality = float(numbers[0]) if numbers else 0.5
        quality = max(0.0, min(1.0, quality))
    except (ValueError, IndexError):
        quality = 0.5

    return {
        "question": question,
        "answer": answer,
        "topic": topic,
        "quality": quality,
    }


def worker_process(domain: dict, pairs_per_worker: int, output_dir: str):
    """Worker: generate QA pairs for a single domain."""
    domain_name = domain["name"]
    output_file = Path(output_dir) / f"{domain_name}.jsonl"
    os.makedirs(output_dir, exist_ok=True)

    log.info(f"Worker [{domain_name}] starting — {pairs_per_worker} pairs")
    kept = 0
    generated = 0

    with open(output_file, "a", encoding="utf-8") as f:
        for i in range(pairs_per_worker):
            topic = random.choice(domain["topics"])
            result = generate_qa_pair(topic)
            generated += 1

            if result is None:
                log.warning(f"  [{domain_name}] Q{i+1}: generation failed")
                continue

            if result["quality"] < MIN_QUALITY:
                log.info(f"  [{domain_name}] Q{i+1}: score {result['quality']:.2f} < {MIN_QUALITY} — skipped")
                continue

            sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": result["question"]},
                    {"role": "assistant", "content": result["answer"]},
                ],
                "_meta": {
                    "source": f"data_expander/{domain_name}",
                    "topic": result["topic"],
                    "quality_score": result["quality"],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            kept += 1
            log.info(f"  [{domain_name}] Q{i+1}: ✓ score={result['quality']:.2f}")

    log.info(f"Worker [{domain_name}] done — kept {kept}/{generated}")
    return {"domain": domain_name, "generated": generated, "kept": kept}


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------
def merge_worker_outputs(output_dir: Path, merged_output: Path):
    """Merge all worker output files into one deduped JSONL."""
    seen = set()
    samples = []

    for fn in output_dir.glob("*.jsonl"):
        with open(fn) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    q = next(
                        (m["content"] for m in d.get("messages", []) if m["role"] == "user"),
                        "",
                    )
                    if q and q not in seen:
                        seen.add(q)
                        samples.append(d)
                except json.JSONDecodeError:
                    continue

    with open(merged_output, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    log.info(f"Merged {len(samples)} unique samples → {merged_output}")
    return len(samples)


def run_parallel(num_workers: int = 3, pairs_per_worker: int = PAIRS_PER_WORKER):
    """Run workers in parallel (sequentially on Ollama since it serializes)."""
    # NOTE: Ollama serializes requests, so true parallelism only helps if
    # running multiple Ollama instances. With a single instance, we run
    # workers sequentially but keep the architecture ready for multiple.
    domains = WORKER_DOMAINS[:num_workers]
    results = []

    print(f"\n{'='*70}")
    print(f"Multi-Domain Data Expander")
    print(f"Workers: {num_workers} | Pairs/worker: {pairs_per_worker}")
    print(f"Model: {MODEL} | Min quality: {MIN_QUALITY}")
    print(f"{'='*70}\n")

    t0 = time.time()

    for domain in domains:
        result = worker_process(domain, pairs_per_worker, str(OUTPUT_DIR))
        results.append(result)

    elapsed = time.time() - t0

    # Merge
    total = merge_worker_outputs(OUTPUT_DIR, MERGED_OUTPUT)

    # Summary
    total_gen = sum(r["generated"] for r in results)
    total_kept = sum(r["kept"] for r in results)

    print(f"\n{'='*70}")
    print("Data Expansion Complete")
    print(f"{'='*70}")
    print(f"  Workers: {len(results)}")
    print(f"  Total generated: {total_gen}")
    print(f"  Total kept: {total_kept}")
    print(f"  Merged unique samples: {total}")
    print(f"  Time: {elapsed:.0f}s")
    for r in results:
        print(f"  [{r['domain']}] generated={r['generated']}, kept={r['kept']}")

    return total


def run_truly_parallel(num_workers: int = 3,
                       pairs_per_worker: int = PAIRS_PER_WORKER):
    """
    Run workers using multiprocessing (useful if running multiple Ollama
    instances on different ports or using batched requests).
    """
    domains = WORKER_DOMAINS[:num_workers]

    print(f"\n{'='*70}")
    print(f"Multi-Domain Data Expander (Parallel)")
    print(f"Workers: {num_workers} | Pairs/worker: {pairs_per_worker}")
    print(f"{'='*70}\n")

    t0 = time.time()

    with mp.Pool(processes=num_workers) as pool:
        args = [(d, pairs_per_worker, str(OUTPUT_DIR)) for d in domains]
        pool.starmap(worker_process, args)

    elapsed = time.time() - t0
    total = merge_worker_outputs(OUTPUT_DIR, MERGED_OUTPUT)

    print(f"\n  Parallel expansion done: {total} unique samples in {elapsed:.0f}s")
    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Jemma Multi-Terminal Data Expander")
    parser.add_argument("--workers", type=int, default=3, help="Number of domain workers")
    parser.add_argument("--pairs", type=int, default=30, help="QA pairs per worker")
    parser.add_argument("--parallel", action="store_true", help="Use multiprocessing pool")
    parser.add_argument("--model", default=MODEL, help="Ollama model")
    parser.add_argument("--min-quality", type=float, default=0.65)
    args = parser.parse_args()

    MODEL = args.model
    MIN_QUALITY = args.min_quality
    os.makedirs("logs", exist_ok=True)

    if args.parallel:
        run_truly_parallel(args.workers, args.pairs)
    else:
        run_parallel(args.workers, args.pairs)
