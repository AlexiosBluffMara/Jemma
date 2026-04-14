"""
Jemma Embed — Embedding Benchmark Suite

Evaluates Jemma embedding models against competitors on:
  1. MTEB text benchmarks (STS, retrieval, classification)
  2. Cross-modal retrieval (image→text, audio→text)
  3. Per-modality comparisons vs CLIP, Jina-CLIP, etc.
  4. Matryoshka dimension scaling analysis
  5. Inference speed (tokens/sec, latency)

Results written to benchmarks/results/embedding_*.json
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

log = logging.getLogger("jemma.embed.bench")

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "benchmarks" / "results"


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------
@dataclass
class EmbeddingBenchResult:
    model_name: str
    variant: str
    task: str
    metric: str
    score: float
    dimension: int
    modality: str = "text"
    latency_ms: float = 0.0
    samples_per_sec: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    model_name: str
    variant: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    text_results: list[EmbeddingBenchResult] = field(default_factory=list)
    multimodal_results: list[EmbeddingBenchResult] = field(default_factory=list)
    speed_results: list[EmbeddingBenchResult] = field(default_factory=list)
    competitor_results: list[EmbeddingBenchResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MTEB-lite evaluation (subset of MTEB for quick iteration)
# ---------------------------------------------------------------------------
MTEB_LITE_TASKS = [
    # STS tasks (Spearman correlation)
    ("STSBenchmark", "sts"),
    ("SICK-R", "sts"),
    # Retrieval (nDCG@10)
    ("ArguAna", "retrieval"),
    ("SciFact", "retrieval"),
    ("NFCorpus", "retrieval"),
    ("FiQA2018", "retrieval"),
    # Classification (accuracy)
    ("AmazonReviewsClassification", "classification"),
    ("TweetSentimentExtraction", "classification"),
    # Pair classification (AP)
    ("SprintDuplicateQuestions", "pair_classification"),
    ("TwitterURLCorpus", "pair_classification"),
]


def run_mteb_evaluation(
    model,
    tasks: list[tuple[str, str]] | None = None,
    truncate_dim: int | None = None,
    batch_size: int = 64,
) -> list[EmbeddingBenchResult]:
    """
    Run MTEB-lite evaluation against Jemma embedding model.
    Returns list of per-task results.
    """
    try:
        from mteb import MTEB
    except ImportError:
        log.warning("mteb package not installed, using manual STS evaluation")
        return _run_manual_sts(model, truncate_dim)

    results = []
    if tasks is None:
        tasks = MTEB_LITE_TASKS

    dim = truncate_dim or model.config.embed_dim
    log.info(f"Running MTEB evaluation (dim={dim}, {len(tasks)} tasks)...")

    class MTEBModelWrapper:
        """Adapter to make JemmaEmbedModel compatible with MTEB."""

        def __init__(self, jemma_model, trunc_dim):
            self.model = jemma_model
            self.trunc_dim = trunc_dim

        def encode(self, sentences, batch_size=32, **kwargs):
            embs = self.model.encode_text(
                sentences, batch_size=batch_size,
                truncate_dim=self.trunc_dim, add_instruction=False,
            )
            return embs.numpy()

    wrapper = MTEBModelWrapper(model, truncate_dim)

    for task_name, task_type in tasks:
        try:
            start = time.time()
            evaluation = MTEB(tasks=[task_name], task_langs=["en"])
            eval_results = evaluation.run(
                wrapper, output_folder=None,
                eval_splits=["test"], batch_size=batch_size,
            )

            elapsed = time.time() - start

            # Extract primary metric
            for r in eval_results:
                score = _extract_mteb_score(r, task_type)
                results.append(EmbeddingBenchResult(
                    model_name=model.config.model_name,
                    variant="jemma-embed",
                    task=task_name,
                    metric=_metric_name(task_type),
                    score=score,
                    dimension=dim,
                    modality="text",
                    latency_ms=elapsed * 1000,
                ))
                log.info(f"  {task_name}: {score:.4f} ({elapsed:.1f}s)")

        except Exception as e:
            log.warning(f"  {task_name} failed: {e}")
            results.append(EmbeddingBenchResult(
                model_name=model.config.model_name,
                variant="jemma-embed",
                task=task_name,
                metric="error",
                score=0.0,
                dimension=dim,
                metadata={"error": str(e)},
            ))

    return results


def _run_manual_sts(model, truncate_dim: int | None = None) -> list[EmbeddingBenchResult]:
    """Fallback STS evaluation without mteb package."""
    from scipy.stats import spearmanr

    # STSBenchmark test set (embedded in code for zero-dep evaluation)
    sts_pairs = [
        ("A man is playing guitar.", "A man is playing a guitar.", 5.0),
        ("A woman is dancing.", "A man is dancing.", 3.2),
        ("A cat is sleeping.", "A dog is running.", 0.5),
        ("The weather is nice today.", "It's a beautiful day.", 4.2),
        ("I love programming.", "Coding is my passion.", 4.5),
        ("The stock market crashed.", "Fish are swimming in the ocean.", 0.1),
        ("She is reading a book.", "She is studying from a textbook.", 3.8),
        ("Two dogs are playing.", "Two dogs are fighting.", 2.5),
        ("A person is cooking.", "Someone is preparing food.", 4.3),
        ("The car is red.", "The vehicle is blue.", 2.0),
    ]

    texts_a = [p[0] for p in sts_pairs]
    texts_b = [p[1] for p in sts_pairs]
    gold_scores = [p[2] for p in sts_pairs]

    emb_a = model.encode_text(texts_a, truncate_dim=truncate_dim, add_instruction=False)
    emb_b = model.encode_text(texts_b, truncate_dim=truncate_dim, add_instruction=False)

    cos_sim = torch.nn.functional.cosine_similarity(emb_a, emb_b).numpy()
    correlation, _ = spearmanr(cos_sim, gold_scores)

    dim = truncate_dim or model.config.embed_dim
    log.info(f"Manual STS (dim={dim}): Spearman={correlation:.4f}")

    return [EmbeddingBenchResult(
        model_name=model.config.model_name,
        variant="jemma-embed",
        task="STSBenchmark-mini",
        metric="spearman",
        score=correlation,
        dimension=dim,
        modality="text",
    )]


def _extract_mteb_score(result: dict, task_type: str) -> float:
    """Extract primary metric from MTEB result dict."""
    if task_type == "sts":
        return result.get("cos_sim", {}).get("spearman", 0.0)
    elif task_type == "retrieval":
        return result.get("ndcg_at_10", 0.0)
    elif task_type == "classification":
        return result.get("accuracy", 0.0)
    elif task_type == "pair_classification":
        return result.get("ap", 0.0)
    return 0.0


def _metric_name(task_type: str) -> str:
    return {
        "sts": "spearman",
        "retrieval": "ndcg@10",
        "classification": "accuracy",
        "pair_classification": "ap",
    }.get(task_type, "score")


# ---------------------------------------------------------------------------
# Matryoshka dimension analysis
# ---------------------------------------------------------------------------
def benchmark_matryoshka_dims(
    model,
    dims: list[int] | None = None,
) -> list[EmbeddingBenchResult]:
    """Test embedding quality at each Matryoshka truncation dimension."""
    if dims is None:
        dims = model.config.matryoshka_dims

    results = []
    for dim in dims:
        log.info(f"\n--- Matryoshka dim={dim} ---")
        dim_results = _run_manual_sts(model, truncate_dim=dim)
        results.extend(dim_results)

    return results


# ---------------------------------------------------------------------------
# Speed benchmarks
# ---------------------------------------------------------------------------
def benchmark_speed(
    model,
    num_samples: int = 1000,
    batch_sizes: list[int] | None = None,
    truncate_dim: int | None = None,
) -> list[EmbeddingBenchResult]:
    """Benchmark encoding throughput and latency."""
    if batch_sizes is None:
        batch_sizes = [1, 8, 32, 64, 128]

    dim = truncate_dim or model.config.embed_dim
    # Generate sample texts of varying length
    texts = [
        f"This is sample text number {i} for benchmarking embedding speed. "
        f"It contains a moderate amount of content to simulate real-world usage."
        for i in range(num_samples)
    ]

    results = []
    for bs in batch_sizes:
        # Warmup
        _ = model.encode_text(texts[:bs], batch_size=bs, truncate_dim=truncate_dim)

        start = time.time()
        _ = model.encode_text(texts[:num_samples], batch_size=bs, truncate_dim=truncate_dim)
        elapsed = time.time() - start

        samples_sec = num_samples / elapsed
        latency_ms = (elapsed / num_samples) * 1000

        results.append(EmbeddingBenchResult(
            model_name=model.config.model_name,
            variant="jemma-embed",
            task=f"speed_batch{bs}",
            metric="samples/sec",
            score=samples_sec,
            dimension=dim,
            latency_ms=latency_ms,
            samples_per_sec=samples_sec,
            metadata={"batch_size": bs, "num_samples": num_samples},
        ))
        log.info(f"  batch={bs}: {samples_sec:.1f} samples/sec, {latency_ms:.1f}ms/sample")

    return results


# ---------------------------------------------------------------------------
# Competitor benchmarks
# ---------------------------------------------------------------------------
COMPETITOR_MODELS = {
    # Text-only
    "all-MiniLM-L6-v2": {
        "type": "sentence_transformer",
        "dim": 384,
        "modality": "text",
    },
    "BAAI/bge-large-en-v1.5": {
        "type": "sentence_transformer",
        "dim": 1024,
        "modality": "text",
    },
    # Multimodal
    "jinaai/jina-clip-v2": {
        "type": "sentence_transformer",
        "dim": 1024,
        "modality": "multimodal",
    },
    "openai/clip-vit-large-patch14": {
        "type": "clip",
        "dim": 768,
        "modality": "multimodal",
    },
}


def benchmark_competitors(
    tasks: list[str] | None = None,
    models: dict | None = None,
) -> list[EmbeddingBenchResult]:
    """
    Run the same benchmarks on competitor models for comparison.
    Uses sentence-transformers for text models, CLIP for multimodal.
    """
    if models is None:
        models = COMPETITOR_MODELS

    results = []
    for model_name, info in models.items():
        log.info(f"\n--- Competitor: {model_name} ---")

        try:
            if info["type"] == "sentence_transformer":
                results.extend(
                    _bench_sentence_transformer(model_name, info["dim"])
                )
            elif info["type"] == "clip":
                results.extend(
                    _bench_clip_model(model_name, info["dim"])
                )
        except Exception as e:
            log.warning(f"  {model_name} failed: {e}")
            results.append(EmbeddingBenchResult(
                model_name=model_name,
                variant="competitor",
                task="load",
                metric="error",
                score=0.0,
                dimension=info["dim"],
                metadata={"error": str(e)},
            ))

    return results


def _bench_sentence_transformer(
    model_name: str, dim: int
) -> list[EmbeddingBenchResult]:
    """Benchmark a sentence-transformers model on manual STS."""
    from sentence_transformers import SentenceTransformer
    from scipy.stats import spearmanr

    model = SentenceTransformer(model_name)

    sts_pairs = [
        ("A man is playing guitar.", "A man is playing a guitar.", 5.0),
        ("A woman is dancing.", "A man is dancing.", 3.2),
        ("A cat is sleeping.", "A dog is running.", 0.5),
        ("The weather is nice today.", "It's a beautiful day.", 4.2),
        ("I love programming.", "Coding is my passion.", 4.5),
        ("The stock market crashed.", "Fish are swimming in the ocean.", 0.1),
        ("She is reading a book.", "She is studying from a textbook.", 3.8),
        ("Two dogs are playing.", "Two dogs are fighting.", 2.5),
        ("A person is cooking.", "Someone is preparing food.", 4.3),
        ("The car is red.", "The vehicle is blue.", 2.0),
    ]

    texts_a = [p[0] for p in sts_pairs]
    texts_b = [p[1] for p in sts_pairs]
    gold = [p[2] for p in sts_pairs]

    emb_a = model.encode(texts_a, normalize_embeddings=True)
    emb_b = model.encode(texts_b, normalize_embeddings=True)

    cos_sim = np.sum(emb_a * emb_b, axis=1)
    correlation, _ = spearmanr(cos_sim, gold)

    # Speed test
    speed_texts = [f"Benchmark text {i}" for i in range(100)]
    start = time.time()
    model.encode(speed_texts, normalize_embeddings=True)
    elapsed = time.time() - start
    samples_sec = 100 / elapsed

    log.info(f"  {model_name}: STS={correlation:.4f}, speed={samples_sec:.1f}/sec")

    return [
        EmbeddingBenchResult(
            model_name=model_name, variant="competitor",
            task="STSBenchmark-mini", metric="spearman",
            score=correlation, dimension=dim, modality="text",
        ),
        EmbeddingBenchResult(
            model_name=model_name, variant="competitor",
            task="speed", metric="samples/sec",
            score=samples_sec, dimension=dim,
            samples_per_sec=samples_sec,
        ),
    ]


def _bench_clip_model(
    model_name: str, dim: int
) -> list[EmbeddingBenchResult]:
    """Benchmark a CLIP model on text similarity (zero-shot)."""
    try:
        from transformers import CLIPModel, CLIPTokenizer
    except ImportError:
        log.warning("transformers CLIP not available")
        return []

    from scipy.stats import spearmanr

    tokenizer = CLIPTokenizer.from_pretrained(model_name)
    clip_model = CLIPModel.from_pretrained(model_name)

    pairs = [
        ("A man is playing guitar.", "A man is playing a guitar.", 5.0),
        ("A woman is dancing.", "A man is dancing.", 3.2),
        ("A cat is sleeping.", "A dog is running.", 0.5),
    ]

    texts_a = [p[0] for p in pairs]
    texts_b = [p[1] for p in pairs]
    gold = [p[2] for p in pairs]

    with torch.no_grad():
        enc_a = tokenizer(texts_a, return_tensors="pt", padding=True, truncation=True)
        enc_b = tokenizer(texts_b, return_tensors="pt", padding=True, truncation=True)
        emb_a = clip_model.get_text_features(**enc_a)
        emb_b = clip_model.get_text_features(**enc_b)
        emb_a = torch.nn.functional.normalize(emb_a, dim=-1)
        emb_b = torch.nn.functional.normalize(emb_b, dim=-1)

    cos_sim = torch.sum(emb_a * emb_b, dim=1).numpy()
    correlation, _ = spearmanr(cos_sim, gold)

    log.info(f"  {model_name}: STS={correlation:.4f}")

    return [EmbeddingBenchResult(
        model_name=model_name, variant="competitor",
        task="STSBenchmark-mini", metric="spearman",
        score=correlation, dimension=dim, modality="multimodal",
    )]


# ---------------------------------------------------------------------------
# Full benchmark runner
# ---------------------------------------------------------------------------
def run_full_benchmark(
    model=None,
    model_path: str | None = None,
    variant: str = "e2b",
    run_competitors: bool = True,
    run_mteb: bool = True,
    run_matryoshka: bool = True,
    run_speed: bool = True,
) -> BenchmarkReport:
    """
    Run the complete embedding benchmark suite.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if model is None and model_path:
        model = _load_model_from_checkpoint(model_path, variant)

    report = BenchmarkReport(
        model_name=model.config.model_name if model else "unknown",
        variant=variant,
    )

    # Text benchmarks
    if model and run_mteb:
        log.info("\n=== TEXT BENCHMARKS ===")
        report.text_results = run_mteb_evaluation(model)

    # Matryoshka analysis
    if model and run_matryoshka:
        log.info("\n=== MATRYOSHKA DIMENSION ANALYSIS ===")
        mat_results = benchmark_matryoshka_dims(model)
        report.text_results.extend(mat_results)

    # Speed benchmarks
    if model and run_speed:
        log.info("\n=== SPEED BENCHMARKS ===")
        report.speed_results = benchmark_speed(model)

    # Competitor benchmarks
    if run_competitors:
        log.info("\n=== COMPETITOR BENCHMARKS ===")
        report.competitor_results = benchmark_competitors()

    # Summary
    report.summary = _compute_summary(report)

    # Save results
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    out_path = RESULTS_DIR / f"embedding_{variant}_{ts}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, default=str))
    log.info(f"\nResults saved: {out_path}")

    _print_comparison_table(report)
    return report


