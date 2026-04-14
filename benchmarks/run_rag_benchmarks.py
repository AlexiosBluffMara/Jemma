#!/usr/bin/env python3
"""
Jemma RAG Benchmark Runner
============================
Benchmarks five configurations on the same 78-question suite:
  1. Base model (Ollama, no context)          — already done
  2. RAG (vector retrieval + Ollama)          — new
  3. GraphRAG (graph-expanded + Ollama)       — new
  4. Fine-tuned model (QLoRA, no context)     — run_finetune_benchmark.py
  5. Fine-tuned + RAG (QLoRA + RAG context)   — new

Results saved to benchmarks/results/ for comparison.
"""
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_e2b_e4b_benchmarks import BENCHMARKS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_MODEL = "gemma4:e4b"
GRAPHRAG_DB = Path(__file__).parent.parent / "datasets" / "graphrag.db"
CIVIC_RAG_DB = Path(__file__).parent.parent / "datasets" / "civic_data.db"
RESULTS_DIR = Path(__file__).parent / "results"


def ollama_generate(prompt: str, system: str = "", model: str = OLLAMA_MODEL,
                    context: str = "") -> dict:
    """Generate via Ollama with optional RAG context."""
    import httpx

    messages = []
    if system:
        if context:
            system = system + f"\n\nContext:\n{context}"
        messages.append({"role": "system", "content": system})
    elif context:
        messages.append({"role": "system", "content": f"Answer using this context:\n{context}"})
    messages.append({"role": "user", "content": prompt})

    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.perf_counter() - t0) * 1000
        response = data.get("message", {}).get("content", "")
        tok_count = data.get("eval_count", len(response.split()))
        tok_s = tok_count / (elapsed / 1000) if elapsed > 0 else 0
        return {
            "response": response,
            "tok_s": round(tok_s, 2),
            "total_ms": round(elapsed, 1),
            "eval_count": tok_count,
        }
    except Exception as e:
        return {"response": f"[ERROR: {e}]", "tok_s": 0, "total_ms": 0, "eval_count": 0}


def retrieve_context(query: str, strategy: str = "vector", top_k: int = 5) -> str:
    """Retrieve context from GraphRAG or civic RAG."""
    try:
        from graphrag import retrieve_vector, retrieve_graph, retrieve_hybrid, init_db
        import sqlite3

        db_path = GRAPHRAG_DB if GRAPHRAG_DB.exists() else CIVIC_RAG_DB
        conn = sqlite3.connect(str(db_path))

        if strategy == "graph":
            chunks = retrieve_graph(query, conn, top_k=top_k)
        elif strategy == "hybrid":
            chunks = retrieve_hybrid(query, conn, top_k=top_k)
        else:
            chunks = retrieve_vector(query, conn, top_k=top_k)

        conn.close()

        if not chunks:
            return ""

        return "\n\n---\n\n".join([
            f"[Score: {c['score']:.3f}]\n{c['text'][:1200]}"
            for c in chunks
        ])
    except Exception as e:
        print(f"    [RAG error: {e}]")
        return ""


SYSTEM_PROMPT = "You are a helpful, accurate, and safe AI assistant. Answer concisely and correctly."


