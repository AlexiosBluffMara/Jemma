from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

from jemma.api.app import create_app
from jemma.core.types import ChatRequest, ChatResponse


class ApiAppTests(unittest.TestCase):
    def test_root_and_preset_endpoints_load(self) -> None:
        client = TestClient(create_app())
        root = client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["name"], "jemma-api")

        presets = client.get("/api/benchmarks/presets")
        self.assertEqual(presets.status_code, 200)
        self.assertTrue(presets.json()["presets"])

    def test_mobile_capability_routes_load(self) -> None:
        client = TestClient(create_app())

        capabilities = client.get("/api/capabilities")
        self.assertEqual(capabilities.status_code, 200)
        payload = capabilities.json()
        self.assertIn("capabilities", payload)
        self.assertTrue(payload["capabilities"])

        skills = client.get("/api/skills")
        self.assertEqual(skills.status_code, 200)
        self.assertEqual(skills.json(), payload)

    def test_chat_route_uses_provider(self) -> None:
        class FakeProvider:
            def chat(self, request: ChatRequest) -> ChatResponse:
                self.request = request
                return ChatResponse(
                    model=request.model,
                    content=f"echo:{request.messages[-1]['content']}",
                    raw={"ok": True},
                    total_duration_ms=12,
                    prompt_eval_count=3,
                    eval_count=5,
                )

        app = create_app()
        provider = FakeProvider()
        app.state.provider = provider
        client = TestClient(app)

        response = client.post(
            "/api/chat",
            json={
                "model": "gemma4-e4b-it-q8",
                "system": "Be concise.",
                "messages": [{"role": "user", "content": "hello"}],
                "options": {"temperature": 0},
                "timeout_s": 30,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model"], "gemma4-e4b-it-q8")
        self.assertEqual(payload["content"], "echo:hello")
        self.assertEqual(payload["total_duration_ms"], 12)
        self.assertEqual(provider.request.system, "Be concise.")
        self.assertEqual(provider.request.messages[-1]["content"], "hello")


if __name__ == "__main__":
    unittest.main()

