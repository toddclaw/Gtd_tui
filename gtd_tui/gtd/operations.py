from __future__ import annotations

from datetime import date, datetime

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
    kwargs = {"title": title, "notes": notes, "folder_id": "today", "position": insert_pos}
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
    kwargs = {"title": title, "notes": notes, "folder_id": "today", "position": insert_pos}
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
            t for t in tasks
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
            t for t in tasks
            if t.folder_id == "today"
            and t.scheduled_date is not None
            and t.scheduled_date > ref
        ],
        key=lambda t: (t.scheduled_date, t.position),
    )


def move_task_up(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a Today task one position toward the top. No-op if already first or not found."""
    active = today_tasks(tasks)
    idx = next((i for i, t in enumerate(active) if t.id == task_id), None)
    if idx is None or idx == 0:
        return tasks
    active[idx].position, active[idx - 1].position = active[idx - 1].position, active[idx].position
    return tasks


def move_task_down(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a Today task one position toward the bottom. No-op if already last or not found."""
    active = today_tasks(tasks)
    idx = next((i for i, t in enumerate(active) if t.id == task_id), None)
    if idx is None or idx == len(active) - 1:
        return tasks
    active[idx].position, active[idx + 1].position = active[idx + 1].position, active[idx].position
    return tasks


def logbook_tasks(tasks: list[Task]) -> list[Task]:
    """Return logbook tasks sorted by completion time, most recent first."""
    return sorted(
        [t for t in tasks if t.folder_id == "logbook"],
        key=lambda t: t.completed_at or datetime.min,
        reverse=True,
    )
