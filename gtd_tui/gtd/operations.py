from __future__ import annotations

import calendar
import re
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Literal

from gtd_tui.gtd.area import Area
from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.project import Project
from gtd_tui.gtd.task import ChecklistItem, RecurRule, RepeatRule, Task

_UnitLiteral = Literal["days", "weeks", "months", "years"]

# Folders whose tasks never auto-surface in Today or Upcoming smart views.
_EXCLUDED_FROM_SMART_VIEWS: frozenset[str] = frozenset({"inbox", "someday", "logbook"})


def add_task(
    tasks: list[Task], title: str, notes: str = "", task_id: str | None = None
) -> list[Task]:
    """Add a new task to the top of Today. Returns updated task list."""
    for task in tasks:
        if task.folder_id == "today":
            task.position += 1
    kwargs = {
        "title": title,
        "notes": notes,
        "folder_id": "today",
        "position": 0,
        "created_at": datetime.now(),
    }
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
        "created_at": datetime.now(),
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
        "created_at": datetime.now(),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    new_task = Task(**kwargs)  # type: ignore[arg-type]
    return tasks + [new_task]


def edit_task(
    tasks: list[Task], task_id: str, title: str, notes: str = ""
) -> list[Task]:
    """Update a task's title and notes. No-op if task_id is not found."""
    for task in tasks:
        if task.id == task_id:
            task.title = title
            task.notes = notes
    return tasks


def complete_task(tasks: list[Task], task_id: str) -> list[Task]:
    """Mark a task complete and move it to the logbook.

    If the task has a recur_rule, spawns a new copy in Today with
    scheduled_date = completion_date + interval, carrying the same recur_rule.

    If the task has a repeat_rule (calendar-fixed), spawns a new template task
    in the same folder with scheduled_date = next_due (future), so that the
    repeat schedule survives the completion and stays visible in Upcoming.
    """
    spawned: list[Task] = []
    ref = date.today()
    for task in tasks:
        if task.id == task_id:
            original_folder_id = task.folder_id
            task.complete()
            if task.recur_rule is not None:
                rule = task.recur_rule
                new_date = _advance_date(
                    task.completed_at.date(), rule.interval, rule.unit  # type: ignore[union-attr]
                )
                spawned.append(
                    Task(
                        title=task.title,
                        notes=task.notes,
                        folder_id="today",
                        scheduled_date=new_date,
                        recur_rule=rule,
                    )
                )
            elif task.repeat_rule is not None:
                # Advance next_due to be strictly in the future so the new
                # template only appears in Upcoming, not in Today's active list.
                next_due = task.repeat_rule.next_due
                while next_due <= ref:
                    next_due = _advance_date(
                        next_due, task.repeat_rule.interval, task.repeat_rule.unit
                    )
                new_rule = RepeatRule(
                    interval=task.repeat_rule.interval,
                    unit=task.repeat_rule.unit,
                    next_due=next_due,
                )
                spawned.append(
                    Task(
                        title=task.title,
                        notes=task.notes,
                        folder_id=original_folder_id,
                        scheduled_date=next_due,
                        repeat_rule=new_rule,
                    )
                )
    return tasks + spawned


