from __future__ import annotations

import json
import subprocess

from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig


class TailscaleAdapter:
    name = "tailscale"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = PolicyEngine(config)

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "actions": ["observe_status", "list_peers"]}

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        return self.policy.validate(self.name, action, confirmed=confirmed)

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        allowed, reasons = self.validate(action, params, confirmed=confirmed)
        if not allowed:
            return {"ok": False, "error": "; ".join(reasons)}

        completed = subprocess.run(
            ["tailscale", "status", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0:
            return {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip()}

        payload = json.loads(completed.stdout or "{}")
        if action == "list_peers":
            peers = payload.get("Peer", {})
            return {"ok": True, "peers": list(peers.keys()), "peer_count": len(peers)}
        return {"ok": True, "status": payload}

