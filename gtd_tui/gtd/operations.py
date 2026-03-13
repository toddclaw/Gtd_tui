from __future__ import annotations

from datetime import datetime

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


def today_tasks(tasks: list[Task]) -> list[Task]:
    """Return today's tasks sorted by position (ascending)."""
    return sorted(
        [t for t in tasks if t.folder_id == "today"],
        key=lambda t: t.position,
    )


def logbook_tasks(tasks: list[Task]) -> list[Task]:
    """Return logbook tasks sorted by completion time, most recent first."""
    return sorted(
        [t for t in tasks if t.folder_id == "logbook"],
        key=lambda t: t.completed_at or datetime.min,
        reverse=True,
    )