def delete_task(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task to the logbook marked as deleted (not completed)."""
    for task in tasks:
        if task.id == task_id:
            task.delete()
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


def set_deadline(tasks: list[Task], task_id: str, deadline: date) -> list[Task]:
    """Set a hard deadline on a task. No-op for unknown task_id."""
    for task in tasks:
        if task.id == task_id:
            task.deadline = deadline
    return tasks


def clear_deadline(tasks: list[Task], task_id: str) -> list[Task]:
    """Remove the deadline from a task. No-op for unknown task_id."""
    for task in tasks:
        if task.id == task_id:
            task.deadline = None
    return tasks


def deadline_status(task: Task, as_of: date | None = None) -> tuple[str, str] | None:
    """Return (display_text, status) for a task's deadline, or None if no deadline.

    status is one of: 'overdue', 'soon' (<=3 days), 'ok' (>3 days).
    display_text is formatted as 'Mar 16 Mon — 2d overdue' or 'Mar 16 Mon — 3d left'.
    """
    if task.deadline is None:
        return None
    from gtd_tui.gtd.dates import format_date

    ref = as_of or date.today()
    delta = (task.deadline - ref).days
    date_str = format_date(task.deadline)
    if delta < 0:
        return (f"{date_str} — {abs(delta)}d overdue", "overdue")
    elif delta == 0:
        return (f"{date_str} — today", "soon")
    elif delta <= 3:
        return (f"{date_str} — {delta}d left", "soon")
    else:
        return (f"{date_str} — {delta}d left", "ok")


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

    Includes tasks (except 'someday' and 'logbook') that have either:
    - a scheduled_date strictly in the future, OR
    - a repeat_rule whose next_due is strictly in the future.

    Tasks with a repeat rule stay in Today (they are still actionable) and also
    appear here to preview the next scheduled occurrence.  Sorted by the
    effective future date, then position.
    """
    ref = as_of or date.today()

    def _future_date(t: Task) -> date | None:
        if t.scheduled_date is not None and t.scheduled_date > ref:
            return t.scheduled_date
        if t.repeat_rule is not None and t.repeat_rule.next_due > ref:
            return t.repeat_rule.next_due
        return None

    result = [
        t
        for t in tasks
        if t.folder_id not in _EXCLUDED_FROM_SMART_VIEWS and _future_date(t) is not None
    ]
    return sorted(result, key=lambda t: (_future_date(t), t.position))


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


def inbox_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks in the Inbox folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == "inbox"],
        key=lambda t: t.position,
    )


def someday_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks in the Someday folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == "someday"],
        key=lambda t: t.position,
    )


