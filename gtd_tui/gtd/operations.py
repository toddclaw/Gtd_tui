from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta

from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.task import RepeatRule, Task

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


def edit_task(tasks: list[Task], task_id: str, title: str, notes: str = "") -> list[Task]:
    """Update a task's title and notes. No-op if task_id is not found."""
    for task in tasks:
        if task.id == task_id:
            task.title = title
            task.notes = notes
    return tasks


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

    Two sources of tasks, matching Things app behaviour:
    1. 'today'-folder tasks with no future scheduled_date (their home is Today).
    2. Tasks from any other non-excluded folder that have a scheduled_date
       on or before today (explicitly scheduled to surface today/overdue).
       Undated tasks in other folders do NOT appear here.

    Sort order: 'today'-folder tasks first (by position), then dated tasks
    from other folders by (scheduled_date, folder_id, position).
    """
    ref = as_of or date.today()
    today_home: list[Task] = []
    dated_other: list[Task] = []
    for t in tasks:
        if t.folder_id in _EXCLUDED_FROM_SMART_VIEWS:
            continue
        if t.folder_id == "today":
            if t.scheduled_date is None or t.scheduled_date <= ref:
                today_home.append(t)
        else:
            if t.scheduled_date is not None and t.scheduled_date <= ref:
                dated_other.append(t)
    today_home.sort(key=lambda t: t.position)
    dated_other.sort(key=lambda t: (t.scheduled_date, t.folder_id, t.position))
    return today_home + dated_other


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
    """Move a task one position up within its visible peers.

    For the 'today' folder, peers are only the currently active (non-snoozed)
    tasks so that K always swaps with the task the user can see.
    For all other folders, peers are the full folder contents.

    No-op if the task is already first or not found.
    """
    task = next((t for t in tasks if t.id == task_id), None)
    if task is None:
        return tasks
    peers = _visible_peers(tasks, task)
    idx = next((i for i, t in enumerate(peers) if t.id == task_id), None)
    if idx is None or idx == 0:
        return tasks
    peers[idx].position, peers[idx - 1].position = (
        peers[idx - 1].position,
        peers[idx].position,
    )
    return tasks


def move_task_down(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task one position down within its visible peers.

    For the 'today' folder, peers are only the currently active (non-snoozed)
    tasks so that J always swaps with the task the user can see.
    For all other folders, peers are the full folder contents.

    No-op if the task is already last or not found.
    """
    task = next((t for t in tasks if t.id == task_id), None)
    if task is None:
        return tasks
    peers = _visible_peers(tasks, task)
    idx = next((i for i, t in enumerate(peers) if t.id == task_id), None)
    if idx is None or idx == len(peers) - 1:
        return tasks
    peers[idx].position, peers[idx + 1].position = (
        peers[idx + 1].position,
        peers[idx].position,
    )
    return tasks


def _visible_peers(tasks: list[Task], task: Task) -> list[Task]:
    """Return the ordered list of peers used for J/K reordering.

    'today'-folder tasks use only the active (visible) subset so that snoozed
    tasks hidden from the view are never accidentally swapped past.
    All other folders show every task they contain.
    """
    if task.folder_id == "today":
        return _today_folder_active(tasks)
    return sorted(
        [t for t in tasks if t.folder_id == task.folder_id],
        key=lambda t: t.position,
    )


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
    """Add a new task to the end of the Waiting On folder."""
    existing = folder_tasks(tasks, "waiting_on")
    next_pos = existing[-1].position + 1 if existing else 0
    new_task = Task(title=title, notes=notes, folder_id="waiting_on", position=next_pos)
    return tasks + [new_task]


