from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jemma.core.policies import PolicyEngine
from jemma.core.types import AppConfig, CapabilityPolicy


class PolicyEngineTests(unittest.TestCase):
    def test_blocks_actuation_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            config = AppConfig(
                repo_root=root,
                state_dir=root / "state",
                artifacts_dir=root / "artifacts",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_timeout_s=120,
                default_model="m",
                planner_model="m",
                validator_model="m",
                fallback_model=None,
                max_steps=4,
                actuation_enabled=False,
                capability_policies={
                    "smartplug": CapabilityPolicy(
                        capability="smartplug",
                        allowed_actions=["observe_status", "power_on"],
                        allowlisted_targets=["demo-lamp"],
                        require_confirmation=True,
                    )
                },
                raw_sections={},
                models={},
            )
            allowed, reasons = PolicyEngine(config).validate(
                "smartplug",
                "power_on",
                target="demo-lamp",
                confirmed=True,
            )
            self.assertFalse(allowed)
            self.assertIn("actuation is disabled in config", reasons)

    def test_allows_read_only_status_checks(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            config = AppConfig(
                repo_root=root,
                state_dir=root / "state",
                artifacts_dir=root / "artifacts",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_timeout_s=120,
                default_model="m",
                planner_model="m",
                validator_model="m",
                fallback_model=None,
                max_steps=4,
                actuation_enabled=False,
                capability_policies={
                    "tailscale": CapabilityPolicy(
                        capability="tailscale",
                        allowed_actions=["observe_status"],
                        require_confirmation=False,
                    )
                },
                raw_sections={},
                models={},
            )
            allowed, reasons = PolicyEngine(config).validate("tailscale", "observe_status")
            self.assertTrue(allowed)
            self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()

