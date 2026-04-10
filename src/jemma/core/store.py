from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jemma.core.types import AppConfig


def _default_json(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Unsupported value for JSON serialization: {type(value)!r}")


class ArtifactStore:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.config.state_dir / "jemma.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    artifact_dir TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_run(self, kind: str, name: str) -> tuple[str, Path]:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        run_id = f"{kind}-{timestamp}"
        artifact_dir = self.config.artifacts_dir / "runs" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO runs (run_id, kind, name, created_at, artifact_dir) VALUES (?, ?, ?, ?, ?)",
                (run_id, kind, name, datetime.now(UTC).isoformat(), str(artifact_dir)),
            )

        return run_id, artifact_dir

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        row = {
            "type": event_type,
            "payload": payload,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._append_jsonl(self.config.artifacts_dir / "runs" / run_id / "events.jsonl", row)

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO events (run_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(payload, default=_default_json), row["created_at"]),
            )

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=_default_json), encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=_default_json) + "\n")

