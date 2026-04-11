from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jemma.config.loader import load_app_config, load_pairwise_manifest, load_solo_manifest


class ConfigLoaderTests(unittest.TestCase):
    def test_load_app_config_registers_default_models_and_policies(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        config = load_app_config(repo_root)
        self.assertIn("gemma4-e4b-it-q8", config.models)
        self.assertIn("discord", config.capability_policies)
        self.assertIn("tailscale", config.capability_policies)
        self.assertFalse(config.actuation_enabled)

    def test_manifest_loaders_resolve_dataset_paths(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        solo = load_solo_manifest(repo_root, repo_root / "manifests" / "benchmarks" / "gemma-solo-eval.toml")
        versus = load_pairwise_manifest(repo_root, repo_root / "manifests" / "benchmarks" / "gemma-head-to-head.toml")
        self.assertEqual(solo.dataset_path, repo_root / "datasets" / "prompts" / "smoke.jsonl")
        self.assertEqual(versus.left_model, "gemma4-e4b-it-q8")


if __name__ == "__main__":
    unittest.main()

