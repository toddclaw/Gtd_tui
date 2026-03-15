from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.task import RecurRule, RepeatRule, Task

_DEFAULT_DATA_FILE = Path(user_data_dir("gtd_tui")) / "data.json"


def _repeat_rule_to_dict(rule: RepeatRule) -> dict[str, Any]:
    return {
        "interval": rule.interval,
        "unit": rule.unit,
        "next_due": rule.next_due.isoformat(),
    }


def _repeat_rule_from_dict(data: dict[str, Any]) -> RepeatRule:
    return RepeatRule(
        interval=data["interval"],
        unit=data["unit"],
        next_due=date.fromisoformat(data["next_due"]),
    )


def _recur_rule_to_dict(rule: RecurRule) -> dict[str, Any]:
    return {"interval": rule.interval, "unit": rule.unit}


def _recur_rule_from_dict(data: dict[str, Any]) -> RecurRule:
    return RecurRule(interval=data["interval"], unit=data["unit"])


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "notes": task.notes,
        "folder_id": task.folder_id,
        "position": task.position,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "scheduled_date": (
            task.scheduled_date.isoformat() if task.scheduled_date else None
        ),
        "repeat_rule": (
            _repeat_rule_to_dict(task.repeat_rule) if task.repeat_rule else None
        ),
        "recur_rule": (
            _recur_rule_to_dict(task.recur_rule) if task.recur_rule else None
        ),
        "is_deleted": task.is_deleted,
    }


def _task_from_dict(data: dict[str, Any]) -> Task:
    raw_rule = data.get("repeat_rule")
    return Task(
        id=data["id"],
        title=data["title"],
        notes=data.get("notes", ""),
        folder_id=data["folder_id"],
        position=data["position"],
        completed_at=(
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        ),
        scheduled_date=(
            date.fromisoformat(data["scheduled_date"])
            if data.get("scheduled_date")
            else None
        ),
        repeat_rule=_repeat_rule_from_dict(raw_rule) if raw_rule else None,
        recur_rule=(
            _recur_rule_from_dict(data["recur_rule"])
            if data.get("recur_rule")
            else None
        ),
        is_deleted=data.get("is_deleted", False),
    )


def _folder_to_dict(folder: Folder) -> dict[str, Any]:
    return {"id": folder.id, "name": folder.name, "position": folder.position}


def _folder_from_dict(data: dict[str, Any]) -> Folder:
    return Folder(id=data["id"], name=data["name"], position=data.get("position", 0))


def load_tasks(data_file: Path | None = None) -> list[Task]:
    """Load tasks from disk. Returns empty list if file is missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        with open(path) as f:
            raw = json.load(f)
        return [_task_from_dict(t) for t in raw.get("tasks", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_folders(data_file: Path | None = None) -> list[Folder]:
    """Load user-created folders from disk. Returns empty list if missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        with open(path) as f:
            raw = json.load(f)
        return [_folder_from_dict(f) for f in raw.get("folders", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def save_data(
    tasks: list[Task], folders: list[Folder], data_file: Path | None = None
) -> None:
    """Atomically save tasks and folders to disk with restricted permissions (600)."""
    path = data_file or _DEFAULT_DATA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tasks": [_task_to_dict(t) for t in tasks],
        "folders": [_folder_to_dict(f) for f in folders],
    }
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


def save_tasks(tasks: list[Task], data_file: Path | None = None) -> None:
    """Atomically save tasks to disk, preserving any existing folder data."""
    existing_folders = load_folders(data_file)
    save_data(tasks, existing_folders, data_file)
