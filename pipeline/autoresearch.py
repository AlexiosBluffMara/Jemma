#!/usr/bin/env python3
"""
Jemma AutoResearch — Self-Improving Training Loop
===================================================
Inspired by Karpathy's AutoResearch concept.

Loop: Generate questions → Query model → Score responses → Curate dataset
      → Re-train → Benchmark → Repeat

Each iteration expands training data with verified high-quality samples,
then fine-tunes and measures improvement against the benchmark suite.

Designed to run continuously, expanding the civic knowledge dataset
through self-play and automated quality scoring.
"""
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import httpx

log = logging.getLogger("autoresearch")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/autoresearch.log", encoding="utf-8"),
    ],
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE = "http://127.0.0.1:11434"
MODEL = "gemma4:e4b"
JUDGE_MODEL = "gemma4:e4b"  # self-judge (same model scores its own answers)

DATASET_PATH = Path("datasets/civic_sft_train.jsonl")
EXPANDED_PATH = Path("datasets/civic_sft_expanded.jsonl")
STATE_PATH = Path("state/autoresearch_state.json")
RESULTS_DIR = Path("benchmarks/results")

MIN_SCORE_TO_KEEP = 0.7   # minimum quality score to add to training set
QUESTIONS_PER_ITERATION = 50
MAX_ITERATIONS = 20

# Topic pools for question generation
CIVIC_TOPICS = [
    "food safety inspections in Chicago",
    "building code violations and enforcement",
    "business license requirements for restaurants",
    "public transportation and traffic safety",
    "emergency services response times",
    "public library programs and accessibility",
    "police district boundaries and jurisdiction",
    "public health clinic services",
    "311 service request categories and resolution",
    "construction permit requirements",
    "environmental regulations for businesses",
    "zoning laws and land use",
    "water quality and utility management",
    "school district funding and governance",
    "fire department inspection protocols",
    "noise ordinance enforcement",
    "property tax assessment appeals",
    "sidewalk and road maintenance responsibility",
    "community development block grants",
    "affordable housing programs",
    "disaster preparedness for municipalities",
    "civic data transparency requirements",
    "public records access and FOIA",
    "town council meeting procedures",
    "budget allocation and fiscal responsibility",
]

QUESTION_TYPES = [
    "factual question requiring specific data",
    "comparison between two civic services",
    "explanation of a civic process step by step",
    "analysis of a civic policy's impact",
    "troubleshooting a civic issue (e.g., pothole report)",
    "safety assessment scenario",
    "legal/regulatory compliance check",
    "data interpretation from civic records",
]

SYSTEM_PROMPT = (
    "You are Jemma SafeBrain, a civic AI assistant for the Town of Normal, IL, "
    "Illinois State University, and Chicago civic services. Provide accurate, "
    "specific answers based on public records and civic data."
)


# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------
def ollama_chat(messages: list[dict], model: str = MODEL,
                temperature: float = 0.7, max_tokens: int = 1024) -> str:
    """Chat with Ollama, return response text."""
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        log.error(f"Ollama error: {e}")
        return ""


# ---------------------------------------------------------------------------
# Step 1: Generate questions
# ---------------------------------------------------------------------------
def generate_questions(n: int = QUESTIONS_PER_ITERATION) -> list[dict]:
    """Generate diverse civic questions using the model itself."""
    questions = []
    per_batch = min(10, n)
    batches = (n + per_batch - 1) // per_batch

    for batch_idx in range(batches):
        topic = random.choice(CIVIC_TOPICS)
        qtype = random.choice(QUESTION_TYPES)

        prompt = (
            f"Generate exactly {per_batch} diverse, specific civic questions about '{topic}'. "
            f"Question type: {qtype}. "
            f"Format: one question per line, numbered 1-{per_batch}. "
            f"Make questions specific, fact-seeking, and answerable from public civic records. "
            f"Do NOT include answers."
        )

        response = ollama_chat([
            {"role": "system", "content": "You are a civic question generator. Generate specific, factual questions."},
            {"role": "user", "content": prompt},
        ], temperature=0.9)

        # Parse questions from response
        for line in response.strip().split("\n"):
            line = line.strip()
            # Remove numbering
            import re
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            if line and len(line) > 20 and "?" in line:
                questions.append({
                    "question": line,
                    "topic": topic,
                    "type": qtype,
                })

        if len(questions) >= n:
            break

    return questions[:n]


