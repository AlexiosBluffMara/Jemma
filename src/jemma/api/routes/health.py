from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health(request: Request) -> dict[str, object]:
    provider = request.app.state.provider
    return {"ok": True, "provider": asdict(provider.health())}