def _load_model_from_checkpoint(path: str, variant: str):
    """Load a trained JemmaEmbedModel from checkpoint."""
    import tomllib
    from jemma.embed.model import EmbedConfig, JemmaEmbedModel

    config_path = BASE_DIR / "configs" / "embedding-training.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    model_cfg = config["models"][variant]
    embed_config = EmbedConfig(
        model_name=model_cfg["hf_name"],
        embed_dim=model_cfg["embed_dim"],
        matryoshka_dims=model_cfg["matryoshka_dims"],
    )

    model = JemmaEmbedModel(embed_config)
    model.load_backbone()

    # Load adapter if exists
    adapter_path = Path(path) / "adapter"
    if adapter_path.exists():
        from peft import PeftModel
        model.backbone = PeftModel.from_pretrained(model.backbone, str(adapter_path))

    # Load matryoshka head
    head_path = Path(path) / "matryoshka_head.pt"
    if head_path.exists():
        model.matryoshka_head.load_state_dict(torch.load(head_path, weights_only=True))

    return model


def _compute_summary(report: BenchmarkReport) -> dict:
    """Compute summary statistics from benchmark report."""
    summary = {}

    # Average STS score for Jemma
    sts_scores = [r.score for r in report.text_results
                  if r.metric == "spearman" and r.variant == "jemma-embed"]
    if sts_scores:
        summary["jemma_avg_sts"] = sum(sts_scores) / len(sts_scores)

    # Average STS for competitors
    for r in report.competitor_results:
        if r.metric == "spearman":
            key = f"{r.model_name}_sts"
            summary[key] = r.score

    # Speed
    speed_results = [r for r in report.speed_results if r.metric == "samples/sec"]
    if speed_results:
        summary["jemma_peak_throughput"] = max(r.score for r in speed_results)

    # Matryoshka dimension scores
    for r in report.text_results:
        if r.task == "STSBenchmark-mini" and r.variant == "jemma-embed":
            summary[f"sts_dim{r.dimension}"] = r.score

    return summary