# ---------------------------------------------------------------------------
# Step 2: Answer questions
# ---------------------------------------------------------------------------
def answer_questions(questions: list[dict]) -> list[dict]:
    """Have the model answer each question."""
    answered = []
    for i, q in enumerate(questions):
        sys.stdout.write(f"  Answering {i+1}/{len(questions)}...")
        sys.stdout.flush()

        response = ollama_chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q["question"]},
        ], temperature=0.3, max_tokens=768)

        q["answer"] = response
        answered.append(q)
        sys.stdout.write(f" ({len(response)} chars)\n")

    return answered


# ---------------------------------------------------------------------------
# Step 3: Score answers (LLM-as-judge)
# ---------------------------------------------------------------------------
def score_answers(qa_pairs: list[dict]) -> list[dict]:
    """Use the model as judge to score answer quality."""
    scored = []
    for i, qa in enumerate(qa_pairs):
        sys.stdout.write(f"  Scoring {i+1}/{len(qa_pairs)}...")
        sys.stdout.flush()

        judge_prompt = (
            f"Rate this civic AI answer on a scale of 0.0 to 1.0.\n\n"
            f"Question: {qa['question']}\n\n"
            f"Answer: {qa['answer'][:1500]}\n\n"
            f"Rate on these criteria:\n"
            f"- Factual accuracy (0-0.3)\n"
            f"- Specificity and detail (0-0.3)\n"
            f"- Relevance to civic domain (0-0.2)\n"
            f"- Safety and appropriateness (0-0.2)\n\n"
            f"Respond with ONLY a single number between 0.0 and 1.0."
        )

        score_text = ollama_chat([
            {"role": "system", "content": "You are a quality judge. Respond with only a number 0.0-1.0."},
            {"role": "user", "content": judge_prompt},
        ], model=JUDGE_MODEL, temperature=0.1, max_tokens=10)

        try:
            import re
            numbers = re.findall(r"(\d+\.?\d*)", score_text)
            score = float(numbers[0]) if numbers else 0.5
            score = max(0.0, min(1.0, score))
        except (ValueError, IndexError):
            score = 0.5

        qa["quality_score"] = score
        scored.append(qa)
        icon = "✓" if score >= MIN_SCORE_TO_KEEP else "✗"
        sys.stdout.write(f" {icon} score={score:.2f}\n")

    return scored


