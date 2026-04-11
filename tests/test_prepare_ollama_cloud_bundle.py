from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolbox.prepare_ollama_cloud_bundle import create_bundle


class PrepareOllamaCloudBundleTests(unittest.TestCase):
    def test_create_bundle_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            gguf_path = root / "model.gguf"
            gguf_path.write_bytes(b"GGUF")
            manifest_path = root / "deployment-manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "artifact_slug": "gemma4-e4b-second-brain",
                        "max_seq_length": 16384,
                        "exports": {"gguf_file": str(gguf_path)},
                    }
                ),
                encoding="utf-8",
            )

            bundle_root = create_bundle(manifest_path)

            self.assertTrue((bundle_root / "Dockerfile").exists())
            self.assertTrue((bundle_root / "Modelfile").exists())
            self.assertTrue((bundle_root / "entrypoint.sh").exists())
            self.assertTrue((bundle_root / "deploy-cloud-run.ps1").exists())
            self.assertTrue((bundle_root / "bundle-manifest.json").exists())

    def test_create_bundle_requires_gguf_export(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "deployment-manifest.json"
            manifest_path.write_text(json.dumps({"artifact_slug": "missing"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "JEMMA_SAVE_GGUF=1"):
                create_bundle(manifest_path)


if __name__ == "__main__":
    unittest.main()