def reference_tasks(tasks: list[Task]) -> list[Task]:
    """Return tasks in the Reference folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == "reference"],
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


def move_block_down(tasks: list[Task], task_ids: set[str]) -> list[Task]:
    """Move a block of tasks down by one position as a unit.

    Rotates the single task immediately below the block to just above the block,
    keeping the block's internal order intact.  No-op if the block is already
    at the last position or any task_id is not found.
    """
    block = [t for t in tasks if t.id in task_ids]
    if not block:
        return tasks
    peers = _visible_peers(tasks, block[0])
    block_peer_indices = sorted(i for i, t in enumerate(peers) if t.id in task_ids)
    if not block_peer_indices:
        return tasks
    bottom_idx = block_peer_indices[-1]
    if bottom_idx >= len(peers) - 1:
        return tasks  # block is at the boundary
    after_task = peers[bottom_idx + 1]
    # Collect positions of [block tasks in order] + [after_task]
    involved = block_peer_indices + [bottom_idx + 1]
    positions = [peers[i].position for i in involved]
    # Rotate left: after_task gets the top block position; block tasks shift down
    after_task.position = positions[0]
    for i, peer_idx in enumerate(block_peer_indices):
        peers[peer_idx].position = positions[i + 1]
    return tasks


def move_block_up(tasks: list[Task], task_ids: set[str]) -> list[Task]:
    """Move a block of tasks up by one position as a unit.

    Rotates the single task immediately above the block to just below the block,
    keeping the block's internal order intact.  No-op if the block is already
    at the first position or any task_id is not found.
    """
    block = [t for t in tasks if t.id in task_ids]
    if not block:
        return tasks
    peers = _visible_peers(tasks, block[0])
    block_peer_indices = sorted(i for i, t in enumerate(peers) if t.id in task_ids)
    if not block_peer_indices:
        return tasks
    top_idx = block_peer_indices[0]
    if top_idx == 0:
        return tasks  # block is at the boundary
    before_task = peers[top_idx - 1]
    # Collect positions of [before_task] + [block tasks in order]
    involved = [top_idx - 1] + block_peer_indices
    positions = [peers[i].position for i in involved]
    # Rotate right: before_task gets the bottom block position; block tasks shift up
    before_task.position = positions[-1]
    for i, peer_idx in enumerate(block_peer_indices):
        peers[peer_idx].position = positions[i]
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


def weekly_review_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
    """Return tasks completed (not deleted) in the past 7 days, most recent first.

    Note: completed tasks all have folder_id='logbook', so folder grouping by
    original folder is not possible without additional data. Results are returned
    as a flat chronological list.
    """
    ref = as_of or date.today()
    cutoff = ref - timedelta(days=7)
    return sorted(
        [
            t
            for t in tasks
            if t.folder_id == "logbook"
            and not t.is_deleted
            and t.completed_at is not None
            and t.completed_at.date() >= cutoff
        ],
        key=lambda t: t.completed_at or datetime.min,
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Waiting On folder
# ---------------------------------------------------------------------------


def add_waiting_on_task(
    tasks: list[Task], title: str, notes: str = "", task_id: str | None = None
) -> list[Task]:
    """Add a new task to the end of the Waiting On folder."""
    existing = folder_tasks(tasks, "waiting_on")
    next_pos = existing[-1].position + 1 if existing else 0
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": "waiting_on",
        "position": next_pos,
        "created_at": datetime.now(),
        "scheduled_date": date.today() + timedelta(days=7),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def insert_waiting_on_task_after(
    tasks: list[Task],
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new WO task immediately after the anchor WO task.

    Falls back to add_waiting_on_task if anchor_id is not found.
    """
    wo = sorted(
        [t for t in tasks if t.folder_id == "waiting_on"], key=lambda t: t.position
    )
    anchor = next((t for t in wo if t.id == anchor_id), None)
    if anchor is None:
        return add_waiting_on_task(tasks, title, notes, task_id)
    insert_pos = anchor.position + 1
    for task in tasks:
        if task.folder_id == "waiting_on" and task.position >= insert_pos:
            task.position += 1
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": "waiting_on",
        "position": insert_pos,
        "created_at": datetime.now(),
        "scheduled_date": date.today() + timedelta(days=7),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def insert_waiting_on_task_before(
    tasks: list[Task],
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new WO task immediately before the anchor WO task.

    Falls back to add_waiting_on_task if anchor_id is not found.
    """
    wo = sorted(
        [t for t in tasks if t.folder_id == "waiting_on"], key=lambda t: t.position
    )
    anchor = next((t for t in wo if t.id == anchor_id), None)
    if anchor is None:
        return add_waiting_on_task(tasks, title, notes, task_id)
    insert_pos = anchor.position
    for task in tasks:
        if task.folder_id == "waiting_on" and task.position >= insert_pos:
            task.position += 1
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": "waiting_on",
        "position": insert_pos,
        "created_at": datetime.now(),
        "scheduled_date": date.today() + timedelta(days=7),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def move_to_waiting_on(tasks: list[Task], task_id: str) -> list[Task]:
    """Move a task to the Waiting On folder at position 0 (top). Preserves any scheduled date."""
    for task in tasks:
        if task.folder_id == "waiting_on":
            task.position += 1
    for task in tasks:
        if task.id == task_id:
            task.folder_id = "waiting_on"
            task.position = 0
            if task.scheduled_date is None:
                task.scheduled_date = date.today() + timedelta(days=7)
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
        "created_at": datetime.now(),
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


def insert_folder(
    folders: list[Folder],
    name: str,
    anchor_id: str | None,
    insert_position: str,
    folder_id: str | None = None,
) -> list[Folder]:
    """Insert a new folder relative to an anchor folder.

    insert_position: 'after' inserts below anchor, 'before' inserts above it,
    'end' (or anchor_id=None) appends after all existing folders.
    All folders are renumbered 0, 1, 2… after insertion.
    """
    import copy as _copy

    result = [_copy.copy(f) for f in folders]
    sorted_result = sorted(result, key=lambda f: f.position)
    new_kwargs: dict = {"name": name, "position": 0}
    if folder_id is not None:
        new_kwargs["id"] = folder_id
    new_folder = Folder(**new_kwargs)
    if insert_position == "end" or anchor_id is None:
        sorted_result.append(new_folder)
    else:
        anchor_idx = next(
            (i for i, f in enumerate(sorted_result) if f.id == anchor_id), None
        )
        if anchor_idx is None:
            sorted_result.append(new_folder)
        elif insert_position == "after":
            sorted_result.insert(anchor_idx + 1, new_folder)
        else:
            sorted_result.insert(anchor_idx, new_folder)
    for i, f in enumerate(sorted_result):
        f.position = i
    return sorted_result


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


def move_folder_up(folders: list[Folder], folder_id: str) -> list[Folder]:
    """Swap a folder with the sibling above it within the same area. No-op at top."""
    folder = next((f for f in folders if f.id == folder_id), None)
    if folder is None:
        return folders
    siblings = sorted(
        [f for f in folders if f.area_id == folder.area_id],
        key=lambda f: f.position,
    )
    idx = next((i for i, f in enumerate(siblings) if f.id == folder_id), None)
    if idx is None or idx == 0:
        return folders
    siblings[idx].position, siblings[idx - 1].position = (
        siblings[idx - 1].position,
        siblings[idx].position,
    )
    return folders


def move_folder_down(folders: list[Folder], folder_id: str) -> list[Folder]:
    """Swap a folder with the sibling below it within the same area. No-op at bottom."""
    folder = next((f for f in folders if f.id == folder_id), None)
    if folder is None:
        return folders
    siblings = sorted(
        [f for f in folders if f.area_id == folder.area_id],
        key=lambda f: f.position,
    )
    idx = next((i for i, f in enumerate(siblings) if f.id == folder_id), None)
    if idx is None or idx == len(siblings) - 1:
        return folders
    siblings[idx].position, siblings[idx + 1].position = (
        siblings[idx + 1].position,
        siblings[idx].position,
    )
    return folders


def purge_logbook_task(tasks: list[Task], task_id: str) -> list[Task]:
    """Permanently remove a logbook entry. No-op if the task is not in the logbook."""
    return [t for t in tasks if not (t.id == task_id and t.folder_id == "logbook")]


def folder_tasks(tasks: list[Task], folder_id: str) -> list[Task]:
    """Return tasks belonging to the given folder, sorted by position."""
    return sorted(
        [t for t in tasks if t.folder_id == folder_id],
        key=lambda t: t.position,
    )


def insert_folder_task_after(
    tasks: list[Task],
    folder_id: str,
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new task immediately after the anchor task in the given folder.

    Falls back to add_task_to_folder if anchor_id is not found.
    """
    members = sorted(
        [t for t in tasks if t.folder_id == folder_id], key=lambda t: t.position
    )
    anchor = next((t for t in members if t.id == anchor_id), None)
    if anchor is None:
        return add_task_to_folder(tasks, folder_id, title, notes, task_id)
    insert_pos = anchor.position + 1
    for task in tasks:
        if task.folder_id == folder_id and task.position >= insert_pos:
            task.position += 1
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": folder_id,
        "position": insert_pos,
        "created_at": datetime.now(),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def insert_folder_task_before(
    tasks: list[Task],
    folder_id: str,
    anchor_id: str,
    title: str,
    notes: str = "",
    task_id: str | None = None,
) -> list[Task]:
    """Insert a new task immediately before the anchor task in the given folder.

    Falls back to add_task_to_folder if anchor_id is not found.
    """
    members = sorted(
        [t for t in tasks if t.folder_id == folder_id], key=lambda t: t.position
    )
    anchor = next((t for t in members if t.id == anchor_id), None)
    if anchor is None:
        return add_task_to_folder(tasks, folder_id, title, notes, task_id)
    insert_pos = anchor.position
    for task in tasks:
        if task.folder_id == folder_id and task.position >= insert_pos:
            task.position += 1
    kwargs: dict = {
        "title": title,
        "notes": notes,
        "folder_id": folder_id,
        "position": insert_pos,
        "created_at": datetime.now(),
    }
    if task_id is not None:
        kwargs["id"] = task_id
    return tasks + [Task(**kwargs)]  # type: ignore[arg-type]


def move_task_to_folder(tasks: list[Task], task_id: str, folder_id: str) -> list[Task]:
    """Move a task to a different folder, inserting it at position 0 (top)."""
    for task in tasks:
        if task.folder_id == folder_id:
            task.position += 1
    for task in tasks:
        if task.id == task_id:
            task.folder_id = folder_id
            task.position = 0
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

_UNIT_ALIASES: dict[str, _UnitLiteral] = {
    "d": "days",
    "day": "days",
    "days": "days",
    "w": "weeks",
    "week": "weeks",
    "weeks": "weeks",
    "m": "months",
    "month": "months",
    "months": "months",
    "y": "years",
    "year": "years",
    "years": "years",
}


class InvalidRepeatError(ValueError):
    """Raised when a repeat input string cannot be parsed."""


def parse_repeat_input(text: str) -> tuple[int, _UnitLiteral] | None:
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
    interval: int, unit: _UnitLiteral, from_date: date | None = None
) -> RepeatRule:
    """Create a RepeatRule whose next_due is one interval after from_date (default: today)."""
    base = from_date or date.today()
    return RepeatRule(
        interval=interval, unit=unit, next_due=_advance_date(base, interval, unit)
    )