def move_to_waiting_on(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task to the Waiting On folder, appending at the end. Preserves any scheduled date."""
    existing = folder_tasks(tasks, "waiting_on")
    next_pos = existing[-1].position + 1 if existing else 0
    for task in tasks:
        if task.id == task_id:
            task.folder_id = "waiting_on"
            task.position = next_pos
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
    """Return all Waiting On tasks, sorted by position.

    Includes undated, future-dated, and past-dated tasks — the full view of
    what you are waiting on from others. Position order is preserved so that
    J/K reordering within the Waiting On view works correctly.
    """
    return sorted(
        [t for t in tasks if t.folder_id == "waiting_on"],
        key=lambda t: t.position,
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
# Search
# ---------------------------------------------------------------------------

_SEARCH_FOLDER_PRIORITY: dict[str, int] = {
    "today": 0,
    "upcoming": 1,
    "waiting_on": 2,
    "someday": 3,
}


def search_tasks(tasks: list[Task], query: str) -> list[tuple[Task, str]]:
    """Full-text search across all tasks by title and notes, case-insensitive.

    Returns (task, match_type) pairs where match_type is "title" or "notes".
    Ordering:
      1. Active tasks (not logbook): title matches first, then notes matches;
         within each group sorted by folder priority then position.
      2. Logbook tasks: title matches first, then notes matches;
         within each group sorted by recency (most-recently completed first).
    Returns empty list for an empty/whitespace-only query.
    """
    if not query.strip():
        return []
    q = query.lower()
    active: list[tuple[Task, str]] = []
    logbook_results: list[tuple[Task, str]] = []

    for task in tasks:
        if q in task.title.lower():
            match_type = "title"
        elif q in task.notes.lower():
            match_type = "notes"
        else:
            continue
        if task.folder_id == "logbook":
            logbook_results.append((task, match_type))
        else:
            active.append((task, match_type))

    active.sort(
        key=lambda r: (
            0 if r[1] == "title" else 1,
            _SEARCH_FOLDER_PRIORITY.get(r[0].folder_id, 4),
            r[0].position,
        )
    )
    logbook_results.sort(
        key=lambda r: (
            0 if r[1] == "title" else 1,
            -(r[0].completed_at.timestamp() if r[0].completed_at else 0),
        )
    )
    return active + logbook_results


# ---------------------------------------------------------------------------
# Repeat rule parsing
# ---------------------------------------------------------------------------

_UNIT_ALIASES: dict[str, str] = {
    "d": "days", "day": "days", "days": "days",
    "w": "weeks", "week": "weeks", "weeks": "weeks",
    "m": "months", "month": "months", "months": "months",
    "y": "years", "year": "years", "years": "years",
}


class InvalidRepeatError(ValueError):
    """Raised when a repeat input string cannot be parsed."""


def parse_repeat_input(text: str) -> tuple[int, str] | None:
    """Parse a repeat interval string into (interval, unit).

    Accepted formats: '7 days', '7d', '2 weeks', '2w', '1 month', '1 year'.
    Returns None for empty input.  Raises InvalidRepeatError for bad input.
    """
    text = text.strip().lower()
    if not text:
        return None
    m = re.match(r"^(\d+)\s*([a-z]+)$", text)
    if not m:
        raise InvalidRepeatError(f"Cannot parse repeat: {text!r}")
    interval = int(m.group(1))
    unit = _UNIT_ALIASES.get(m.group(2))
    if unit is None or interval <= 0:
        raise InvalidRepeatError(f"Cannot parse repeat: {text!r}")
    return interval, unit


def make_repeat_rule(
    interval: int, unit: str, from_date: date | None = None
) -> RepeatRule:
    """Create a RepeatRule whose next_due is one interval after from_date (default: today)."""
    base = from_date or date.today()
    return RepeatRule(interval=interval, unit=unit, next_due=_advance_date(base, interval, unit))


def set_repeat_rule(
    tasks: list[Task], task_id: str, rule: RepeatRule | None
) -> list[Task]:
    """Set or clear the repeat rule on a task. No-op for unknown task_id."""
    for task in tasks:
        if task.id == task_id:
            task.repeat_rule = rule
    return tasks


# ---------------------------------------------------------------------------
# Repeating task spawning
# ---------------------------------------------------------------------------


def spawn_repeating_tasks(
    tasks: list[Task], as_of: date | None = None
) -> list[Task]:
    """Spawn copies of repeating tasks whose next_due has arrived.

    For each task with a repeat_rule where next_due <= today:
    - Creates one copy in Today (no repeat rule on the copy).
    - Advances next_due on the original past today, skipping any missed periods.

    If the app was not opened for multiple intervals, only one copy is spawned
    (the current/most-recent due instance) to avoid flooding Today.
    """
    ref = as_of or date.today()
    spawned: list[Task] = []

    for task in tasks:
        if task.repeat_rule is None or task.repeat_rule.next_due > ref:
            continue
        rule = task.repeat_rule
        spawned.append(Task(title=task.title, notes=task.notes, folder_id="today"))
        while rule.next_due <= ref:
            rule.next_due = _advance_date(rule.next_due, rule.interval, rule.unit)

    if not spawned:
        return tasks

    n = len(spawned)
    for task in tasks:
        if task.folder_id == "today":
            task.position += n
    for i, task in enumerate(spawned):
        task.position = i

    return tasks + spawned


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


def _advance_date(d: date, interval: int, unit: str) -> date:
    """Advance a date by one repeat interval."""
    if unit == "days":
        return d + timedelta(days=interval)
    if unit == "weeks":
        return d + timedelta(weeks=interval)
    if unit == "months":
        month = d.month + interval
        year = d.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    # years
    try:
        return date(d.year + interval, d.month, d.day)
    except ValueError:  # Feb 29 in non-leap year
        return date(d.year + interval, d.month, 28)
