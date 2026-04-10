from __future__ import annotations

import json
import os
from urllib import error, request

from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig


class SmartPlugAdapter:
    name = "smartplug"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = PolicyEngine(config)
        self.plug_config = config.raw_sections.get("lan", {}).get("smartplug", {})

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "actions": ["observe_status", "power_on", "power_off"]}

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        target = str(params.get("plug", ""))
        return self.policy.validate(self.name, action, target=target, confirmed=confirmed)

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        allowed, reasons = self.validate(action, params, confirmed=confirmed)
        if not allowed:
            return {"ok": False, "error": "; ".join(reasons)}

        endpoint = self.plug_config.get("endpoint")
        api_key_name = self.plug_config.get("api_key_env")
        if not endpoint:
            return {"ok": False, "error": "smartplug endpoint is not configured"}

        payload = {"plug": params.get("plug"), "action": action}
        headers = {"Content-Type": "application/json"}
        if api_key_name and os.environ.get(str(api_key_name)):
            headers["Authorization"] = f"Bearer {os.environ[str(api_key_name)]}"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                return {"ok": True, "payload": json.loads(response.read().decode("utf-8"))}
        except error.URLError as exc:
            return {"ok": False, "error": str(exc)}