def set_repeat_rule(
    tasks: list[Task], task_id: str, rule: RepeatRule | None
) -> list[Task]:
    """Set or clear the repeat rule on a task. No-op for unknown task_id."""
    for task in tasks:
        if task.id == task_id:
            task.repeat_rule = rule
    return tasks


def set_recur_rule(
    tasks: list[Task], task_id: str, rule: RecurRule | None
) -> list[Task]:
    """Set or clear the recur rule on a task. No-op for unknown task_id."""
    for task in tasks:
        if task.id == task_id:
            task.recur_rule = rule
    return tasks


# ---------------------------------------------------------------------------
# Repeating task spawning
# ---------------------------------------------------------------------------


def spawn_repeating_tasks(tasks: list[Task], as_of: date | None = None) -> list[Task]:
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
        # If the original lives in Today, give it a future scheduled_date equal to
        # next_due so it no longer appears in Today's active list — only in Upcoming.
        # This prevents the user from accidentally completing the template instead of
        # the spawned copy, which would remove the repeat from Upcoming.
        if task.folder_id == "today":
            task.scheduled_date = rule.next_due

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
# Tags / Contexts
# ---------------------------------------------------------------------------


def add_tag(tasks: list[Task], task_id: str, tag: str) -> list[Task]:
    """Add a tag to a task (no-op if already present)."""
    tag = tag.strip()
    if not tag:
        return tasks
    return [
        replace(t, tags=[*t.tags, tag]) if t.id == task_id and tag not in t.tags else t
        for t in tasks
    ]


