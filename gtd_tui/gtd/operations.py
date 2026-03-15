from __future__ import annotations

from datetime import date, datetime

from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.task import Task


def add_task(
    tasks: list[Task], title: str, notes: str = "", task_id: str | None = None
) -> list[Task]:
    """Add a new task to the top of Today. Returns updated task list."""
    for task in tasks:
        if task.folder_id == "today":
            task.position += 1
    kwargs = {"title": title, "notes": notes, "folder_id": "today", "position": 0}
    if task_id is not None:
        kwargs["id"] = task_id
    new_task = Task(**kwargs)  # type: ignore[arg-type]
    return [new_task] + tasks


def insert_task_after(
    tasks: list[Task],
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new Today task immediately after the anchor task."""
    active = today_tasks(tasks)
    anchor = next((t for t in active if t.id == anchor_id), None)
    if anchor is None:
        return add_task(tasks, title, notes, task_id)
    insert_pos = anchor.position + 1
    for task in tasks:
        if task.folder_id == "today" and task.position >= insert_pos:
            task.position += 1
    kwargs = {
        "title": title,
        "notes": notes,
        "folder_id": "today",
        "position": insert_pos,
    }
    if task_id is not None:
        kwargs["id"] = task_id
    new_task = Task(**kwargs)  # type: ignore[arg-type]
    return tasks + [new_task]


def insert_task_before(
    tasks: list[Task],
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new Today task immediately before the anchor task."""
    active = today_tasks(tasks)
    anchor = next((t for t in active if t.id == anchor_id), None)
    if anchor is None:
        return add_task(tasks, title, notes, task_id)
    insert_pos = anchor.position
    for task in tasks:
        if task.folder_id == "today" and task.position >= insert_pos:
            task.position += 1
    kwargs = {
        "title": title,
        "notes": notes,
        "folder_id": "today",
        "position": insert_pos,
    }
    if task_id is not None:
        kwargs["id"] = task_id
    new_task = Task(**kwargs)  # type: ignore[arg-type]
    return tasks + [new_task]


def complete_task(tasks: list[Task], task_id: str) -> list[Task]:
    """Mark a task complete and move it to the logbook."""
    for task in tasks:
        if task.id == task_id:
            task.complete()
    return tasks


def schedule_task(tasks: list[Task], task_id: str, scheduled_date: date) -> list[Task]:
    """Set a future scheduled_date on a task, hiding it from Today until that date."""
    for task in tasks:
        if task.id == task_id:
            task.scheduled_date = scheduled_date
    return tasks


def unschedule_task(tasks: list[Task], task_id: str) -> list[Task]:
    """Clear a task's scheduled_date, returning it to Today immediately."""
    for task in tasks:
        if task.id == task_id:
            task.scheduled_date = None
    return tasks


def today_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return active Today tasks: folder 'today' with no future scheduled_date."""
    ref = as_of or date.today()
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id == "today"
            and (t.scheduled_date is None or t.scheduled_date <= ref)
        ],
        key=lambda t: t.position,
    )


def scheduled_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return Today-folder tasks snoozed to a future date, sorted by that date."""
    ref = as_of or date.today()
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id == "today"
            and t.scheduled_date is not None
            and t.scheduled_date > ref
        ],
        key=lambda t: (t.scheduled_date, t.position),
    )


