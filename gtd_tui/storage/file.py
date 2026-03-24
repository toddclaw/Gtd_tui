from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir

from gtd_tui.gtd.area import Area
from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.project import Project
from gtd_tui.gtd.task import ChecklistItem, RecurRule, RepeatRule, Task
from gtd_tui.storage.crypto import (
    DecryptionError,
    decrypt_data,
    encrypt_data,
    is_encrypted,
)

_DEFAULT_DATA_FILE = Path(user_data_dir("gtd_tui")) / "data.json"


def default_data_file_path() -> Path:
    """Default XDG path for the task database (`data.json`)."""
    return _DEFAULT_DATA_FILE


def _repeat_rule_to_dict(rule: RepeatRule) -> dict[str, Any]:
    d: dict[str, Any] = {
        "interval": rule.interval,
        "unit": rule.unit,
        "next_due": rule.next_due.isoformat(),
    }
    if rule.days_of_week:
        d["days_of_week"] = rule.days_of_week
    if rule.nth_weekday is not None:
        d["nth_weekday"] = list(rule.nth_weekday)
    return d


def _repeat_rule_from_dict(data: dict[str, Any]) -> RepeatRule:
    nth_raw = data.get("nth_weekday")
    return RepeatRule(
        interval=data["interval"],
        unit=data["unit"],
        next_due=date.fromisoformat(data["next_due"]),
        days_of_week=data.get("days_of_week", []),
        nth_weekday=tuple(nth_raw) if nth_raw else None,  # type: ignore[arg-type]
    )


def _recur_rule_to_dict(rule: RecurRule) -> dict[str, Any]:
    d: dict[str, Any] = {"interval": rule.interval, "unit": rule.unit}
    if rule.days_of_week:
        d["days_of_week"] = rule.days_of_week
    if rule.nth_weekday is not None:
        d["nth_weekday"] = list(rule.nth_weekday)
    return d


def _recur_rule_from_dict(data: dict[str, Any]) -> RecurRule:
    nth_raw = data.get("nth_weekday")
    return RecurRule(
        interval=data["interval"],
        unit=data["unit"],
        days_of_week=data.get("days_of_week", []),
        nth_weekday=tuple(nth_raw) if nth_raw else None,  # type: ignore[arg-type]
    )


def _checklist_item_to_dict(item: ChecklistItem) -> dict[str, Any]:
    return {"id": item.id, "label": item.label, "checked": item.checked}


def _checklist_item_from_dict(data: dict[str, Any]) -> ChecklistItem:
    return ChecklistItem(
        id=data["id"], label=data["label"], checked=data.get("checked", False)
    )


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
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "repeat_rule": (
            _repeat_rule_to_dict(task.repeat_rule) if task.repeat_rule else None
        ),
        "recur_rule": (
            _recur_rule_to_dict(task.recur_rule) if task.recur_rule else None
        ),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "is_deleted": task.is_deleted,
        "tags": task.tags,
        "project_id": task.project_id,
        "checklist": [_checklist_item_to_dict(i) for i in task.checklist],
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
        deadline=(
            date.fromisoformat(data["deadline"]) if data.get("deadline") else None
        ),
        repeat_rule=_repeat_rule_from_dict(raw_rule) if raw_rule else None,
        recur_rule=(
            _recur_rule_from_dict(data["recur_rule"])
            if data.get("recur_rule")
            else None
        ),
        created_at=(
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        ),
        is_deleted=data.get("is_deleted", False),
        tags=data.get("tags", []),
        project_id=data.get("project_id", None),
        checklist=[_checklist_item_from_dict(i) for i in data.get("checklist", [])],
    )


def _project_to_dict(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "title": project.title,
        "notes": project.notes,
        "folder_id": project.folder_id,
        "position": project.position,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "completed_at": (
            project.completed_at.isoformat() if project.completed_at else None
        ),
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "area_id": project.area_id,
    }


def _project_from_dict(data: dict[str, Any]) -> Project:
    return Project(
        id=data["id"],
        title=data["title"],
        notes=data.get("notes", ""),
        folder_id=data.get("folder_id", "today"),
        position=data.get("position", 0),
        deadline=(
            date.fromisoformat(data["deadline"]) if data.get("deadline") else None
        ),
        completed_at=(
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        ),
        created_at=(
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        ),
        area_id=data.get("area_id"),
    )


def _folder_to_dict(folder: Folder) -> dict[str, Any]:
    return {
        "id": folder.id,
        "name": folder.name,
        "position": folder.position,
        "area_id": folder.area_id,
    }


def _folder_from_dict(data: dict[str, Any]) -> Folder:
    return Folder(
        id=data["id"],
        name=data["name"],
        position=data.get("position", 0),
        area_id=data.get("area_id"),
    )


def _area_to_dict(area: Area) -> dict[str, Any]:
    return {"id": area.id, "name": area.name, "position": area.position}


def _area_from_dict(data: dict[str, Any]) -> Area:
    return Area(id=data["id"], name=data["name"], position=data.get("position", 0))


def _read_raw(path: Path, password: str | None) -> dict[str, Any]:
    """Read and parse the data file, decrypting if necessary."""
    data = path.read_bytes()
    if is_encrypted(data):
        if password is None:
            raise DecryptionError("File is encrypted but no password was provided")
        data = decrypt_data(data, password)
    return json.loads(data)


