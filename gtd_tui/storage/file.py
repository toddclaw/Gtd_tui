from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from gtd_tui.gtd.task import Task


_DEFAULT_DATA_FILE = Path(user_data_dir("gtd_tui")) / "data.json"


def _to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "notes": task.notes,
        "folder_id": task.folder_id,
        "position": task.position,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
    }


def _from_dict(data: dict[str, Any]) -> Task:
    return Task(
        id=data["id"],
        title=data["title"],
        notes=data.get("notes", ""),
        folder_id=data["folder_id"],
        position=data["position"],
        completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        scheduled_date=date.fromisoformat(data["scheduled_date"]) if data.get("scheduled_date") else None,
    )


def load_tasks(data_file: Path | None = None) -> list[Task]:
    """Load tasks from disk. Returns empty list if file is missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        with open(path) as f:
            raw = json.load(f)
        return [_from_dict(t) for t in raw.get("tasks", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def save_tasks(tasks: list[Task], data_file: Path | None = None) -> None:
    """Atomically save tasks to disk with restricted permissions (600)."""
    path = data_file or _DEFAULT_DATA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"tasks": [_to_dict(t) for t in tasks]}
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)  # atomic on POSIX
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
