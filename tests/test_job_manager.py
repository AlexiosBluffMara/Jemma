from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jemma.core.store import ArtifactStore
from jemma.core.types import (
    AppConfig,
    CapabilityPolicy,
    ChatRequest,
    ChatResponse,
    ModelSpec,
    SoloBenchmarkManifest,
)
from jemma.services.jobs import JobManager


class FakeProvider:
    def list_models(self) -> list[str]:
        return ["model-a"]

    def health(self) -> object:
        return None

    def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(model=request.model, content="OK", raw={})


class JobManagerTests(unittest.TestCase):
    def test_submit_solo_job_tracks_completion(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            dataset = root / "datasets" / "prompts" / "smoke.jsonl"
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
            manager = JobManager(config, FakeProvider(), ArtifactStore(config))
            job = manager.submit_solo(SoloBenchmarkManifest("solo", ["model-a"], dataset))

            for _ in range(100):
                current = manager.get_job(job["job_id"])
                if current and current["status"] == "succeeded":
                    break
                time.sleep(0.01)
            else:
                self.fail("job did not complete")

            finished = manager.get_job(job["job_id"])
            assert finished is not None
            self.assertEqual(finished["status"], "succeeded")
            self.assertGreaterEqual(finished["completed_steps"], 1)


if __name__ == "__main__":
    unittest.main()

