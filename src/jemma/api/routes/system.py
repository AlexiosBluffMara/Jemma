from __future__ import annotations

from fastapi import APIRouter, Request

from jemma.services.telemetry import collect_runtime_telemetry

router = APIRouter(tags=["system"])


@router.get("/system")
def get_system(request: Request) -> dict[str, object]:
    config = request.app.state.config
    return collect_runtime_telemetry(config)

