#!/usr/bin/env python3
"""Import a fine-tuned GGUF model into a local Ollama instance.

Usage:
    python toolbox/import_gguf_to_ollama.py <gguf-file> [--model-name NAME] [--ctx-size 16384]

This script:
1. Creates a temporary Modelfile pointing at the GGUF
2. Runs `ollama create` to register the model
3. Verifies the model appears in `ollama list`
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def build_modelfile(gguf_path: Path, context_length: int) -> str:
    lines = [f"FROM {gguf_path.resolve()}"]
    lines.append(f"PARAMETER num_ctx {context_length}")
    lines.append(
        'TEMPLATE """{{ if .System }}<start_of_turn>system\n{{ .System }}'
        "<end_of_turn>\n{{ end }}{{ if .Prompt }}<start_of_turn>user\n"
        '{{ .Prompt }}<end_of_turn>\n<start_of_turn>model\n{{ end }}"""'
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a GGUF into local Ollama.")
    parser.add_argument("gguf_file", type=Path, help="Path to the GGUF file")
    parser.add_argument(
        "--model-name",
        default=None,
        help="Ollama model name (default: derived from GGUF filename)",
    )
    parser.add_argument("--ctx-size", type=int, default=16384, help="Context window size")
    args = parser.parse_args()

    gguf_path = args.gguf_file.resolve()
    if not gguf_path.is_file():
        print(f"ERROR: GGUF file not found: {gguf_path}", file=sys.stderr)
        return 1

    if not shutil.which("ollama"):
        print("ERROR: ollama not found in PATH.", file=sys.stderr)
        return 1

    model_name = args.model_name or gguf_path.stem.lower().replace(".", "-").replace("_", "-")
    modelfile_content = build_modelfile(gguf_path, args.ctx_size)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".Modelfile", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(modelfile_content)
        modelfile_path = tmp.name

    print(f"Creating Ollama model '{model_name}' from {gguf_path}")
    print(f"Modelfile:\n{modelfile_content}")

    try:
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"ERROR: ollama create failed:\n{result.stderr}", file=sys.stderr)
            return 1
        print(result.stdout)
    finally:
        Path(modelfile_path).unlink(missing_ok=True)

    # Verify
    verify = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
    if model_name in verify.stdout:
        print(f"SUCCESS: Model '{model_name}' is now available in Ollama.")
    else:
        print(f"WARNING: Model '{model_name}' not found in ollama list output.", file=sys.stderr)
        print(verify.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