def load_tasks(
    data_file: Path | None = None, password: str | None = None
) -> list[Task]:
    """Load tasks from disk. Returns empty list if file is missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return [_task_from_dict(t) for t in raw.get("tasks", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_folders(
    data_file: Path | None = None, password: str | None = None
) -> list[Folder]:
    """Load user-created folders from disk. Returns empty list if missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return [_folder_from_dict(f) for f in raw.get("folders", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


_UNDO_CAP = 20

UndoStack = list[tuple[list[Task], list[Folder], list[Project], list[Area]]]


def _undo_stack_to_list(stack: UndoStack) -> list[Any]:
    return [
        {
            "tasks": [_task_to_dict(t) for t in tasks],
            "folders": [_folder_to_dict(f) for f in folders],
            "projects": [_project_to_dict(p) for p in projects],
            "areas": [_area_to_dict(a) for a in areas],
        }
        for tasks, folders, projects, areas in stack
    ]


def _undo_stack_from_list(raw: list[Any]) -> UndoStack:
    result: UndoStack = []
    for entry in raw:
        try:
            if "projects" not in entry:
                continue
            tasks = [_task_from_dict(t) for t in entry.get("tasks", [])]
            folders = [_folder_from_dict(f) for f in entry.get("folders", [])]
            projects = [_project_from_dict(p) for p in entry.get("projects", [])]
            areas = (
                [_area_from_dict(a) for a in entry.get("areas", [])]
                if "areas" in entry
                else []
            )
            result.append((tasks, folders, projects, areas))
        except (KeyError, ValueError):
            pass
    return result


def load_undo_stack(
    data_file: Path | None = None, password: str | None = None
) -> UndoStack:
    """Load the persisted undo stack. Returns empty list if missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return _undo_stack_from_list(raw.get("undo_stack", []))
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_redo_stack(
    data_file: Path | None = None, password: str | None = None
) -> UndoStack:
    """Load the persisted redo stack. Returns empty list if missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return _undo_stack_from_list(raw.get("redo_stack", []))
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def save_data(
    tasks: list[Task],
    folders: list[Folder],
    data_file: Path | None = None,
    password: str | None = None,
    undo_stack: UndoStack | None = None,
    redo_stack: UndoStack | None = None,
    projects: list[Project] | None = None,
    areas: list[Area] | None = None,
    tag_order: list[str] | None = None,
    collapsed_areas: set[str] | None = None,
) -> None:
    """Atomically save tasks, folders, optional undo/redo stacks, projects, and areas to disk.

    If *password* is provided the file is written as an encrypted binary blob;
    otherwise it is written as plain JSON.  The undo/redo stacks are capped at
    _UNDO_CAP entries each before saving.
    """
    path = data_file or _DEFAULT_DATA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "tasks": [_task_to_dict(t) for t in tasks],
        "folders": [_folder_to_dict(f) for f in folders],
    }
    if undo_stack is not None:
        payload["undo_stack"] = _undo_stack_to_list(undo_stack[-_UNDO_CAP:])
    if redo_stack is not None:
        payload["redo_stack"] = _undo_stack_to_list(redo_stack[-_UNDO_CAP:])
    if projects is not None:
        payload["projects"] = [_project_to_dict(p) for p in projects]
    if areas is not None:
        payload["areas"] = [_area_to_dict(a) for a in areas]
    if tag_order is not None:
        payload["tag_order"] = tag_order
    if collapsed_areas is not None:
        payload["collapsed_areas"] = sorted(collapsed_areas)
    json_bytes = json.dumps(payload, indent=2).encode()
    write_bytes = encrypt_data(json_bytes, password) if password else json_bytes

    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(write_bytes)
        os.replace(tmp, path)  # atomic on POSIX
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_tasks(
    tasks: list[Task],
    data_file: Path | None = None,
    password: str | None = None,
) -> None:
    """Atomically save tasks to disk, preserving any existing folder data."""
    existing_folders = load_folders(data_file, password=password)
    save_data(tasks, existing_folders, data_file, password=password)


def load_projects(
    data_file: Path | None = None, password: str | None = None
) -> list[Project]:
    """Load projects from disk. Returns empty list if file is missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return [_project_from_dict(p) for p in raw.get("projects", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_areas(
    data_file: Path | None = None, password: str | None = None
) -> list[Area]:
    """Load areas from disk. Returns empty list if file is missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return [_area_from_dict(a) for a in raw.get("areas", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_tag_order(
    data_file: Path | None = None, password: str | None = None
) -> list[str]:
    """Load persisted tag ordering from disk. Returns empty list if missing or corrupt."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return []
    try:
        raw = _read_raw(path, password)
        return [str(t) for t in raw.get("tag_order", [])]
    except (json.JSONDecodeError, KeyError, ValueError):
        return []


def load_collapsed_areas(
    data_file: Path | None = None, password: str | None = None
) -> set[str]:
    """Load the set of collapsed area IDs from disk. Returns empty set if missing."""
    path = data_file or _DEFAULT_DATA_FILE
    if not path.exists():
        return set()
    try:
        raw = _read_raw(path, password)
        return set(str(a) for a in raw.get("collapsed_areas", []))
    except (json.JSONDecodeError, KeyError, ValueError):
        return set()


# Public serialization helpers — used by portability.py for export/import.
task_to_dict = _task_to_dict
task_from_dict = _task_from_dict
folder_to_dict = _folder_to_dict
folder_from_dict = _folder_from_dict

__all__ = [
    "UndoStack",
    "default_data_file_path",
    "folder_from_dict",
    "folder_to_dict",
    "load_areas",
    "load_collapsed_areas",
    "load_folders",
    "load_projects",
    "load_redo_stack",
    "load_tag_order",
    "load_tasks",
    "load_undo_stack",
    "save_data",
    "save_tasks",
    "task_from_dict",
    "task_to_dict",
]
