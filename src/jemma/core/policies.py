from __future__ import annotations

from pathlib import Path

from jemma.core.types import AppConfig


class PolicyEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def validate(
        self,
        capability: str,
        action: str,
        *,
        target: str | None = None,
        confirmed: bool = False,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        policy = self.config.capability_policies.get(capability)
        if policy is None:
            reasons.append(f"capability {capability!r} is not registered")
            return False, reasons

        if action not in policy.allowed_actions:
            reasons.append(f"action {action!r} is not allowed for {capability}")

        kill_switch = self.config.state_dir / "disable_actuation.flag"
        is_observe_action = action.startswith("observe") or action.endswith("status")
        if kill_switch.exists() and not is_observe_action:
            reasons.append("global actuation kill switch is enabled")

        if not self.config.actuation_enabled and not is_observe_action:
            reasons.append("actuation is disabled in config")

        if policy.allowlisted_targets and target and target not in policy.allowlisted_targets:
            reasons.append(f"target {target!r} is not allowlisted for {capability}")

        if policy.require_confirmation and not is_observe_action and not confirmed:
            reasons.append("confirmation is required for this action")

        return not reasons, reasons

