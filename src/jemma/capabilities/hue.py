from __future__ import annotations

import json
import os
from urllib import error, request

from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig


class HueAdapter:
    name = "hue"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = PolicyEngine(config)
        self.hue_config = config.raw_sections.get("lan", {}).get("hue", {})

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "actions": ["observe_bridge", "observe_lights", "activate_scene"]}

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        target = None
        if action == "activate_scene":
            target = str(params.get("room", ""))
        return self.policy.validate(self.name, action, target=target, confirmed=confirmed)

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        allowed, reasons = self.validate(action, params, confirmed=confirmed)
        if not allowed:
            return {"ok": False, "error": "; ".join(reasons)}

        bridge_ip = self.hue_config.get("bridge_ip")
        app_key = os.environ.get("HUE_APP_KEY")
        if not bridge_ip or not app_key:
            return {"ok": False, "error": "Hue bridge_ip or HUE_APP_KEY is not configured"}

        if action == "observe_bridge":
            return self._request_json("GET", bridge_ip, "/clip/v2/resource/bridge", app_key)
        if action == "observe_lights":
            return self._request_json("GET", bridge_ip, "/clip/v2/resource/light", app_key)
        if action == "activate_scene":
            scene_id = params.get("scene_id")
            if not scene_id:
                return {"ok": False, "error": "scene_id is required"}
            payload = {"recall": {"action": "active"}}
            return self._request_json("PUT", bridge_ip, f"/clip/v2/resource/scene/{scene_id}", app_key, payload)
        return {"ok": False, "error": f"unsupported action {action!r}"}

    @staticmethod
    def _request_json(
        method: str,
        bridge_ip: str,
        path: str,
        app_key: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        body = None
        headers = {"hue-application-key": app_key, "Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(f"https://{bridge_ip}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=10) as response:
                return {"ok": True, "payload": json.loads(response.read().decode("utf-8"))}
        except error.URLError as exc:
            return {"ok": False, "error": str(exc)}

