#!/usr/bin/env python3
"""
Jemma Fine-Tuned E4B Benchmark
===============================
Quick QLoRA fine-tune on civic SFT data, then run the same benchmark suite
to measure the impact of fine-tuning vs base model.
"""
import json, time, sys, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

import torch
print(f"PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME = "unsloth/gemma-4-E4B-it"
DATASET_PATH = "datasets/civic_sft_train.jsonl"
ADAPTER_DIR = "checkpoints/benchmark_adapter"
TRAIN_STEPS = 200
BATCH_SIZE = 2
LR = 2e-4
LORA_R = 32

# ── Step 1: Fine-tune ────────────────────────────────────────────────────────
def train():
    from unsloth import FastModel
    from trl import SFTTrainer, SFTConfig
    import datasets

    print(f"\n{'='*70}")
    print("STEP 1: QLoRA Fine-Tuning")
    print(f"{'='*70}")

    model, tokenizer = FastModel.from_pretrained(
        MODEL_NAME, dtype=None, max_seq_length=4096,
        load_in_4bit=True, full_finetuning=False,
    )

    model = FastModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_R * 2,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable: {trainable/1e6:.1f}M / {total/1e9:.2f}B ({trainable/total:.2%})")

    # Load dataset (strip _meta, keep only messages)
    raw = []
    with open(DATASET_PATH) as f:
        for line in f:
            d = json.loads(line)
            raw.append({"messages": d["messages"]})
    print(f"Dataset: {len(raw)} samples")

    def formatting_func(example):
        msgs = example["messages"]
        # Single example: msgs is a list of role/content dicts
        if isinstance(msgs, list) and len(msgs) > 0 and isinstance(msgs[0], dict):
            return [tokenizer.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=False
            )]
        # Batched: msgs is a list of lists
        return [
            tokenizer.apply_chat_template(
                m, tokenize=False, add_generation_prompt=False
            ) for m in msgs
        ]

    ds = datasets.Dataset.from_list(raw)

    config = SFTConfig(
        output_dir=ADAPTER_DIR,
        max_steps=TRAIN_STEPS,
        per_device_train_batch_size=BATCH_SIZE,
        learning_rate=LR,
        warmup_steps=20,
        weight_decay=0.01,
        logging_steps=20,
        bf16=True,
        max_seq_length=4096,
        seed=42,
        save_strategy="no",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=ds,
        formatting_func=formatting_func,
        args=config,
    )

    t0 = time.perf_counter()
    result = trainer.train()
    train_time = time.perf_counter() - t0

    print(f"\nTraining complete in {train_time:.1f}s")
    print(f"Final loss: {result.training_loss:.4f}")

    # Save adapter
    os.makedirs(ADAPTER_DIR, exist_ok=True)
    model.save_pretrained(ADAPTER_DIR)
    tokenizer.save_pretrained(ADAPTER_DIR)
    print(f"Adapter saved to {ADAPTER_DIR}")

    return model, tokenizer, train_time, result.training_loss


# ── Step 2: Benchmark ────────────────────────────────────────────────────────
def benchmark(model, tokenizer):
    from run_e2b_e4b_benchmarks import BENCHMARKS
    import statistics

    print(f"\n{'='*70}")
    print("STEP 2: Benchmarking Fine-Tuned Model")
    print(f"{'='*70}")

    FastModel_cls = None
    try:
        from unsloth import FastModel as FM
        FM.for_inference(model)
        FastModel_cls = FM
    except Exception:
        model.eval()

    SYSTEM_PROMPT = "You are a helpful, accurate, and safe AI assistant. Answer concisely and correctly."

    def generate(prompt, system="", max_tokens=512):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text=[text], return_tensors="pt").to(model.device)

        try:
            t0 = time.perf_counter()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs, max_new_tokens=max_tokens,
                    temperature=None, do_sample=False,
                )
            elapsed = (time.perf_counter() - t0) * 1000

            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            response = tokenizer.decode(new_tokens, skip_special_tokens=True)
            tok_count = len(new_tokens)
            tok_s = (tok_count / (elapsed / 1000)) if elapsed > 0 else 0
        except Exception as e:
            torch.cuda.empty_cache()
            return {"response": f"[ERROR: {type(e).__name__}]", "tok_s": 0, "total_ms": 0, "eval_count": 0}
        finally:
            del inputs
            torch.cuda.empty_cache()

        return {"response": response, "tok_s": round(tok_s, 2), "total_ms": round(elapsed, 1), "eval_count": tok_count}

    results = {
        "model": "e4b_finetuned_civic",
        "model_name": MODEL_NAME,
        "backend": "unsloth-4bit-qlora",
        "adapter": ADAPTER_DIR,
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

            result = generate(q_data["q"], system=SYSTEM_PROMPT)
            score, explanation = q_data["check"](result["response"], q_data["answer"])

            bench_scores.append(score)
            bench_latencies.append(result["total_ms"])
            if result["tok_s"] > 0:
                bench_tok_s.append(result["tok_s"])

            icon = "✓" if score >= 0.5 else "✗"
            sys.stdout.write(f" {icon} ({score:.0%}, {result['total_ms']:.0f}ms, {result['tok_s']:.1f} tok/s)\n")

            question_results.append({
                "question": q_data["q"][:120],
                "expected": q_data["answer"],
                "response_preview": result["response"][:200],
                "score": score,
                "latency_ms": result["total_ms"],
                "tok_s": result["tok_s"],
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

    outfile = f"benchmarks/results/e4b_finetuned_civic_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    os.makedirs("benchmarks/results", exist_ok=True)
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {outfile}")

    print(f"\n{'='*70}")
    print(f"SUMMARY: Fine-Tuned E4B ({ADAPTER_DIR})")
    print(f"{'='*70}")
    for bname, b in results["benchmarks"].items():
        print(f"  {bname:<30} {b['avg_score']:>6.1%}  (pass: {b['pass_rate']:.0%})")
    print(f"  {'OVERALL':<30} {results['summary']['overall_score']:>6.1%}")

    return results


if __name__ == "__main__":
    model, tokenizer, train_time, final_loss = train()
    results = benchmark(model, tokenizer)
    results["training"] = {
        "train_time_s": round(train_time, 1),
        "final_loss": round(final_loss, 4),
        "steps": TRAIN_STEPS,
        "lora_r": LORA_R,
        "dataset_path": DATASET_PATH,
    }
    # Re-save with training info
    outfile = f"benchmarks/results/e4b_finetuned_civic_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFinal results saved: {outfile}")