def remove_tag(tasks: list[Task], task_id: str, tag: str) -> list[Task]:
    """Remove a tag from a task."""
    return [
        replace(t, tags=[x for x in t.tags if x != tag]) if t.id == task_id else t
        for t in tasks
    ]


def set_tags(tasks: list[Task], task_id: str, tags: list[str]) -> list[Task]:
    """Replace the tags list for a task."""
    return [replace(t, tags=tags) if t.id == task_id else t for t in tasks]


def all_tags(tasks: list[Task]) -> list[tuple[str, int]]:
    """Return sorted list of (tag, count) tuples across all non-logbook tasks."""
    counts: dict[str, int] = {}
    for t in tasks:
        if t.folder_id != "logbook" and not t.is_deleted:
            for tag in t.tags:
                counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items())


def tasks_with_tag(tasks: list[Task], tag: str) -> list[Task]:
    """Return all non-logbook tasks that have the given tag, sorted by position."""
    return sorted(
        [
            t
            for t in tasks
            if tag in t.tags and t.folder_id != "logbook" and not t.is_deleted
        ],
        key=lambda t: t.position,
    )


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------


def add_project(
    projects: list[Project],
    title: str,
    folder_id: str = "today",
    deadline: date | None = None,
) -> list[Project]:
    """Add a new project at the end of the list."""
    position = max((p.position for p in projects), default=-1) + 1
    return [
        *projects,
        Project(
            title=title,
            folder_id=folder_id,
            position=position,
            deadline=deadline,
            created_at=datetime.now(),
        ),
    ]


