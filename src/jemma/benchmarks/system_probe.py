from __future__ import annotations

import platform
import subprocess
from pathlib import Path


def _run_command(command: list[str]) -> dict[str, str | int | bool]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "command": " ".join(command), "error": str(exc)}

    return {
        "ok": completed.returncode == 0,
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def collect_system_probe(repo_root: Path) -> dict[str, object]:
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cwd": str(repo_root),
        "gpu": _run_command(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu", "--format=csv,noheader"]),
        "ollama_version": _run_command(["ollama", "--version"]),
        "tailscale_version": _run_command(["tailscale", "version"]),
    }

