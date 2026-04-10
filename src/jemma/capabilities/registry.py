from __future__ import annotations

from jemma.capabilities.hue import HueAdapter
from jemma.capabilities.router_status import RouterStatusAdapter
from jemma.capabilities.smartplug import SmartPlugAdapter
from jemma.capabilities.tailscale import TailscaleAdapter
from jemma.core.types import AppConfig


def build_capability_registry(config: AppConfig) -> dict[str, object]:
    return {
        "tailscale": TailscaleAdapter(config),
        "router_status": RouterStatusAdapter(config),
        "hue": HueAdapter(config),
        "smartplug": SmartPlugAdapter(config),
    }

