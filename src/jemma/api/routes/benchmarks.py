from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from jemma.api.schemas import PairwiseBenchmarkRequest, SoloBenchmarkRequest, StressBenchmarkRequest
from jemma.core.types import PairwiseBenchmarkManifest, SoloBenchmarkManifest, StressBenchmarkManifest

router = APIRouter(tags=["benchmarks"])


@router.get("/benchmarks/presets")
def benchmark_presets() -> dict[str, object]:
    return {
        "presets": [
            {"name": "gemma-solo-eval", "kind": "solo", "manifest_path": "manifests/benchmarks/gemma-solo-eval.toml"},
            {"name": "gemma-head-to-head", "kind": "pairwise", "manifest_path": "manifests/benchmarks/gemma-head-to-head.toml"},
            {
                "name": "gemma-stress-vs-reasoning",
                "kind": "stress",
                "manifest_path": "manifests/benchmarks/gemma-stress-vs-reasoning.toml",
            },
        ]
    }


@router.post("/jobs/benchmark/solo")
def submit_solo_benchmark(request: Request, body: SoloBenchmarkRequest) -> dict[str, object]:
    config = request.app.state.config
    manifest = SoloBenchmarkManifest(
        name=body.name,
        models=body.models,
        dataset_path=_resolve_repo_path(config.repo_root, body.dataset_path),
        repetitions=body.repetitions,
        warmup_runs=body.warmup_runs,
        options=body.options,
    )
    return {"job": request.app.state.jobs.submit_solo(manifest, visibility=body.visibility)}


@router.post("/jobs/benchmark/pairwise")
def submit_pairwise_benchmark(request: Request, body: PairwiseBenchmarkRequest) -> dict[str, object]:
    config = request.app.state.config
    manifest = PairwiseBenchmarkManifest(
        name=body.name,
        left_model=body.left_model,
        right_model=body.right_model,
        dataset_path=_resolve_repo_path(config.repo_root, body.dataset_path),
        repetitions=body.repetitions,
        warmup_runs=body.warmup_runs,
        options=body.options,
    )
    return {"job": request.app.state.jobs.submit_pairwise(manifest, visibility=body.visibility)}


@router.post("/jobs/benchmark/stress")
def submit_stress_benchmark(request: Request, body: StressBenchmarkRequest) -> dict[str, object]:
    config = request.app.state.config
    manifest = StressBenchmarkManifest(
        name=body.name,
        models=body.models,
        standard_dataset_path=_resolve_repo_path(config.repo_root, body.standard_dataset_path),
        reasoning_dataset_path=_resolve_repo_path(config.repo_root, body.reasoning_dataset_path),
        repetitions=body.repetitions,
        warmup_runs=body.warmup_runs,
        options=body.options,
    )
    return {"job": request.app.state.jobs.submit_stress(manifest, visibility=body.visibility)}


def _resolve_repo_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else repo_root / path

