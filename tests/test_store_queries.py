from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jemma.core.store import ArtifactStore
from jemma.core.types import AppConfig, CapabilityPolicy


class ArtifactStoreTests(unittest.TestCase):
    def test_run_queries_return_written_summary_and_events(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            config = AppConfig(
                repo_root=root,
                state_dir=root / "state",
                artifacts_dir=root / "artifacts",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_timeout_s=120,
                llamacpp_base_url="http://127.0.0.1:8080",
                llamacpp_timeout_s=120,
                default_model="m",
                planner_model="m",
                validator_model="m",
                fallback_model=None,
                max_steps=4,
                actuation_enabled=False,
                capability_policies={"tailscale": CapabilityPolicy("tailscale", ["observe_status"])},
                raw_sections={},
                models={},
            )
            store = ArtifactStore(config)
            run_id, artifact_dir = store.create_run("solo-benchmark", "demo")
            store.append_event(run_id, "scenario_completed", {"passed": True})
            store.write_json(artifact_dir / "summary.json", {"pass_rate": 1.0})
            store.write_json(artifact_dir / "raw_results.json", [{"scenario_id": "one"}])

            self.assertEqual(store.get_run(run_id)["name"], "demo")
            self.assertEqual(store.read_run_summary(run_id)["pass_rate"], 1.0)
            self.assertEqual(store.read_run_results(run_id)[0]["scenario_id"], "one")
            self.assertEqual(store.list_events(run_id)[0]["event_type"], "scenario_completed")


if __name__ == "__main__":
    unittest.main()

