from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from jemma.agent.loop import AgentLoop
from jemma.benchmarks.runner import BenchmarkRunner
from jemma.capabilities.registry import build_capability_registry
from jemma.config.loader import load_app_config, load_objective, load_pairwise_manifest, load_solo_manifest
from jemma.core.store import ArtifactStore
from jemma.providers.registry import build_provider


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jemma autonomous benchmark framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check local provider health")

    solo = subparsers.add_parser("benchmark-solo", help="Run a solo benchmark manifest")
    solo.add_argument("--manifest", required=True)

    versus = subparsers.add_parser("benchmark-versus", help="Run a pairwise benchmark manifest")
    versus.add_argument("--manifest", required=True)

    objective = subparsers.add_parser("run-objective", help="Run an objective manifest")
    objective.add_argument("--manifest", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    config = load_app_config(repo_root)
    provider = build_provider(config)
    store = ArtifactStore(config)

    if args.command == "health":
        print(json.dumps(asdict(provider.health()), indent=2))
        return 0

    if args.command == "benchmark-solo":
        manifest = load_solo_manifest(repo_root, Path(args.manifest))
        runner = BenchmarkRunner(config, provider, store)
        print(json.dumps(runner.run_solo(manifest), indent=2, default=str))
        return 0

    if args.command == "benchmark-versus":
        manifest = load_pairwise_manifest(repo_root, Path(args.manifest))
        runner = BenchmarkRunner(config, provider, store)
        print(json.dumps(runner.run_pairwise(manifest), indent=2, default=str))
        return 0

    if args.command == "run-objective":
        objective = load_objective(Path(args.manifest))
        loop = AgentLoop(config, provider, store, build_capability_registry(config))
        print(json.dumps(asdict(loop.run_objective(objective)), indent=2, default=str))
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

