from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlencode

DISCORD_PERMISSION_BITS: dict[str, int] = {
    "VIEW_CHANNEL": 1 << 10,
    "SEND_MESSAGES": 1 << 11,
    "EMBED_LINKS": 1 << 14,
    "ATTACH_FILES": 1 << 15,
    "READ_MESSAGE_HISTORY": 1 << 16,
    "USE_APPLICATION_COMMANDS": 1 << 31,
    "MANAGE_THREADS": 1 << 34,
    "CREATE_PUBLIC_THREADS": 1 << 35,
    "CREATE_PRIVATE_THREADS": 1 << 36,
    "SEND_MESSAGES_IN_THREADS": 1 << 38,
    "MODERATE_MEMBERS": 1 << 40,
    "SEND_POLLS": 1 << 49,
    "BYPASS_SLOWMODE": 1 << 52,
}

DEFAULT_BOT_PERMISSIONS = [
    "VIEW_CHANNEL",
    "SEND_MESSAGES",
    "EMBED_LINKS",
    "ATTACH_FILES",
    "READ_MESSAGE_HISTORY",
    "USE_APPLICATION_COMMANDS",
    "MANAGE_THREADS",
    "CREATE_PUBLIC_THREADS",
    "CREATE_PRIVATE_THREADS",
    "SEND_MESSAGES_IN_THREADS",
    "MODERATE_MEMBERS",
    "SEND_POLLS",
    "BYPASS_SLOWMODE",
]


@dataclass(slots=True)
class DiscordOAuthInstallSpec:
    scopes: list[str]
    permission_names: list[str] = field(default_factory=list)
    permissions_int: str = "0"
    install_url: str | None = None
    redirect_uri: str | None = None
    guild_id: str | None = None


def permission_value(permission_names: list[str]) -> int:
    value = 0
    for name in permission_names:
        bit = DISCORD_PERMISSION_BITS.get(name)
        if bit is None:
            raise ValueError(f"unsupported Discord permission {name!r}")
        value |= bit
    return value


def build_authorize_url(
    *,
    client_id: str,
    scopes: list[str],
    permission_names: list[str] | None = None,
    guild_id: str | None = None,
    disable_guild_select: bool = True,
    redirect_uri: str | None = None,
    state: str | None = None,
) -> DiscordOAuthInstallSpec:
    chosen_permissions = list(permission_names or DEFAULT_BOT_PERMISSIONS)
    params: dict[str, str] = {
        "client_id": client_id,
        "scope": " ".join(scopes),
        "permissions": str(permission_value(chosen_permissions)),
    }
    if guild_id:
        params["guild_id"] = guild_id
    if disable_guild_select:
        params["disable_guild_select"] = "true"
    if redirect_uri:
        params["redirect_uri"] = redirect_uri
        params["response_type"] = "code"
    if state:
        params["state"] = state
    return DiscordOAuthInstallSpec(
        scopes=list(scopes),
        permission_names=chosen_permissions,
        permissions_int=params["permissions"],
        install_url=f"https://discord.com/oauth2/authorize?{urlencode(params)}",
        redirect_uri=redirect_uri,
        guild_id=guild_id,
    )
