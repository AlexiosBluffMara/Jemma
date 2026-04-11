from __future__ import annotations

import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jemma.cli import main
from jemma.config.loader import load_app_config
from jemma.discord.blueprint import build_research_server_blueprint_from_app_config
from jemma.discord.oauth import build_authorize_url, permission_value


class DiscordBlueprintTests(unittest.TestCase):
    def test_permission_value_combines_expected_flags(self) -> None:
        permissions = permission_value(["SEND_MESSAGES", "CREATE_PRIVATE_THREADS"])
        self.assertEqual(permissions, (1 << 11) | (1 << 36))

    def test_build_authorize_url_contains_guild_and_permissions(self) -> None:
        oauth = build_authorize_url(
            client_id="123456",
            scopes=["bot", "applications.commands"],
            permission_names=["SEND_MESSAGES", "CREATE_PRIVATE_THREADS"],
            guild_id="654321",
            redirect_uri="http://127.0.0.1/callback",
        )
        self.assertIn("client_id=123456", oauth.install_url or "")
        self.assertIn("guild_id=654321", oauth.install_url or "")
        self.assertIn(f"permissions={permission_value(['SEND_MESSAGES', 'CREATE_PRIVATE_THREADS'])}", oauth.install_url or "")

    def test_blueprint_contains_open_entry_and_private_moderation(self) -> None:
        config = load_app_config(Path(__file__).resolve().parents[1])
        blueprint = build_research_server_blueprint_from_app_config(config, client_id="123456")
        channels = {channel.name: channel for channel in blueprint.channels}
        self.assertIn("open-lobby", channels)
        self.assertEqual(channels["open-lobby"].visibility, "public-write")
        self.assertIn("mod-intake", channels)
        self.assertEqual(channels["mod-intake"].default_thread_mode, "private")
        self.assertTrue(blueprint.oauth.install_url)

    def test_setup_check_reports_missing_values(self) -> None:
        stdout = StringIO()
        with patch.dict("os.environ", {}, clear=True), patch("sys.stdout", stdout):
            exit_code = main(["discord-setup-check"])
        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn('"ready": false', output)
        self.assertIn("DISCORD_CLIENT_ID", output)
        self.assertIn("DISCORD_GUILD_ID", output)
        self.assertIn("DISCORD_BOT_TOKEN", output)


if __name__ == "__main__":
    unittest.main()
