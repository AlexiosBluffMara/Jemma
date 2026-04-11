from __future__ import annotations

from fastapi import APIRouter, Request

from jemma.agent.loop import AgentLoop
from jemma.capabilities.registry import build_capability_registry
from jemma.config.loader import load_objective

router = APIRouter(tags=["objectives"])


@router.get("/objectives")
def list_objectives() -> dict[str, object]:
    return {
        "objectives": [
            {
                "name": "lan-watch",
                "manifest_path": "manifests/objectives/lan-watch.toml",
                "description": "Inspect local network readiness for benchmark execution.",
            }
        ]
    }


@router.post("/objectives/lan-watch")
def run_lan_watch(request: Request) -> dict[str, object]:
    config = request.app.state.config
    provider = request.app.state.provider
    store = request.app.state.store
    objective = load_objective(config.repo_root / "manifests" / "objectives" / "lan-watch.toml")
    loop = AgentLoop(config, provider, store, build_capability_registry(config))
    result = loop.run_objective(objective)
    return {
        "ok": result.ok,
        "objective": result.objective,
        "summary": result.summary,
        "artifact_dir": str(result.artifact_dir),
    }

