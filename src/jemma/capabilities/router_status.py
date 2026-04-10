from __future__ import annotations

import platform
import socket
import subprocess

from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig


class RouterStatusAdapter:
    name = "router_status"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = PolicyEngine(config)
        self.router_config = config.raw_sections.get("lan", {}).get("router_status", {})

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "actions": ["observe_gateway", "observe_dns", "observe_internet"]}

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        return self.policy.validate(self.name, action, confirmed=confirmed)

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        allowed, reasons = self.validate(action, params, confirmed=confirmed)
        if not allowed:
            return {"ok": False, "error": "; ".join(reasons)}

        if action == "observe_gateway":
            gateway_ip = str(self.router_config.get("gateway_ip", "192.168.1.1"))
            ping_flag = "-n" if platform.system() == "Windows" else "-c"
            completed = subprocess.run(
                ["ping", ping_flag, "1", gateway_ip],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return {
                "ok": completed.returncode == 0,
                "gateway_ip": gateway_ip,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }

        if action == "observe_dns":
            host = str(params.get("host", self.router_config.get("dns_test_host", "1.1.1.1")))
            try:
                result = socket.gethostbyname(host)
            except socket.gaierror as exc:
                return {"ok": False, "error": str(exc), "host": host}
            return {"ok": True, "host": host, "resolved_ip": result}

        if action == "observe_internet":
            host = str(params.get("host", "1.1.1.1"))
            port = int(params.get("port", 53))
            try:
                with socket.create_connection((host, port), timeout=3):
                    return {"ok": True, "host": host, "port": port}
            except OSError as exc:
                return {"ok": False, "host": host, "port": port, "error": str(exc)}

        return {"ok": False, "error": f"unsupported action {action!r}"}

