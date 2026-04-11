from __future__ import annotations

import json
import sqlite3
import threading
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
        self._lock = threading.Lock()
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

        with self._lock:
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

        with self._lock:
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    "INSERT INTO events (run_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, event_type, json.dumps(payload, default=_default_json), row["created_at"]),
                )

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=_default_json), encoding="utf-8")

    def read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT run_id, kind, name, created_at, artifact_dir FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT run_id, kind, name, created_at, artifact_dir FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_events(self, run_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, run_id, event_type, payload, created_at
                FROM events
                WHERE run_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            events.append(item)
        return events

    def read_run_summary(self, run_id: str) -> dict[str, Any] | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        return self.read_json(Path(run["artifact_dir"]) / "summary.json")

    def read_run_results(self, run_id: str) -> Any:
        run = self.get_run(run_id)
        if run is None:
            return None
        return self.read_json(Path(run["artifact_dir"]) / "raw_results.json")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=_default_json) + "\n")

