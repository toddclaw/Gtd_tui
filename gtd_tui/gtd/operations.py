from __future__ import annotations

from datetime import date, datetime

from gtd_tui.gtd.task import Task


def add_task(tasks: list[Task], title: str, notes: str = "") -> list[Task]:
    """Add a new task to the top of Today. Returns updated task list."""
    for task in tasks:
        if task.folder_id == "today":
            task.position += 1
    new_task = Task(title=title, notes=notes, folder_id="today", position=0)
    return [new_task] + tasks


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


def logbook_tasks(tasks: list[Task]) -> list[Task]:
    """Return logbook tasks sorted by completion time, most recent first."""
    return sorted(
        [t for t in tasks if t.folder_id == "logbook"],
        key=lambda t: t.completed_at or datetime.min,
        reverse=True,
    )