def move_task_up(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a Today task one position up. No-op if already first or not found."""
    active = today_tasks(tasks)
    idx = next((i for i, t in enumerate(active) if t.id == task_id), None)
    if idx is None or idx == 0:
        return tasks
    active[idx].position, active[idx - 1].position = (
        active[idx - 1].position,
        active[idx].position,
    )
    return tasks


def move_task_down(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a Today task one position down. No-op if already last or not found."""
    active = today_tasks(tasks)
    idx = next((i for i, t in enumerate(active) if t.id == task_id), None)
    if idx is None or idx == len(active) - 1:
        return tasks
    active[idx].position, active[idx + 1].position = (
        active[idx + 1].position,
        active[idx].position,
    )
    return tasks


def logbook_tasks(tasks: list[Task]) -> list[Task]:
    """Return logbook tasks sorted by completion time, most recent first."""
    return sorted(
        [t for t in tasks if t.folder_id == "logbook"],
        key=lambda t: t.completed_at or datetime.min,
        reverse=True,
    )


def add_waiting_on_task(tasks: list[Task], title: str, notes: str = "") -> list[Task]:
    """Add a new task to the Waiting On folder."""
    new_task = Task(title=title, notes=notes, folder_id="waiting_on", position=0)
    return tasks + [new_task]


def move_to_waiting_on(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task to the Waiting On folder. Preserves any scheduled date."""
    for task in tasks:
        if task.id == task_id:
            task.folder_id = "waiting_on"
    return tasks


def move_to_today(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task to Today at position 0, clearing its scheduled date."""
    for task in tasks:
        if task.folder_id == "today":
            task.position += 1
    for task in tasks:
        if task.id == task_id:
            task.folder_id = "today"
            task.scheduled_date = None
            task.position = 0
    return tasks


def waiting_on_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return Waiting On tasks not yet surfaced: no date or a future date."""
    ref = as_of or date.today()
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id == "waiting_on"
            and (t.scheduled_date is None or t.scheduled_date > ref)
        ],
        key=lambda t: (t.scheduled_date or date.min, t.position),
    )


def surfaced_waiting_on_tasks(
    tasks: list[Task], as_of: date | None = None
) -> list[Task]:
    """Return Waiting On tasks whose date has arrived — they surface in Today."""
    ref = as_of or date.today()
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id == "waiting_on"
            and t.scheduled_date is not None
            and t.scheduled_date <= ref
        ],
        key=lambda t: t.scheduled_date,  # type: ignore[arg-type, return-value]
    )


# ---------------------------------------------------------------------------
# Folder operations (BACKLOG-4)
# ---------------------------------------------------------------------------


def add_task_to_folder(
    tasks: list[Task],
    folder_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Append a new task to the end of the given folder."""
    existing = folder_tasks(tasks, folder_id)
    next_pos = existing[-1].position + 1 if existing else 0
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": folder_id,
        "position": next_pos,
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def create_folder(
    folders: list[Folder], name: str, folder_id: str | None = None
) -> list[Folder]:
    """Create a new user folder appended after existing folders."""
    max_pos = max((f.position for f in folders), default=-1)
    kwargs: dict = {"name": name, "position": max_pos + 1}
    if folder_id is not None:
        kwargs["id"] = folder_id
    return folders + [Folder(**kwargs)]


def rename_folder(folders: list[Folder], folder_id: str, new_name: str) -> list[Folder]:
    """Rename a user folder. No-op for built-in folders or unknown IDs."""
    if folder_id in BUILTIN_FOLDER_IDS:
        return folders
    for folder in folders:
        if folder.id == folder_id:
            folder.name = new_name
    return folders


def delete_folder(folders: list[Folder], folder_id: str) -> list[Folder]:
    """Remove a user folder from the list. No-op for built-in folders."""
    if folder_id in BUILTIN_FOLDER_IDS:
        return folders
    return [f for f in folders if f.id != folder_id]


def folder_tasks(tasks: list[Task], folder_id: str) -> list[Task]:
    """Return tasks belonging to the given folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == folder_id],
        key=lambda t: t.position,
    )


def move_task_to_folder(tasks: list[Task], task_id: str, folder_id: str) -> list[Task]:
    """Move a task to a different folder, appending it at the end."""
    target_tasks = folder_tasks(tasks, folder_id)
    new_pos = target_tasks[-1].position + 1 if target_tasks else 0
    for task in tasks:
        if task.id == task_id:
            task.folder_id = folder_id
            task.position = new_pos
    return tasks


def discard_folder_tasks(tasks: list[Task], folder_id: str) -> list[Task]:
    """Delete all tasks in the given folder."""
    return [t for t in tasks if t.folder_id != folder_id]


def move_folder_tasks_to_today(tasks: list[Task], folder_id: str) -> list[Task]:
    """Move all tasks from the given folder to Today at the bottom."""
    today = [t for t in tasks if t.folder_id == "today"]
    next_pos = (max(t.position for t in today) + 1) if today else 0
    for task in tasks:
        if task.folder_id == folder_id:
            task.folder_id = "today"
            task.position = next_pos
            next_pos += 1
    return tasks
