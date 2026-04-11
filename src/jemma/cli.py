from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import os
from pathlib import Path

from jemma.agent.loop import AgentLoop
from jemma.benchmarks.runner import BenchmarkRunner
from jemma.capabilities.registry import build_capability_registry
from jemma.config.loader import load_app_config, load_objective, load_pairwise_manifest, load_solo_manifest, load_stress_manifest
from jemma.core.store import ArtifactStore
from jemma.discord.blueprint import build_research_server_blueprint_from_app_config
from jemma.providers.registry import build_provider


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jemma autonomous benchmark framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check local provider health")

    solo = subparsers.add_parser("benchmark-solo", help="Run a solo benchmark manifest")
    solo.add_argument("--manifest", required=True)

    versus = subparsers.add_parser("benchmark-versus", help="Run a pairwise benchmark manifest")
    versus.add_argument("--manifest", required=True)

    stress = subparsers.add_parser("benchmark-stress", help="Run a stress benchmark manifest")
    stress.add_argument("--manifest", required=True)

    objective = subparsers.add_parser("run-objective", help="Run an objective manifest")
    objective.add_argument("--manifest", required=True)

    serve_api = subparsers.add_parser("serve-api", help="Run the Jemma HTTP API")
    serve_api.add_argument("--host", default="127.0.0.1")
    serve_api.add_argument("--port", default=8000, type=int)

    discord_blueprint = subparsers.add_parser("discord-blueprint", help="Render the Discord research server blueprint")
    discord_blueprint.add_argument("--client-id")
    discord_blueprint.add_argument("--guild-id")
    discord_blueprint.add_argument("--redirect-uri")

    discord_oauth = subparsers.add_parser("discord-oauth-url", help="Build the Discord bot OAuth install URL")
    discord_oauth.add_argument("--client-id")
    discord_oauth.add_argument("--guild-id")
    discord_oauth.add_argument("--redirect-uri")

    subparsers.add_parser("discord-setup-check", help="Report which Discord setup values are still missing")

    discord_bot = subparsers.add_parser("discord-run-bot", help="Run the Discord bot runtime")
    discord_bot.add_argument("--token-env", default="DISCORD_BOT_TOKEN")
    discord_bot.add_argument("--sync-commands", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    config = load_app_config(repo_root)
    provider = build_provider(config)
    store = ArtifactStore(config)

    if args.command == "health":
        print(json.dumps(asdict(provider.health()), indent=2))
        return 0

    if args.command == "benchmark-solo":
        manifest = load_solo_manifest(repo_root, Path(args.manifest))
        runner = BenchmarkRunner(config, provider, store)
        print(json.dumps(runner.run_solo(manifest), indent=2, default=str))
        return 0

    if args.command == "benchmark-versus":
        manifest = load_pairwise_manifest(repo_root, Path(args.manifest))
        runner = BenchmarkRunner(config, provider, store)
        print(json.dumps(runner.run_pairwise(manifest), indent=2, default=str))
        return 0

    if args.command == "benchmark-stress":
        manifest = load_stress_manifest(repo_root, Path(args.manifest))
        runner = BenchmarkRunner(config, provider, store)
        print(json.dumps(runner.run_stress(manifest), indent=2, default=str))
        return 0

    if args.command == "run-objective":
        objective = load_objective(Path(args.manifest))
        loop = AgentLoop(config, provider, store, build_capability_registry(config))
        print(json.dumps(asdict(loop.run_objective(objective)), indent=2, default=str))
        return 0

    if args.command == "serve-api":
        import uvicorn

        from jemma.api.app import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port)
        return 0

    if args.command == "discord-blueprint":
        blueprint = build_research_server_blueprint_from_app_config(
            config,
            client_id=args.client_id,
            guild_id=args.guild_id,
            redirect_uri=args.redirect_uri,
        )
        print(json.dumps(blueprint.to_dict(), indent=2))
        return 0

    if args.command == "discord-oauth-url":
        blueprint = build_research_server_blueprint_from_app_config(
            config,
            client_id=args.client_id,
            guild_id=args.guild_id,
            redirect_uri=args.redirect_uri,
        )
        print(json.dumps(asdict(blueprint.oauth), indent=2))
        return 0

    if args.command == "discord-setup-check":
        discord_defaults = dict(config.raw_sections.get("default", {}).get("discord", {}))
        oauth_defaults = dict(discord_defaults.get("oauth", {}))
        env_checks = [
            {
                "name": "DISCORD_BOT_TOKEN",
                "required": True,
                "purpose": "Run the bot runtime and slash commands.",
                "present": bool(os.environ.get("DISCORD_BOT_TOKEN")),
            },
            {
                "name": str(oauth_defaults.get("client_id_env", "DISCORD_CLIENT_ID")),
                "required": True,
                "purpose": "Generate the OAuth install URL and identify the Discord application.",
                "present": bool(os.environ.get(str(oauth_defaults.get("client_id_env", "DISCORD_CLIENT_ID")))),
            },
            {
                "name": str(oauth_defaults.get("guild_id_env", "DISCORD_GUILD_ID")),
                "required": True,
                "purpose": "Preselect your Discord server during bot installation.",
                "present": bool(os.environ.get(str(oauth_defaults.get("guild_id_env", "DISCORD_GUILD_ID")))),
            },
            {
                "name": "DISCORD_CLIENT_SECRET",
                "required": False,
                "purpose": "Only needed if you build a full OAuth callback flow or external dashboard.",
                "present": bool(os.environ.get("DISCORD_CLIENT_SECRET")),
            },
        ]
        missing_required = [item["name"] for item in env_checks if item["required"] and not item["present"]]
        print(
            json.dumps(
                {
                    "server_name": discord_defaults.get("server_name"),
                    "github_repo": discord_defaults.get("github_repo"),
                    "redirect_uri": oauth_defaults.get("redirect_uri"),
                    "ready": not missing_required,
                    "missing_required": missing_required,
                    "checks": env_checks,
                    "next_steps": [
                        "Create a Discord application and bot in the Discord Developer Portal.",
                        "Copy the application ID into DISCORD_CLIENT_ID.",
                        "Copy your server ID into DISCORD_GUILD_ID.",
                        "Copy the bot token into DISCORD_BOT_TOKEN.",
                        "Run `jemma discord-oauth-url` and open the generated install URL.",
                        "After inviting the bot, run `jemma discord-run-bot --sync-commands`.",
                    ],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "discord-run-bot":
        token = os.environ.get(args.token_env)
        if not token:
            raise RuntimeError(f"{args.token_env} is not set")
        from jemma.discord.bot import DiscordBotRuntime

        runtime = DiscordBotRuntime(
            config,
            provider,
            blueprint=build_research_server_blueprint_from_app_config(config),
            sync_commands=args.sync_commands,
        )
        runtime.run(token)
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

