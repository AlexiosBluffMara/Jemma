from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field

from jemma.core.types import AppConfig
from jemma.discord.oauth import DEFAULT_BOT_PERMISSIONS, DiscordOAuthInstallSpec, build_authorize_url


@dataclass(slots=True)
class DiscordRoleTemplate:
    name: str
    purpose: str
    base_permissions: list[str] = field(default_factory=list)
    monetized: bool = False


@dataclass(slots=True)
class DiscordChannelTemplate:
    name: str
    kind: str
    purpose: str
    visibility: str
    allow_roles: list[str] = field(default_factory=list)
    deny_roles: list[str] = field(default_factory=list)
    slowmode_s: int = 0
    default_thread_mode: str | None = None
    auto_archive_minutes: int = 1440
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DiscordAutomationRule:
    name: str
    trigger: str
    actions: list[str]
    rationale: str


@dataclass(slots=True)
class DiscordRule:
    title: str
    summary: str
    enforcement: str


@dataclass(slots=True)
class DiscordStorageWorkflow:
    name: str
    preferred_surface: str
    guidance: str


@dataclass(slots=True)
class DiscordServerBlueprint:
    server_name: str
    community_name: str
    summary: str
    github_repo: str
    roles: list[DiscordRoleTemplate]
    channels: list[DiscordChannelTemplate]
    rules: list[DiscordRule]
    automations: list[DiscordAutomationRule]
    storage_workflows: list[DiscordStorageWorkflow]
    oauth: DiscordOAuthInstallSpec

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_research_server_blueprint(
    *,
    server_name: str,
    community_name: str,
    github_repo: str,
    subscriptions_enabled: bool = True,
    client_id: str | None = None,
    guild_id: str | None = None,
    redirect_uri: str | None = None,
    scopes: list[str] | None = None,
    entry_role: str = "visitor",
    member_role: str = "researcher",
    moderator_role: str = "moderator",
    bot_operator_role: str = "bot-operator",
    subscriber_role: str = "supporter",
) -> DiscordServerBlueprint:
    roles = [
        DiscordRoleTemplate(
            name=entry_role,
            purpose="Default role for every new arrival so anyone can read, introduce themselves, and join the open lobby immediately.",
            base_permissions=["VIEW_CHANNEL", "SEND_MESSAGES", "READ_MESSAGE_HISTORY", "USE_APPLICATION_COMMANDS"],
        ),
        DiscordRoleTemplate(
            name=member_role,
            purpose="Granted after rules acknowledgement or lightweight verification; unlocks project forums, code review, and artifact sharing.",
            base_permissions=[
                "VIEW_CHANNEL",
                "SEND_MESSAGES",
                "READ_MESSAGE_HISTORY",
                "ATTACH_FILES",
                "CREATE_PUBLIC_THREADS",
                "SEND_MESSAGES_IN_THREADS",
                "USE_APPLICATION_COMMANDS",
            ],
        ),
        DiscordRoleTemplate(
            name=moderator_role,
            purpose="Handles incident triage, thread cleanup, and professional-speech enforcement without needing full administrator access.",
            base_permissions=[
                "VIEW_CHANNEL",
                "SEND_MESSAGES",
                "READ_MESSAGE_HISTORY",
                "MANAGE_THREADS",
                "MODERATE_MEMBERS",
                "BYPASS_SLOWMODE",
                "USE_APPLICATION_COMMANDS",
            ],
        ),
        DiscordRoleTemplate(
            name=bot_operator_role,
            purpose="Owns bot configuration, webhook wiring, and GitHub or artifact automation controls.",
            base_permissions=DEFAULT_BOT_PERMISSIONS,
        ),
    ]
    if subscriptions_enabled:
        roles.append(
            DiscordRoleTemplate(
                name=subscriber_role,
                purpose="Monetized supporter lane for premium office hours, sponsor updates, or private implementation labs without gating initial entry.",
                base_permissions=["VIEW_CHANNEL", "SEND_MESSAGES", "READ_MESSAGE_HISTORY", "USE_APPLICATION_COMMANDS"],
                monetized=True,
            )
        )

    channels = [
        DiscordChannelTemplate(
            name="start-here",
            kind="text",
            purpose="Read-only landing page with rules, mission, and onboarding commands.",
            visibility="public-read",
            allow_roles=["@everyone"],
        ),
        DiscordChannelTemplate(
            name="open-lobby",
            kind="text",
            purpose="Low-friction conversation channel available to everyone from the start, with slowmode and active moderation.",
            visibility="public-write",
            allow_roles=["@everyone"],
            slowmode_s=30,
        ),
        DiscordChannelTemplate(
            name="introductions",
            kind="text",
            purpose="Structured introductions and intent setting for new members.",
            visibility="public-write",
            allow_roles=["@everyone"],
            slowmode_s=60,
        ),
        DiscordChannelTemplate(
            name="research-intake",
            kind="forum",
            purpose="Primary public forum where members open topic threads with required tags for ideas, papers, and problem statements.",
            visibility="public-write",
            allow_roles=["@everyone"],
            default_thread_mode="public",
            auto_archive_minutes=1440,
            tags=["paper", "idea", "question", "dataset", "ethics"],
        ),
        DiscordChannelTemplate(
            name="code-review",
            kind="forum",
            purpose="Threaded code review tied back to GitHub pull requests or snippets that should be promoted into the repo.",
            visibility="member-write",
            allow_roles=[member_role, moderator_role, bot_operator_role],
            default_thread_mode="public",
            auto_archive_minutes=4320,
            tags=["bug", "feature", "benchmark", "infra"],
        ),
        DiscordChannelTemplate(
            name="artifacts-and-datasets",
            kind="forum",
            purpose="Organized storage for datasets, model cards, experiment outputs, and reusable attachments with one thread per artifact family.",
            visibility="member-write",
            allow_roles=[member_role, moderator_role, bot_operator_role],
            default_thread_mode="public",
            auto_archive_minutes=10080,
            tags=["dataset", "checkpoint", "evaluation", "demo", "license"],
        ),
        DiscordChannelTemplate(
            name="repo-feed",
            kind="text",
            purpose="Webhook-only mirror of GitHub pushes, issues, pull requests, and Actions runs.",
            visibility="public-read",
            allow_roles=["@everyone", bot_operator_role],
        ),
        DiscordChannelTemplate(
            name="build-alerts",
            kind="text",
            purpose="High-signal CI and deployment alerts for maintainers.",
            visibility="member-read",
            allow_roles=[member_role, moderator_role, bot_operator_role],
        ),
        DiscordChannelTemplate(
            name="mod-intake",
            kind="forum",
            purpose="Private moderation intake where the bot opens private threads for reports, escalations, and policy decisions.",
            visibility="private-mod",
            allow_roles=[moderator_role, bot_operator_role],
            deny_roles=["@everyone"],
            default_thread_mode="private",
            auto_archive_minutes=10080,
            tags=["report", "spam", "conduct", "appeal", "security"],
        ),
    ]
    if subscriptions_enabled:
        channels.append(
            DiscordChannelTemplate(
                name="supporter-office-hours",
                kind="forum",
                purpose="Subscriber-only space for curated AMAs, deep dives, and sponsor-friendly implementation threads.",
                visibility="subscriber-write",
                allow_roles=[subscriber_role, moderator_role, bot_operator_role],
                default_thread_mode="private",
                auto_archive_minutes=4320,
                tags=["ama", "roadmap", "early-access"],
            )
        )

    rules = [
        DiscordRule(
            title="Professional speech required",
            summary="Members may disagree strongly, but insults, baiting, slurs, and hostile dogpiling are removed quickly.",
            enforcement="Immediate deletion plus timeout escalation for repeated behavior.",
        ),
        DiscordRule(
            title="Open entry, structured progression",
            summary="Everyone can read and join the open lobby immediately; higher-trust project areas unlock after rules acknowledgement or moderator verification.",
            enforcement="Role automation moves members from visitor to researcher once onboarding is complete.",
        ),
        DiscordRule(
            title="Research claims need evidence",
            summary="Strong claims should link papers, experiments, datasets, or reproducible code when possible.",
            enforcement="Bot nudges for citations; moderators can move unsupported claims into clarification threads.",
        ),
        DiscordRule(
            title="Sensitive data stays out",
            summary="No private credentials, personal data, or embargoed research artifacts in public channels.",
            enforcement="Flagged messages are quarantined into private moderator threads.",
        ),
    ]

    automations = [
        DiscordAutomationRule(
            name="onboarding-role-seed",
            trigger="Member joins the server",
            actions=[
                f"Assign the {entry_role} role",
                "Post onboarding instructions in the welcome flow",
                "Offer slash commands for rules acknowledgement and intake thread creation",
            ],
            rationale="Keeps the server open to everyone initially without exposing private or high-noise workspaces.",
        ),
        DiscordAutomationRule(
            name="professional-speech-moderation",
            trigger="New message or edited message arrives in public channels",
            actions=[
                "Run lightweight classification for harassment, spam, slurs, and research-policy violations",
                "Delete or hold risky content based on confidence",
                "Open a private moderator thread with message context for anything escalated",
            ],
            rationale="Maintains a professional tone while still allowing broad entry and active discussion.",
        ),
        DiscordAutomationRule(
            name="github-and-ci-bridge",
            trigger="GitHub webhook for pushes, pull requests, issues, or Actions status",
            actions=[
                "Send concise summaries into repo-feed",
                "Route failures into build-alerts",
                "Offer thread jump links back to GitHub for the canonical code review surface",
            ],
            rationale=f"Uses Discord as the coordination layer while keeping {github_repo} as the source of truth.",
        ),
        DiscordAutomationRule(
            name="artifact-indexing",
            trigger="A member uploads a file or large code sample",
            actions=[
                "Hash the attachment and record metadata in an artifact manifest",
                "Reply with licensing and retention guidance",
                "Recommend pushing durable code to GitHub and durable datasets to external storage when they outgrow Discord",
            ],
            rationale="Lets Discord act as a staging and discovery layer rather than fragile long-term storage.",
        ),
    ]

    storage_workflows = [
        DiscordStorageWorkflow(
            name="Code sharing",
            preferred_surface="GitHub repository plus repo-feed webhooks",
            guidance="Use Discord threads for review context and triage, but keep canonical code in GitHub pull requests, issues, and gists linked back into the server.",
        ),
        DiscordStorageWorkflow(
            name="Files and artifacts",
            preferred_surface="Discord attachments for intake, external artifact storage for retention",
            guidance="Treat Discord attachments as convenient intake and preview storage. Mirror important files into artifacts, datasets, or object storage and post the canonical link back into the thread.",
        ),
        DiscordStorageWorkflow(
            name="Research discussions",
            preferred_surface="Forum channels with required tags",
            guidance="Use forum posts as durable indexed discussions so each experiment, paper, or question has its own searchable thread instead of disappearing in chat scrollback.",
        ),
    ]

    effective_scopes = list(scopes or ["bot", "applications.commands"])
    oauth = DiscordOAuthInstallSpec(scopes=effective_scopes, permission_names=DEFAULT_BOT_PERMISSIONS)
    if client_id:
        oauth = build_authorize_url(
            client_id=client_id,
            scopes=effective_scopes,
            permission_names=DEFAULT_BOT_PERMISSIONS,
            guild_id=guild_id,
            redirect_uri=redirect_uri,
        )

    return DiscordServerBlueprint(
        server_name=server_name,
        community_name=community_name,
        summary="Open onboarding, forum-first research collaboration, subscriber lanes that do not block entry, and moderator-controlled private escalation threads.",
        github_repo=github_repo,
        roles=roles,
        channels=channels,
        rules=rules,
        automations=automations,
        storage_workflows=storage_workflows,
        oauth=oauth,
    )


