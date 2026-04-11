from __future__ import annotations

import asyncio
import json

from jemma.core.types import AppConfig, ChatRequest
from jemma.discord.blueprint import DiscordServerBlueprint, build_research_server_blueprint_from_app_config
from jemma.providers.base import ChatProvider


def _truncate(text: str, *, limit: int = 1800) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _format_rules(blueprint: DiscordServerBlueprint) -> str:
    return "\n".join(f"- **{rule.title}**: {rule.summary}" for rule in blueprint.rules)


def _system_prompt(blueprint: DiscordServerBlueprint) -> str:
    return (
        f"You are Jemma, the research Discord assistant for {blueprint.server_name}. "
        "Use professional language, welcome newcomers, and keep discussions evidence-based. "
        "Prefer forum-first organization, route durable code to GitHub, and escalate safety or conduct concerns to moderators. "
        f"Canonical repository: {blueprint.github_repo or 'the linked GitHub repo'}.\n\n"
        f"Core rules:\n{_format_rules(blueprint)}"
    )


class DiscordBotRuntime:
    def __init__(
        self,
        config: AppConfig,
        provider: ChatProvider,
        *,
        blueprint: DiscordServerBlueprint | None = None,
        sync_commands: bool = False,
    ) -> None:
        self.config = config
        self.provider = provider
        self.blueprint = blueprint or build_research_server_blueprint_from_app_config(config)
        self.sync_commands = sync_commands

    def run(self, token: str) -> None:
        try:
            import discord
            from discord import app_commands
        except ImportError as exc:
            raise RuntimeError("discord.py is required. Install project dependencies before running the bot.") from exc

        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        runtime = self

        class JemmaDiscordClient(discord.Client):
            def __init__(self) -> None:
                super().__init__(intents=intents)
                self.tree = app_commands.CommandTree(self)

            async def setup_hook(self) -> None:
                if runtime.sync_commands:
                    await self.tree.sync()

        client = JemmaDiscordClient()

        @client.event
        async def on_ready() -> None:
            print(f"Discord bot ready as {client.user}")

        @client.tree.command(name="ask", description="Ask Jemma a research or repo question")
        @app_commands.describe(prompt="Question for the assistant", private="Whether the response should be ephemeral")
        async def ask(interaction: discord.Interaction, prompt: str, private: bool = False) -> None:
            await interaction.response.defer(ephemeral=private, thinking=True)
            response = await asyncio.to_thread(
                runtime.provider.chat,
                ChatRequest(
                    model=runtime.config.default_model,
                    system=_system_prompt(runtime.blueprint),
                    messages=[{"role": "user", "content": prompt}],
                ),
            )
            await interaction.followup.send(_truncate(response.content), ephemeral=private)

        @client.tree.command(name="blueprint", description="Show the Discord server operating blueprint")
        async def blueprint(interaction: discord.Interaction) -> None:
            channels = ", ".join(channel.name for channel in runtime.blueprint.channels[:6])
            message = (
                f"**{runtime.blueprint.server_name}**\n"
                f"{runtime.blueprint.summary}\n\n"
                f"Primary channels: {channels}\n"
                f"GitHub source of truth: {runtime.blueprint.github_repo}\n"
                f"OAuth ready: {'yes' if runtime.blueprint.oauth.install_url else 'needs DISCORD_CLIENT_ID'}"
            )
            await interaction.response.send_message(message, ephemeral=True)

        @client.tree.command(name="policy", description="Show the moderation policy summary")
        async def policy(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(_truncate(_format_rules(runtime.blueprint)), ephemeral=True)

        @client.tree.command(name="intake", description="Open a public or private research intake thread")
        @app_commands.describe(title="Short thread title", private="Create a moderator-only private thread")
        async def intake(interaction: discord.Interaction, title: str, private: bool = False) -> None:
            channel = interaction.channel
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Run this command from a text channel where the bot can create threads.",
                    ephemeral=True,
                )
                return
            thread_type = discord.ChannelType.private_thread if private else discord.ChannelType.public_thread
            thread = await channel.create_thread(
                name=title[:100],
                type=thread_type,
                auto_archive_duration=1440,
                invitable=not private,
                reason="Jemma research intake thread",
            )
            payload = {
                "title": title,
                "private": private,
                "created_by": getattr(interaction.user, "name", "unknown"),
                "recommended_tags": ["idea", "paper", "code", "dataset"],
            }
            await thread.send(
                "Thread created for structured intake.\n"
                "Please attach context, GitHub links, datasets, or reproducible steps.\n"
                f"```json\n{_truncate(json.dumps(payload, indent=2), limit=1200)}\n```"
            )
            await interaction.response.send_message(f"Created thread {thread.mention}", ephemeral=True)

        client.run(token)