# ---------------------------------------------------------------------------
# Step 4: Curate and append to dataset
# ---------------------------------------------------------------------------
def curate_dataset(scored_pairs: list[dict]) -> int:
    """Append high-quality pairs to the expanded training dataset."""
    kept = [qa for qa in scored_pairs if qa["quality_score"] >= MIN_SCORE_TO_KEEP]

    if not kept:
        log.info("No samples met quality threshold.")
        return 0

    os.makedirs(EXPANDED_PATH.parent, exist_ok=True)

    with open(EXPANDED_PATH, "a", encoding="utf-8") as f:
        for qa in kept:
            sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": qa["question"]},
                    {"role": "assistant", "content": qa["answer"]},
                ],
                "_meta": {
                    "source": "autoresearch",
                    "topic": qa.get("topic", ""),
                    "quality_score": qa["quality_score"],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    log.info(f"Added {len(kept)}/{len(scored_pairs)} samples to {EXPANDED_PATH}")
    return len(kept)


# ---------------------------------------------------------------------------
# Step 5: Merge datasets
# ---------------------------------------------------------------------------
def merge_datasets() -> int:
    """Merge original + expanded into a combined training file."""
    combined = []

    # Load original
    if DATASET_PATH.exists():
        with open(DATASET_PATH) as f:
            for line in f:
                combined.append(json.loads(line))

    # Load expanded
    if EXPANDED_PATH.exists():
        with open(EXPANDED_PATH) as f:
            for line in f:
                combined.append(json.loads(line))

    # Deduplicate by question text
    seen = set()
    unique = []
    for sample in combined:
        msgs = sample.get("messages", [])
        user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
        if user_msg and user_msg not in seen:
            seen.add(user_msg)
            unique.append(sample)

    merged_path = Path("datasets/civic_sft_combined.jsonl")
    with open(merged_path, "w", encoding="utf-8") as f:
        for sample in unique:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    log.info(f"Merged dataset: {len(unique)} unique samples → {merged_path}")
    return len(unique)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "iteration": 0,
        "total_generated": 0,
        "total_kept": 0,
        "total_dataset_size": 0,
        "best_score": 0.0,
        "scores_history": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def save_state(state: dict):
    os.makedirs(STATE_PATH.parent, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run_iteration(state: dict) -> dict:
    """Run a single AutoResearch iteration."""
    iteration = state["iteration"]
    log.info(f"\n{'='*70}")
    log.info(f"AutoResearch Iteration {iteration + 1}")
    log.info(f"{'='*70}")

    # Step 1: Generate questions
    print(f"\n[Step 1] Generating {QUESTIONS_PER_ITERATION} questions...")
    questions = generate_questions(QUESTIONS_PER_ITERATION)
    log.info(f"Generated {len(questions)} questions")

    # Step 2: Answer
    print(f"\n[Step 2] Answering {len(questions)} questions...")
    answered = answer_questions(questions)

    # Step 3: Score
    print(f"\n[Step 3] Scoring {len(answered)} answers...")
    scored = score_answers(answered)

    # Step 4: Curate
    print(f"\n[Step 4] Curating dataset...")
    kept = curate_dataset(scored)

    # Step 5: Merge
    print(f"\n[Step 5] Merging datasets...")
    total = merge_datasets()

    # Update state
    avg_quality = sum(qa["quality_score"] for qa in scored) / len(scored) if scored else 0
    state["iteration"] = iteration + 1
    state["total_generated"] += len(questions)
    state["total_kept"] += kept
    state["total_dataset_size"] = total
    state["scores_history"].append({
        "iteration": iteration + 1,
        "generated": len(questions),
        "kept": kept,
        "avg_quality": round(avg_quality, 4),
        "dataset_size": total,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_state(state)

    # Summary
    print(f"\n{'='*70}")
    print(f"Iteration {iteration + 1} Summary")
    print(f"{'='*70}")
    print(f"  Questions generated: {len(questions)}")
    print(f"  Answers scored: {len(scored)}")
    print(f"  Samples kept (score >= {MIN_SCORE_TO_KEEP}): {kept}")
    print(f"  Avg quality score: {avg_quality:.3f}")
    print(f"  Total dataset size: {total}")
    print(f"  Cumulative kept: {state['total_kept']}")

    return state


def main():
    global QUESTIONS_PER_ITERATION, MIN_SCORE_TO_KEEP, MODEL, JUDGE_MODEL

    import argparse
    parser = argparse.ArgumentParser(description="Jemma AutoResearch Self-Improvement")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations")
    parser.add_argument("--questions", type=int, default=50, help="Questions per iteration")
    parser.add_argument("--min-score", type=float, default=0.7, help="Minimum quality score")
    parser.add_argument("--model", default=MODEL, help="Ollama model to use")
    parser.add_argument("--fresh", action="store_true", help="Start from scratch")
    args = parser.parse_args()

    QUESTIONS_PER_ITERATION = args.questions
    MIN_SCORE_TO_KEEP = args.min_score
    MODEL = args.model
    JUDGE_MODEL = args.model

    os.makedirs("logs", exist_ok=True)

    if args.fresh and STATE_PATH.exists():
        STATE_PATH.unlink()
    if args.fresh and EXPANDED_PATH.exists():
        EXPANDED_PATH.unlink()

    state = load_state()
    log.info(f"Starting AutoResearch (iterations={args.iterations}, "
             f"questions/iter={args.questions}, min_score={args.min_score})")
    log.info(f"Model: {args.model}")
    log.info(f"Current state: iteration={state['iteration']}, "
             f"dataset_size={state['total_dataset_size']}")

    for i in range(args.iterations):
        t0 = time.time()
        state = run_iteration(state)
        elapsed = time.time() - t0
        log.info(f"Iteration took {elapsed:.1f}s")

        if i < args.iterations - 1:
            log.info("Cooling down 5s before next iteration...")
            time.sleep(5)

    # Final summary
    print(f"\n{'='*70}")
    print("AutoResearch Complete")
    print(f"{'='*70}")
    print(f"  Total iterations: {state['iteration']}")
    print(f"  Total questions generated: {state['total_generated']}")
    print(f"  Total samples kept: {state['total_kept']}")
    print(f"  Final dataset size: {state['total_dataset_size']}")
    print(f"  Quality scores: {[h['avg_quality'] for h in state['scores_history']]}")


if __name__ == "__main__":
    main()
