#!/usr/bin/env python3
"""
Jemma Unsloth/Transformers Benchmark — E4B BF16 (raw base model, no fine-tuning)
Runs the same benchmark questions via direct model inference for comparison with Ollama.
"""
import json, time, re, sys, os, statistics
from pathlib import Path
from datetime import datetime, timezone

# ── Import benchmarks from main suite ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from run_e2b_e4b_benchmarks import BENCHMARKS, REFERENCE_SCORES

# ── Load model ────────────────────────────────────────────────────────────────
import torch
print(f"PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")

MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "unsloth/gemma-4-E4B-it"
LOAD_4BIT = "--4bit" in sys.argv
LABEL = sys.argv[2] if len(sys.argv) > 2 else MODEL_NAME.split("/")[-1]

print(f"\nLoading {MODEL_NAME} (4bit={LOAD_4BIT})...")
t0 = time.perf_counter()

if LOAD_4BIT:
    from unsloth import FastModel
    model, tokenizer = FastModel.from_pretrained(
        MODEL_NAME, dtype=None, max_seq_length=4096,
        load_in_4bit=True, full_finetuning=False,
    )
    FastModel.for_inference(model)
else:
    from transformers import AutoProcessor, AutoModelForMultimodalLM
    tokenizer = AutoProcessor.from_pretrained(MODEL_NAME)
    model = AutoModelForMultimodalLM.from_pretrained(
        MODEL_NAME, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.eval()

load_time = time.perf_counter() - t0
print(f"Model loaded in {load_time:.1f}s")
print(f"Model type: {type(model).__name__}")
param_count = sum(p.numel() for p in model.parameters())
print(f"Parameters: {param_count/1e9:.2f}B")


def generate(prompt: str, system: str = "", max_tokens: int = 384, temperature: float = 0.0) -> dict:
    """Generate response using HuggingFace model."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text=[text], return_tensors="pt").to(model.device)
    outputs = None

    try:
        t0 = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,
            )
        elapsed = (time.perf_counter() - t0) * 1000

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)
        tok_count = len(new_tokens)
        tok_s = (tok_count / (elapsed / 1000)) if elapsed > 0 else 0
    except Exception as e:
        torch.cuda.empty_cache()
        return {
            "response": f"[ERROR: {type(e).__name__}: {e}]",
            "tok_s": 0,
            "total_ms": 0,
            "eval_count": 0,
        }
    finally:
        del inputs
        if outputs is not None
        if outputs is not None:
            del outputs
        torch.cuda.empty_cache()

    return {
        "response": response,
        "tok_s": round(tok_s, 2),
        "total_ms": round(elapsed, 1),
        "eval_count": tok_count,
    }


SYSTEM_PROMPT = "You are a helpful, accurate, and safe AI assistant. Answer concisely and correctly."

def run_all():
    results = {
        "model": LABEL,
        "model_name": MODEL_NAME,
        "backend": "unsloth-4bit" if LOAD_4BIT else "transformers-bf16",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "load_time_s": round(load_time, 1),
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

            result = generate(q_data["q"], system=SYSTEM_PROMPT)
            score, explanation = q_data["check"](result["response"], q_data["answer"])

            bench_scores.append(score)
            bench_latencies.append(result["total_ms"])
            if result["tok_s"] > 0:
                bench_tok_s.append(result["tok_s"])

            icon = "✓" if score >= 0.5 else "✗"
            sys.stdout.write(f" {icon} ({score:.0%}, {result['total_ms']:.0f}ms, {result['tok_s']:.1f} tok/s)\n")

            question_results.append({
                "question": q_data["q"][:120] + "..." if len(q_data["q"]) > 120 else q_data["q"],
                "expected": q_data["answer"],
                "response_preview": result["response"][:200],
                "score": score,
                "explanation": explanation,
                "latency_ms": result["total_ms"],
                "tok_s": result["tok_s"],
                "eval_count": result["eval_count"],
            })

        avg_score = statistics.mean(bench_scores) if bench_scores else 0
        results["benchmarks"][bench_name] = {
            "description": bench["description"],
            "category": bench["category"],
            "comparable_to": bench["comparable_to"],
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
        "total_correct": sum(1 for b in results["benchmarks"].values()
                            for q in b["questions"] if q["score"] >= 0.5),
        "avg_latency_ms": round(statistics.mean(total_latency), 1) if total_latency else 0,
        "avg_tok_s": round(statistics.mean(total_tok_s), 2) if total_tok_s else 0,
    }

    # Save
    os.makedirs("benchmarks/results", exist_ok=True)
    outfile = f"benchmarks/results/{LABEL}_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {outfile}")

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY: {LABEL} ({results['model_name']})")
    print(f"{'='*70}")
    for bname, b in results["benchmarks"].items():
        print(f"  {bname:<30} {b['avg_score']:>6.1%}  (pass: {b['pass_rate']:.0%}, {b['avg_latency_ms']:.0f}ms, {b['avg_tok_s']:.1f} tok/s)")
    print(f"  {'OVERALL':<30} {results['summary']['overall_score']:>6.1%}")
    print(f"  Avg latency: {results['summary']['avg_latency_ms']:.0f}ms | Avg tok/s: {results['summary']['avg_tok_s']:.1f}")

    return results


if __name__ == "__main__":
    run_all()
