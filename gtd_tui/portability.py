"""Export and import helpers for gtd_tui data.

Supported export formats:
  json — lossless round-trip; recommended for backup/import
  txt  — one task per line (folder: title)
  csv  — columns: folder, title, scheduled_date, deadline, notes
  md   — markdown with folder headings and task bullet lists

Only JSON import is supported because the other formats are lossy.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import (
    folder_from_dict,
    folder_to_dict,
    load_folders,
    load_tasks,
    save_data,
    task_from_dict,
    task_to_dict,
)

_EXPORT_VERSION = 1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BUILTIN_NAMES: dict[str, str] = {
    "inbox": "Inbox",
    "today": "Today",
    "upcoming": "Upcoming",
    "waiting_on": "Waiting On",
    "someday": "Someday",
    "logbook": "Logbook",
    "reference": "Reference",
}


def _folder_name(folder_id: str, folders: list[Folder]) -> str:
    if folder_id in _BUILTIN_NAMES:
        return _BUILTIN_NAMES[folder_id]
    for f in folders:
        if f.id == folder_id:
            return f.name
    return folder_id


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_json(tasks: list[Task], folders: list[Folder]) -> str:
    """Serialise *tasks* and *folders* to a JSON string.

    The returned JSON is a lossless snapshot that can be round-tripped back
    via :func:`import_json`.  Only user-created folders are included; built-in
    folders are omitted because they always exist.
    """
    user_folders = [f for f in folders if f.id not in BUILTIN_FOLDER_IDS]
    payload: dict[str, Any] = {
        "version": _EXPORT_VERSION,
        "folders": [folder_to_dict(f) for f in user_folders],
        "tasks": [task_to_dict(t) for t in tasks],
    }
    return json.dumps(payload, indent=2)


def export_txt(tasks: list[Task], folders: list[Folder]) -> str:
    """Return tasks as newline-delimited plain text.

    Format: ``<folder>: <title>``  (one task per line, skipping deleted tasks)
    """
    lines: list[str] = []
    for t in tasks:
        if t.is_deleted:
            continue
        name = _folder_name(t.folder_id, folders)
        lines.append(f"{name}: {t.title}")
    return "\n".join(lines) + ("\n" if lines else "")


def export_csv(tasks: list[Task], folders: list[Folder]) -> str:
    """Return tasks as CSV with columns: folder, title, scheduled_date, deadline, notes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["folder", "title", "scheduled_date", "deadline", "notes"])
    for t in tasks:
        if t.is_deleted:
            continue
        writer.writerow(
            [
                _folder_name(t.folder_id, folders),
                t.title,
                t.scheduled_date.isoformat() if t.scheduled_date else "",
                t.deadline.isoformat() if t.deadline else "",
                t.notes or "",
            ]
        )
    return buf.getvalue()


def export_md(tasks: list[Task], folders: list[Folder]) -> str:
    """Return tasks as Markdown with folder headings and task bullet lists."""
    # Group tasks by folder, preserving folder order
    by_folder: dict[str, list[Task]] = {}
    folder_order: list[str] = []
    for t in tasks:
        if t.is_deleted:
            continue
        if t.folder_id not in by_folder:
            by_folder[t.folder_id] = []
            folder_order.append(t.folder_id)
        by_folder[t.folder_id].append(t)

    lines: list[str] = []
    for fid in folder_order:
        name = _folder_name(fid, folders)
        lines.append(f"## {name}\n")
        for t in by_folder[fid]:
            check = "x" if t.completed_at else " "
            lines.append(f"- [{check}] {t.title}")
            if t.notes:
                for note_line in t.notes.splitlines():
                    lines.append(f"  {note_line}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_json(
    export_path: Path,
    data_file: Path | None = None,
    password: str | None = None,
) -> tuple[int, int]:
    """Merge an exported JSON file into the active data file.

    Only tasks and folders whose IDs are not already present are added
    (non-destructive merge).  Built-in folder IDs are never imported.

    Returns:
        (tasks_added, folders_added) counts.
    """
    raw = export_path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    existing_tasks = load_tasks(data_file, password=password)
    existing_folders = load_folders(data_file, password=password)

    existing_task_ids = {t.id for t in existing_tasks}
    existing_folder_ids = {f.id for f in existing_folders}

    new_tasks: list[Task] = []
    for td in payload.get("tasks", []):
        if td["id"] not in existing_task_ids:
            new_tasks.append(task_from_dict(td))

    new_folders: list[Folder] = []
    for fd in payload.get("folders", []):
        fid = fd["id"]
        if fid not in BUILTIN_FOLDER_IDS and fid not in existing_folder_ids:
            new_folders.append(folder_from_dict(fd))

    merged_tasks = existing_tasks + new_tasks
    merged_folders = existing_folders + new_folders

    save_data(merged_tasks, merged_folders, data_file, password=password)

    return len(new_tasks), len(new_folders)
