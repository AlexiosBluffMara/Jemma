from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

router = APIRouter(tags=["models"])


@router.get("/models")
def list_models(request: Request) -> dict[str, object]:
    config = request.app.state.config
    return {"models": [asdict(model) for model in config.models.values()]}