def run_benchmark(config_name: str, use_rag: bool = False,
                  rag_strategy: str = "vector") -> dict:
    """Run the full 78-question benchmark suite with a given configuration."""
    print(f"\n{'='*70}")
    print(f"BENCHMARK: {config_name}")
    print(f"RAG: {rag_strategy if use_rag else 'none'}")
    print(f"{'='*70}")

    results = {
        "config": config_name,
        "model": OLLAMA_MODEL,
        "rag_strategy": rag_strategy if use_rag else "none",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmarks": {},
        "summary": {},
    }

    total_score = 0
    total_questions = 0
    total_latency = []
    total_tok_s = []

    for bench_name, bench in BENCHMARKS.items():
        print(f"\n  [{bench_name}] ({len(bench['questions'])} questions)")
        bench_scores = []
        bench_latencies = []
        bench_tok_s = []
        question_results = []

        for i, q_data in enumerate(bench["questions"]):
            sys.stdout.write(f"    Q{i+1}...")
            sys.stdout.flush()

            context = ""
            if use_rag:
                context = retrieve_context(q_data["q"], strategy=rag_strategy)

            result = ollama_generate(q_data["q"], system=SYSTEM_PROMPT, context=context)
            score, explanation = q_data["check"](result["response"], q_data["answer"])

            bench_scores.append(score)
            bench_latencies.append(result["total_ms"])
            if result["tok_s"] > 0:
                bench_tok_s.append(result["tok_s"])

            icon = "✓" if score >= 0.5 else "✗"
            rag_tag = f" [+RAG {len(context)}ch]" if context else ""
            sys.stdout.write(f" {icon} ({score:.0%}, {result['total_ms']:.0f}ms{rag_tag})\n")

            question_results.append({
                "question": q_data["q"][:120],
                "expected": q_data["answer"],
                "response_preview": result["response"][:200],
                "score": score,
                "latency_ms": result["total_ms"],
                "tok_s": result["tok_s"],
                "rag_context_len": len(context),
            })

        avg_score = statistics.mean(bench_scores) if bench_scores else 0
        results["benchmarks"][bench_name] = {
            "description": bench["description"],
            "num_questions": len(bench["questions"]),
            "avg_score": round(avg_score, 4),
            "pass_rate": round(sum(1 for s in bench_scores if s >= 0.5) / len(bench_scores), 4) if bench_scores else 0,
            "avg_latency_ms": round(statistics.mean(bench_latencies), 1) if bench_latencies else 0,
            "avg_tok_s": round(statistics.mean(bench_tok_s), 2) if bench_tok_s else 0,
            "questions": question_results,
        }

        total_score += sum(bench_scores)
        total_questions += len(bench_scores)
        total_latency.extend(bench_latencies)
        total_tok_s.extend(bench_tok_s)

        print(f"    → Score: {avg_score:.1%} | Pass: {results['benchmarks'][bench_name]['pass_rate']:.0%} | Avg latency: {results['benchmarks'][bench_name]['avg_latency_ms']:.0f}ms")

    results["summary"] = {
        "overall_score": round(total_score / total_questions, 4) if total_questions else 0,
        "total_questions": total_questions,
        "avg_latency_ms": round(statistics.mean(total_latency), 1) if total_latency else 0,
        "avg_tok_s": round(statistics.mean(total_tok_s), 2) if total_tok_s else 0,
    }

    # Save
    tag = config_name.lower().replace(" ", "_").replace("+", "_")
    outfile = RESULTS_DIR / f"{tag}_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {outfile}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: {config_name}")
    print(f"{'='*70}")
    for bname, b in results["benchmarks"].items():
        print(f"  {bname:<30} {b['avg_score']:>6.1%}  (pass: {b['pass_rate']:.0%}, {b['avg_latency_ms']:.0f}ms)")
    print(f"  {'OVERALL':<30} {results['summary']['overall_score']:>6.1%}")
    print(f"  Avg latency: {results['summary']['avg_latency_ms']:.0f}ms | Avg tok/s: {results['summary']['avg_tok_s']:.1f}")

    return results


# ---------------------------------------------------------------------------
# Compare results
# ---------------------------------------------------------------------------
def load_all_results() -> list[dict]:
    """Load all benchmark result files."""
    results = []
    for fn in sorted(RESULTS_DIR.glob("*.json")):
        with open(fn) as f:
            data = json.load(f)
        if "summary" in data and "benchmarks" in data:
            data["_file"] = fn.name
            results.append(data)
    return results


def print_comparison(results: list[dict]):
    """Print side-by-side comparison table."""
    if not results:
        print("No results to compare.")
        return

    # Get all benchmark names
    all_benches = list(BENCHMARKS.keys())
    configs = [r.get("config", r.get("model", "?")) for r in results]

    print(f"\n{'='*90}")
    print("CROSS-CONFIGURATION COMPARISON")
    print(f"{'='*90}")

    header = f"{'Benchmark':<25}" + "".join(f"{c[:18]:>20}" for c in configs)
    print(header)
    print("-" * len(header))

    for bench in all_benches:
        row = f"{bench:<25}"
        for r in results:
            score = r.get("benchmarks", {}).get(bench, {}).get("avg_score", 0)
            row += f"{score:>19.1%} "
        print(row)

    print("-" * len(header))
    row = f"{'OVERALL':<25}"
    for r in results:
        score = r.get("summary", {}).get("overall_score", 0)
        row += f"{score:>19.1%} "
    print(row)

    row = f"{'Avg Latency (ms)':<25}"
    for r in results:
        lat = r.get("summary", {}).get("avg_latency_ms", 0)
        row += f"{lat:>18.0f}ms "
    print(row)

    row = f"{'Throughput (tok/s)':<25}"
    for r in results:
        tps = r.get("summary", {}).get("avg_tok_s", 0)
        row += f"{tps:>18.1f}  "
    print(row)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Jemma RAG Benchmark Runner")
    parser.add_argument("--config", choices=[
        "base", "rag-vector", "rag-graph", "rag-hybrid", "compare"
    ], default="base", help="Which configuration to benchmark")
    parser.add_argument("--model", default=OLLAMA_MODEL)
    args = parser.parse_args()

    OLLAMA_MODEL = args.model

    if args.config == "compare":
        results = load_all_results()
        print_comparison(results)
    elif args.config == "base":
        run_benchmark("E4B Base (Ollama)", use_rag=False)
    elif args.config == "rag-vector":
        run_benchmark("E4B + RAG Vector", use_rag=True, rag_strategy="vector")
    elif args.config == "rag-graph":
        run_benchmark("E4B + GraphRAG", use_rag=True, rag_strategy="graph")
    elif args.config == "rag-hybrid":
        run_benchmark("E4B + RAG Hybrid", use_rag=True, rag_strategy="hybrid")
