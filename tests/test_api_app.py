from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

from jemma.api.app import create_app


class ApiAppTests(unittest.TestCase):
    def test_root_and_preset_endpoints_load(self) -> None:
        client = TestClient(create_app())
        root = client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["name"], "jemma-api")

        presets = client.get("/api/benchmarks/presets")
        self.assertEqual(presets.status_code, 200)
        self.assertTrue(presets.json()["presets"])


if __name__ == "__main__":
    unittest.main()

