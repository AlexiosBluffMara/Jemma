from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jemma.benchmarks.runner import BenchmarkRunner
from jemma.core.store import ArtifactStore
from jemma.core.types import AppConfig, CapabilityPolicy, ChatRequest, ChatResponse, ModelSpec, SoloBenchmarkManifest


class FakeProvider:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses

    def list_models(self) -> list[str]:
        return list(self.responses)

    def health(self) -> object:
        return None

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(model=request.model, content=self.responses[request.model], raw={})


class BenchmarkRunnerTests(unittest.TestCase):
    def test_solo_summary_aggregates_passes(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            dataset = root / "datasets" / "smoke.jsonl"
            dataset.parent.mkdir(parents=True)
            dataset.write_text(
                '{"scenario_id":"ok","prompt":"Reply with exactly OK","validator":"exact_text","expected":"OK"}\n',
                encoding="utf-8",
            )
            config = AppConfig(
                repo_root=root,
                state_dir=root / "state",
                artifacts_dir=root / "artifacts",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_timeout_s=120,
                default_model="model-a",
                planner_model="model-a",
                validator_model="model-a",
                fallback_model=None,
                max_steps=4,
                actuation_enabled=False,
                capability_policies={"tailscale": CapabilityPolicy("tailscale", ["observe_status"])},
                raw_sections={},
                models={"model-a": ModelSpec("model-a", "ollama", "remote-a", 4096)},
            )
            runner = BenchmarkRunner(
                config,
                FakeProvider({"model-a": "OK"}),
                ArtifactStore(config),
            )
            result = runner.run_solo(SoloBenchmarkManifest("solo", ["model-a"], dataset))
            self.assertEqual(result["summary"]["models"]["model-a"]["pass_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()

