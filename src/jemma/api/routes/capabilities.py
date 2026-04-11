from __future__ import annotations

from fastapi import APIRouter, Request

from jemma.api.schemas import CapabilityDescriptor, CapabilityListResponse
from jemma.capabilities.registry import build_capability_registry

router = APIRouter(tags=["capabilities"])

_CAPABILITY_SUMMARIES = {
    "discord": "Read-only Discord server blueprint and invite planning for the public demo surface.",
    "tailscale": "Read-only mesh VPN visibility for remote-first workstation reachability checks.",
    "router_status": "Network reachability and DNS observation for trusted LAN validation.",
    "hue": "Bridge and light inspection with confirmation-gated scene activation.",
    "smartplug": "Confirmation-gated smart plug status and power controls for approved targets only.",
}


@router.get("/capabilities", response_model=CapabilityListResponse)
def list_capabilities(request: Request) -> CapabilityListResponse:
    config = request.app.state.config
    registry = build_capability_registry(config)
    capabilities: list[CapabilityDescriptor] = []

    for name, adapter in registry.items():
        described = adapter.describe()
        policy = config.capability_policies.get(name)
        capabilities.append(
            CapabilityDescriptor(
                name=str(described.get("name", name)),
                actions=[str(action) for action in described.get("actions", [])],
                allowlisted_targets=list(policy.allowlisted_targets) if policy else [],
                require_confirmation=policy.require_confirmation if policy else True,
                summary=_CAPABILITY_SUMMARIES.get(name, "Capability available through the local Jemma control plane."),
            )
        )

    capabilities.sort(key=lambda item: item.name)
    return CapabilityListResponse(capabilities=capabilities)


@router.get("/skills", response_model=CapabilityListResponse)
def list_skills(request: Request) -> CapabilityListResponse:
    return list_capabilities(request)