def delete_project(projects: list[Project], project_id: str) -> list[Project]:
    """Remove a project by ID."""
    return [p for p in projects if p.id != project_id]


def rename_project(
    projects: list[Project], project_id: str, title: str
) -> list[Project]:
    """Rename a project."""
    return [replace(p, title=title) if p.id == project_id else p for p in projects]


def move_project_up(projects: list[Project], project_id: str) -> list[Project]:
    """Swap a project with the sibling above it within the same area. No-op at top."""
    project = next((p for p in projects if p.id == project_id), None)
    if project is None:
        return projects
    siblings = sorted(
        [p for p in projects if p.area_id == project.area_id],
        key=lambda p: p.position,
    )
    idx = next((i for i, p in enumerate(siblings) if p.id == project_id), None)
    if idx is None or idx == 0:
        return projects
    siblings[idx].position, siblings[idx - 1].position = (
        siblings[idx - 1].position,
        siblings[idx].position,
    )
    return projects


def move_project_down(projects: list[Project], project_id: str) -> list[Project]:
    """Swap a project with the sibling below it within the same area. No-op at bottom."""
    project = next((p for p in projects if p.id == project_id), None)
    if project is None:
        return projects
    siblings = sorted(
        [p for p in projects if p.area_id == project.area_id],
        key=lambda p: p.position,
    )
    idx = next((i for i, p in enumerate(siblings) if p.id == project_id), None)
    if idx is None or idx == len(siblings) - 1:
        return projects
    siblings[idx].position, siblings[idx + 1].position = (
        siblings[idx + 1].position,
        siblings[idx].position,
    )
    return projects


def move_tag_up(tag_order: list[str], tag_name: str) -> list[str]:
    """Move a tag one position earlier in the ordering. No-op if already first."""
    if tag_name not in tag_order:
        return tag_order
    idx = tag_order.index(tag_name)
    if idx == 0:
        return tag_order
    result = list(tag_order)
    result[idx], result[idx - 1] = result[idx - 1], result[idx]
    return result


def move_tag_down(tag_order: list[str], tag_name: str) -> list[str]:
    """Move a tag one position later in the ordering. No-op if already last."""
    if tag_name not in tag_order:
        return tag_order
    idx = tag_order.index(tag_name)
    if idx == len(tag_order) - 1:
        return tag_order
    result = list(tag_order)
    result[idx], result[idx + 1] = result[idx + 1], result[idx]
    return result


def unlink_project_tasks(tasks: list[Task], project_id: str) -> list[Task]:
    """Clear project_id on all tasks belonging to the given project."""
    return [
        replace(t, project_id=None) if t.project_id == project_id else t for t in tasks
    ]


def complete_project(projects: list[Project], project_id: str) -> list[Project]:
    """Mark a project as complete."""
    return [
        replace(p, completed_at=datetime.now()) if p.id == project_id else p
        for p in projects
    ]


def project_tasks(tasks: list[Task], project_id: str) -> list[Task]:
    """Return all active (non-logbook) sub-tasks of a project, sorted by position."""
    return sorted(
        [
            t
            for t in tasks
            if t.project_id == project_id
            and t.folder_id != "logbook"
            and not t.is_deleted
        ],
        key=lambda t: t.position,
    )


def project_progress(tasks: list[Task], project_id: str) -> tuple[int, int]:
    """Return (completed, total) for a project's sub-tasks."""
    sub = [t for t in tasks if t.project_id == project_id and not t.is_deleted]
    total = len(sub)
    done = sum(1 for t in sub if t.is_complete)
    return done, total


