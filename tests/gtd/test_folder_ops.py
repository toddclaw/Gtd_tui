"""Tests for BACKLOG-4: user-created folder operations."""
from __future__ import annotations

import pytest

from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.operations import (
    add_task,
    create_folder,
    delete_folder,
    discard_folder_tasks,
    folder_tasks,
    move_folder_tasks_to_today,
    move_task_to_folder,
    rename_folder,
    today_tasks,
)


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


def test_create_folder_appends_to_list():
    folders = create_folder([], "Work")
    assert len(folders) == 1
    assert folders[0].name == "Work"


def test_create_folder_assigns_position_zero_when_empty():
    folders = create_folder([], "Work")
    assert folders[0].position == 0


def test_create_folder_appends_after_existing():
    folders = create_folder([], "Work")
    folders = create_folder(folders, "Personal")
    assert folders[1].name == "Personal"
    assert folders[1].position == 1


def test_create_folder_accepts_explicit_id():
    folders = create_folder([], "Work", folder_id="fixed-id")
    assert folders[0].id == "fixed-id"


def test_create_folder_generates_unique_id_when_not_provided():
    folders = create_folder([], "A")
    folders = create_folder(folders, "B")
    ids = [f.id for f in folders]
    assert ids[0] != ids[1]


# ---------------------------------------------------------------------------
# rename_folder
# ---------------------------------------------------------------------------


def test_rename_folder_updates_name():
    folders = create_folder([], "Work", folder_id="f1")
    folders = rename_folder(folders, "f1", "Work Projects")
    assert folders[0].name == "Work Projects"


def test_rename_folder_noop_for_builtin():
    folders: list[Folder] = []
    for bid in BUILTIN_FOLDER_IDS:
        result = rename_folder(folders, bid, "Renamed")
    # No folders were added, list stays empty
    assert folders == []


def test_rename_folder_noop_for_unknown_id():
    folders = create_folder([], "Work", folder_id="f1")
    folders = rename_folder(folders, "unknown-id", "Changed")
    assert folders[0].name == "Work"


# ---------------------------------------------------------------------------
# delete_folder
# ---------------------------------------------------------------------------


def test_delete_folder_removes_it():
    folders = create_folder([], "Work", folder_id="f1")
    folders = delete_folder(folders, "f1")
    assert folders == []


def test_delete_folder_noop_for_builtin():
    folders = create_folder([], "Work", folder_id="f1")
    for bid in BUILTIN_FOLDER_IDS:
        result = delete_folder(folders, bid)
        assert len(result) == 1  # folder "f1" still there


def test_delete_folder_only_removes_target():
    folders = create_folder([], "Work", folder_id="f1")
    folders = create_folder(folders, "Personal", folder_id="f2")
    folders = delete_folder(folders, "f1")
    assert len(folders) == 1
    assert folders[0].id == "f2"


# ---------------------------------------------------------------------------
# folder_tasks
# ---------------------------------------------------------------------------


def test_folder_tasks_returns_tasks_in_folder():
    tasks = add_task([], "Today task")
    from gtd_tui.gtd.operations import move_task_to_folder
    fid = "custom-folder"
    tasks = move_task_to_folder(tasks, tasks[0].id, fid)
    result = folder_tasks(tasks, fid)
    assert len(result) == 1
    assert result[0].title == "Today task"


def test_folder_tasks_returns_empty_for_unknown_folder():
    tasks = add_task([], "Today task")
    result = folder_tasks(tasks, "no-such-folder")
    assert result == []


def test_folder_tasks_sorted_by_position():
    tasks = add_task([], "A")
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "C")
    result = folder_tasks(tasks, "today")
    positions = [t.position for t in result]
    assert positions == sorted(positions)


# ---------------------------------------------------------------------------
# move_task_to_folder
# ---------------------------------------------------------------------------


def test_move_task_to_folder_changes_folder_id():
    tasks = add_task([], "My task")
    task_id = tasks[0].id
    tasks = move_task_to_folder(tasks, task_id, "custom")
    assert tasks[0].folder_id == "custom"


def test_move_task_to_folder_appends_at_end():
    tasks = add_task([], "Task A")
    tasks = add_task(tasks, "Task B")
    # Move Task A to a custom folder (currently has position 1)
    task_a_id = next(t.id for t in tasks if t.title == "Task A")
    tasks = move_task_to_folder(tasks, task_a_id, "custom")
    moved = next(t for t in tasks if t.title == "Task A")
    assert moved.position == 0  # first in "custom"


def test_move_task_to_folder_appends_after_existing():
    tasks = add_task([], "Task A")
    tasks = add_task(tasks, "Task B")
    a_id = next(t.id for t in tasks if t.title == "Task A")
    b_id = next(t.id for t in tasks if t.title == "Task B")
    tasks = move_task_to_folder(tasks, a_id, "custom")
    tasks = move_task_to_folder(tasks, b_id, "custom")
    custom = folder_tasks(tasks, "custom")
    assert custom[0].title == "Task A"
    assert custom[1].title == "Task B"


# ---------------------------------------------------------------------------
# discard_folder_tasks
# ---------------------------------------------------------------------------


def test_discard_folder_tasks_removes_all_tasks():
    tasks = add_task([], "Task A")
    tasks = add_task(tasks, "Task B")
    a_id = next(t.id for t in tasks if t.title == "Task A")
    tasks = move_task_to_folder(tasks, a_id, "custom")
    tasks = discard_folder_tasks(tasks, "custom")
    result = folder_tasks(tasks, "custom")
    assert result == []


def test_discard_folder_tasks_preserves_other_folders():
    tasks = add_task([], "Keep this")
    tasks = add_task(tasks, "Delete this")
    del_id = next(t.id for t in tasks if t.title == "Delete this")
    tasks = move_task_to_folder(tasks, del_id, "to-delete")
    tasks = discard_folder_tasks(tasks, "to-delete")
    remaining = folder_tasks(tasks, "today")
    assert len(remaining) == 1
    assert remaining[0].title == "Keep this"


# ---------------------------------------------------------------------------
# move_folder_tasks_to_today
# ---------------------------------------------------------------------------


def test_move_folder_tasks_to_today_changes_folder():
    tasks = add_task([], "Custom task")
    task_id = tasks[0].id
    tasks = move_task_to_folder(tasks, task_id, "custom")
    tasks = move_folder_tasks_to_today(tasks, "custom")
    assert tasks[0].folder_id == "today"


def test_move_folder_tasks_to_today_appends_after_existing():
    tasks = add_task([], "Today task")  # position 0
    tasks = add_task(tasks, "Custom task")
    custom_id = next(t.id for t in tasks if t.title == "Custom task")
    tasks = move_task_to_folder(tasks, custom_id, "custom")
    tasks = move_folder_tasks_to_today(tasks, "custom")
    today = today_tasks(tasks)
    titles = [t.title for t in today]
    assert "Today task" in titles
    assert "Custom task" in titles
    # Custom task appended after Today task
    custom_pos = next(t.position for t in today if t.title == "Custom task")
    today_pos = next(t.position for t in today if t.title == "Today task")
    assert custom_pos > today_pos
