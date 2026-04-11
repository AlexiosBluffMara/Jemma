from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from jemma.agent.loop import AgentLoop
from jemma.core.store import ArtifactStore
from jemma.core.types import (
    AgentObjective,
    AppConfig,
    CapabilityPolicy,
    ChatRequest,
    ChatResponse,
    ModelSpec,
)


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_models(self) -> list[str]:
        return ["planner", "fallback"]

    def health(self) -> object:
        return None

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request.model)
        if request.response_format == "json":
            content = json.dumps({"steps": [{"step_id": "step-1", "kind": "infer", "target": "planner", "instruction": "say ready", "args": {}, "expected_contains": ["ready"]}]})
            return ChatResponse(model=request.model, content=content, raw={})
        return ChatResponse(model=request.model, content="network ready for benchmark", raw={})


class AgentLoopTests(unittest.TestCase):
    def test_runs_planned_inference_step(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            config = AppConfig(
                repo_root=root,
                state_dir=root / "state",
                artifacts_dir=root / "artifacts",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_timeout_s=120,
                default_model="planner",
                planner_model="planner",
                validator_model="planner",
                fallback_model="fallback",
                max_steps=4,
                actuation_enabled=False,
                capability_policies={"tailscale": CapabilityPolicy("tailscale", ["observe_status"])},
                raw_sections={},
                models={
                    "planner": ModelSpec("planner", "ollama", "planner-remote", 4096),
                    "fallback": ModelSpec("fallback", "ollama", "fallback-remote", 4096),
                },
            )
            loop = AgentLoop(config, FakeProvider(), ArtifactStore(config), {})
            result = loop.run_objective(
                AgentObjective(
                    name="lan-watch",
                    prompt="check readiness",
                    success_criteria=["ready", "benchmark"],
                    model="planner",
                    fallback_model="fallback",
                )
            )
            self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()