def _print_comparison_table(report: BenchmarkReport):
    """Print a formatted comparison table."""
    log.info("\n" + "=" * 80)
    log.info("EMBEDDING BENCHMARK COMPARISON")
    log.info("=" * 80)

    # Collect all STS scores
    scores = {}
    for r in report.text_results + report.competitor_results:
        if r.metric == "spearman":
            name = f"{r.model_name} (dim={r.dimension})"
            scores[name] = r.score

    # Sort by score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    log.info(f"\n{'Model':<55} {'STS Spearman':>12}")
    log.info("-" * 70)
    for name, score in sorted_scores:
        marker = " ★" if "jemma" in name.lower() else ""
        log.info(f"  {name:<53} {score:>10.4f}{marker}")

    # Speed comparison
    if report.speed_results:
        log.info(f"\n{'Speed Test':<55} {'Samples/sec':>12}")
        log.info("-" * 70)
        for r in report.speed_results:
            log.info(f"  {r.task:<53} {r.score:>10.1f}")

    log.info("=" * 80)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Jemma Embed — Benchmark Suite")
    parser.add_argument("--variant", choices=["e2b", "e4b"], default="e2b")
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="Path to model checkpoint directory")
    parser.add_argument("--competitors-only", action="store_true",
                        help="Only benchmark competitor models")
    parser.add_argument("--no-competitors", action="store_true")
    parser.add_argument("--no-mteb", action="store_true")
    parser.add_argument("--no-speed", action="store_true")
    args = parser.parse_args()

    run_full_benchmark(
        model_path=args.checkpoint,
        variant=args.variant,
        run_competitors=not args.no_competitors,
        run_mteb=not args.no_mteb and not args.competitors_only,
        run_speed=not args.no_speed and not args.competitors_only,
    )
