from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jemma.api.routes import benchmarks, capabilities, chat, health, jobs, models, objectives, runs, system, training
from jemma.config.loader import load_app_config
from jemma.core.store import ArtifactStore
from jemma.providers.registry import build_provider
from jemma.services.jobs import JobManager


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def create_app() -> FastAPI:
    repo_root = _repo_root()
    config = load_app_config(repo_root)
    store = ArtifactStore(config)
    provider = build_provider(config)
    jobs_service = JobManager(config, provider, store)

    app = FastAPI(title="Jemma API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.config = config
    app.state.store = store
    app.state.provider = provider
    app.state.jobs = jobs_service

    app.include_router(health.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(capabilities.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(benchmarks.router, prefix="/api")
    app.include_router(objectives.router, prefix="/api")
    app.include_router(training.router, prefix="/api")

    @app.get("/")
    def root() -> dict[str, object]:
        return {
            "name": "jemma-api",
            "version": "0.2.0",
            "models": [asdict(item) for item in config.models.values()],
        }

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)

