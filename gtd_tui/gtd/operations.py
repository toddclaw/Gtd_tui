from __future__ import annotations

from datetime import date, datetime

from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.task import Task

# Folders whose tasks never auto-surface in Today or Upcoming smart views.
_EXCLUDED_FROM_SMART_VIEWS: frozenset[str] = frozenset({"someday", "logbook"})


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
    """Insert a new Today task immediately after the anchor task.

    The anchor must be a task in the 'today' folder; falls back to add_task
    when anchor_id is not found in that folder.
    """
    today_only = _today_folder_active(tasks)
    anchor = next((t for t in today_only if t.id == anchor_id), None)
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
    """Insert a new Today task immediately before the anchor task.

    The anchor must be a task in the 'today' folder; falls back to add_task
    when anchor_id is not found in that folder.
    """
    today_only = _today_folder_active(tasks)
    anchor = next((t for t in today_only if t.id == anchor_id), None)
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
    """Set a future scheduled_date on a task, moving it out of Today."""
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
    """Return tasks that should appear in the Today smart view.

    Includes tasks from any folder except 'someday' and 'logbook' whose
    scheduled_date is absent or has already arrived.

    Sort order: 'today'-folder tasks first (by position), then tasks from
    other folders grouped by folder_id then position.
    """
    ref = as_of or date.today()
    eligible = [
        t
        for t in tasks
        if t.folder_id not in _EXCLUDED_FROM_SMART_VIEWS
        and (t.scheduled_date is None or t.scheduled_date <= ref)
    ]
    return sorted(
        eligible,
        key=lambda t: (0 if t.folder_id == "today" else 1, t.folder_id, t.position),
    )


def upcoming_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return tasks that should appear in the Upcoming smart view.

    Includes all tasks (except 'someday' and 'logbook') with a scheduled_date
    strictly in the future, sorted by date then position.
    """
    ref = as_of or date.today()
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id not in _EXCLUDED_FROM_SMART_VIEWS
            and t.scheduled_date is not None
            and t.scheduled_date > ref
        ],
        key=lambda t: (t.scheduled_date, t.position),
    )


# Backward-compat alias — returns only 'today'-folder future tasks.
# Prefer upcoming_tasks() for new code.
def scheduled_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return 'today'-folder tasks snoozed to a future date (legacy helper)."""
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


def someday_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks in the Someday folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == "someday"],
        key=lambda t: t.position,
    )


def move_task_up(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a 'today'-folder task one position up.

    No-op if the task is not in the 'today' folder, already first, or not found.
    """
    active = _today_folder_active(tasks)
    idx = next((i for i, t in enumerate(active) if t.id == task_id), None)
    if idx is None or idx == 0:
        return tasks
    active[idx].position, active[idx - 1].position = (
        active[idx - 1].position,
        active[idx].position,
    )
    return tasks


def move_task_down(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a 'today'-folder task one position down.

    No-op if the task is not in the 'today' folder, already last, or not found.
    """
    active = _today_folder_active(tasks)
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


# ---------------------------------------------------------------------------
# Waiting On folder
# ---------------------------------------------------------------------------


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
    """Move a task to Today (folder_id='today') at position 0, clearing its date."""
    for task in tasks:
        if task.folder_id == "today":
            task.position += 1
    for task in tasks:
        if task.id == task_id:
            task.folder_id = "today"
            task.scheduled_date = None
            task.position = 0
    return tasks


def waiting_on_tasks(tasks: list[Task]) -> list[Task]:
    """Return all Waiting On tasks, sorted by scheduled_date then position.

    Includes undated, future-dated, and past-dated tasks — the full view of
    what you are waiting on from others.
    """
    return sorted(
        [t for t in tasks if t.folder_id == "waiting_on"],
        key=lambda t: (t.scheduled_date or date.min, t.position),
    )


def surfaced_waiting_on_tasks(
    tasks: list[Task], as_of: date | None = None
) -> list[Task]:
    """Return Waiting On tasks whose date has arrived.

    These also appear in the Today smart view via today_tasks().
    """
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
# Folder operations
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _today_folder_active(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """'today'-folder tasks with no future scheduled_date, sorted by position."""
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