def build_research_server_blueprint_from_app_config(
    config: AppConfig,
    *,
    client_id: str | None = None,
    guild_id: str | None = None,
    redirect_uri: str | None = None,
) -> DiscordServerBlueprint:
    default_config = config.raw_sections.get("default", {})
    discord_config = dict(default_config.get("discord", {}))
    oauth_config = dict(discord_config.get("oauth", {}))
    resolved_client_id = client_id or _read_env(oauth_config.get("client_id_env"))
    resolved_guild_id = guild_id or _read_env(oauth_config.get("guild_id_env"))
    resolved_redirect_uri = redirect_uri or _string_or_none(oauth_config.get("redirect_uri"))
    scopes = [str(scope) for scope in oauth_config.get("scopes", ["bot", "applications.commands"])]
    return build_research_server_blueprint(
        server_name=str(discord_config.get("server_name", "Research Discord")),
        community_name=str(discord_config.get("community_name", "Research Discord")),
        github_repo=str(discord_config.get("github_repo", "")),
        subscriptions_enabled=bool(discord_config.get("enable_server_subscriptions", True)),
        client_id=resolved_client_id,
        guild_id=resolved_guild_id,
        redirect_uri=resolved_redirect_uri,
        scopes=scopes,
        entry_role=str(discord_config.get("entry_role", "visitor")),
        member_role=str(discord_config.get("member_role", "researcher")),
        moderator_role=str(discord_config.get("moderator_role", "moderator")),
        bot_operator_role=str(discord_config.get("bot_operator_role", "bot-operator")),
        subscriber_role=str(discord_config.get("subscriber_role", "supporter")),
    )


def _read_env(name: object) -> str | None:
    if not name:
        return None
    return os.environ.get(str(name))


def _string_or_none(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