def check_auto_complete_project(
    tasks: list[Task], projects: list[Project], project_id: str
) -> list[Project]:
    """If all sub-tasks of a project are complete, auto-complete the project."""
    sub = [t for t in tasks if t.project_id == project_id and not t.is_deleted]
    if not sub:
        return projects
    if all(t.is_complete for t in sub):
        return complete_project(projects, project_id)
    return projects


def add_task_to_project(
    tasks: list[Task], project_id: str, title: str, notes: str = ""
) -> list[Task]:
    """Add a new task as a sub-task of a project."""
    existing = project_tasks(tasks, project_id)
    position = max((t.position for t in existing), default=-1) + 1
    new_task = Task(
        title=title,
        notes=notes,
        project_id=project_id,
        folder_id="today",
        position=position,
        created_at=datetime.now(),
    )
    return [*tasks, new_task]


def assign_task_to_project(
    tasks: list[Task], task_id: str, project_id: str | None
) -> list[Task]:
    """Assign (or unassign) a task to a project."""
    return [replace(t, project_id=project_id) if t.id == task_id else t for t in tasks]


# ---------------------------------------------------------------------------
# Area operations
# ---------------------------------------------------------------------------


def add_area(areas: list[Area], name: str) -> list[Area]:
    """Add a new area at the end of the list."""
    position = max((a.position for a in areas), default=-1) + 1
    return [*areas, Area(name=name, position=position)]


def delete_area(areas: list[Area], area_id: str) -> list[Area]:
    """Remove an area by ID."""
    return [a for a in areas if a.id != area_id]


def rename_area(areas: list[Area], area_id: str, name: str) -> list[Area]:
    """Rename an area."""
    return [replace(a, name=name) if a.id == area_id else a for a in areas]


def assign_folder_to_area(
    folders: list[Folder], folder_id: str, area_id: str | None
) -> list[Folder]:
    """Assign (or unassign) a folder to an area."""
    return [replace(f, area_id=area_id) if f.id == folder_id else f for f in folders]


def assign_project_to_area(
    projects: list[Project], project_id: str, area_id: str | None
) -> list[Project]:
    """Assign (or unassign) a project to an area."""
    return [replace(p, area_id=area_id) if p.id == project_id else p for p in projects]


# ---------------------------------------------------------------------------
# Checklist operations
# ---------------------------------------------------------------------------


def add_checklist_item(tasks: list[Task], task_id: str, label: str) -> list[Task]:
    """Append a new unchecked checklist item to the given task."""
    return [
        (
            replace(t, checklist=[*t.checklist, ChecklistItem(label=label)])
            if t.id == task_id
            else t
        )
        for t in tasks
    ]


def toggle_checklist_item(tasks: list[Task], task_id: str, item_id: str) -> list[Task]:
    """Toggle the checked state of a checklist item."""

    def _toggle(t: Task) -> Task:
        if t.id != task_id:
            return t
        new_checklist = [
            replace(item, checked=not item.checked) if item.id == item_id else item
            for item in t.checklist
        ]
        return replace(t, checklist=new_checklist)

    return [_toggle(t) for t in tasks]


def delete_checklist_item(tasks: list[Task], task_id: str, item_id: str) -> list[Task]:
    """Remove a checklist item by id."""

    def _delete(t: Task) -> Task:
        if t.id != task_id:
            return t
        return replace(t, checklist=[i for i in t.checklist if i.id != item_id])

    return [_delete(t) for t in tasks]


def move_checklist_item(
    tasks: list[Task], task_id: str, item_id: str, delta: int
) -> list[Task]:
    """Move a checklist item up (delta=-1) or down (delta=+1)."""

    def _move(t: Task) -> Task:
        if t.id != task_id:
            return t
        items = list(t.checklist)
        idx = next((i for i, it in enumerate(items) if it.id == item_id), None)
        if idx is None:
            return t
        new_idx = max(0, min(len(items) - 1, idx + delta))
        items.insert(new_idx, items.pop(idx))
        return replace(t, checklist=items)

    return [_move(t) for t in tasks]


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
