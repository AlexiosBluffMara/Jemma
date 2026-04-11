from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jemma.notebook_support import resolve_python_executable, validate_dataset_file


class NotebookSupportTests(unittest.TestCase):
    def test_validate_dataset_file_accepts_supported_shapes(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            dataset_path = Path(temp_dir) / "train.jsonl"
            dataset_path.write_text(
                '\n'.join(
                    [
                        '{"messages":[{"role":"user","content":"hello"},{"role":"assistant","content":"world"}]}',
                        '{"conversations":[{"role":"user","content":"a"},{"role":"assistant","content":"b"}]}',
                        '{"prompt":"p","response":"r"}',
                    ]
                ),
                encoding="utf-8",
            )
            summary = validate_dataset_file(dataset_path)
            self.assertEqual(summary["rows"], 3)
            self.assertEqual(summary["shapes"]["messages"], 1)
            self.assertEqual(summary["shapes"]["conversations"], 1)
            self.assertEqual(summary["shapes"]["prompt_response"], 1)

    def test_validate_dataset_file_rejects_unknown_shape(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            dataset_path = Path(temp_dir) / "train.jsonl"
            dataset_path.write_text('{"foo":"bar"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "messages, conversations, or prompt/response"):
                validate_dataset_file(dataset_path)

    def test_resolve_python_executable_prefers_existing_candidate(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        resolved = resolve_python_executable(repo_root)
        self.assertTrue(resolved is None or resolved.is_file())


if __name__ == "__main__":
    unittest.main()
