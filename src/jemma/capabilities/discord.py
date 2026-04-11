from __future__ import annotations

from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig
from jemma.discord.blueprint import build_research_server_blueprint_from_app_config


class DiscordAdapter:
    name = "discord"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.policy = PolicyEngine(config)

    def describe(self) -> dict[str, object]:
        return {
            "name": self.name,
            "actions": ["observe_blueprint", "build_invite_url", "render_channel_matrix", "render_ruleset"],
        }

    def validate(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> tuple[bool, list[str]]:
        return self.policy.validate(self.name, action, confirmed=confirmed)

    def execute(self, action: str, params: dict[str, object], *, confirmed: bool = False) -> dict[str, object]:
        allowed, reasons = self.validate(action, params, confirmed=confirmed)
        if not allowed:
            return {"ok": False, "error": "; ".join(reasons)}

        blueprint = build_research_server_blueprint_from_app_config(
            self.config,
            client_id=_as_optional_string(params.get("client_id")),
            guild_id=_as_optional_string(params.get("guild_id")),
            redirect_uri=_as_optional_string(params.get("redirect_uri")),
        )
        if action == "observe_blueprint":
            return {"ok": True, "blueprint": blueprint.to_dict()}
        if action == "build_invite_url":
            return {
                "ok": blueprint.oauth.install_url is not None,
                "install_url": blueprint.oauth.install_url,
                "permissions_int": blueprint.oauth.permissions_int,
                "permission_names": blueprint.oauth.permission_names,
                "scopes": blueprint.oauth.scopes,
                "error": None if blueprint.oauth.install_url else "Discord client_id is not configured",
            }
        if action == "render_channel_matrix":
            return {
                "ok": True,
                "channels": [
                    {
                        "name": channel.name,
                        "kind": channel.kind,
                        "visibility": channel.visibility,
                        "allow_roles": channel.allow_roles,
                        "default_thread_mode": channel.default_thread_mode,
                    }
                    for channel in blueprint.channels
                ],
            }
        if action == "render_ruleset":
            return {
                "ok": True,
                "rules": [
                    {"title": rule.title, "summary": rule.summary, "enforcement": rule.enforcement}
                    for rule in blueprint.rules
                ],
            }
        return {"ok": False, "error": f"unsupported action {action!r}"}


def _as_optional_string(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
