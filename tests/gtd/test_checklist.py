"""Tests for BACKLOG-29: Checklist sub-steps within a task."""

from __future__ import annotations

from gtd_tui.gtd.operations import (
    add_checklist_item,
    add_task,
    delete_checklist_item,
    move_checklist_item,
    toggle_checklist_item,
)
from gtd_tui.gtd.task import Task


def _task() -> Task:
    tasks = add_task([], "My task")
    return tasks[0]


def _task_id(tasks: list[Task]) -> str:
    return tasks[0].id


# --- add_checklist_item ---


def test_add_checklist_item_appends_item() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    assert len(tasks[0].checklist) == 1
    assert tasks[0].checklist[0].label == "Step 1"
    assert tasks[0].checklist[0].checked is False


def test_add_checklist_item_multiple_items() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    tasks = add_checklist_item(tasks, tid, "Step 2")
    assert len(tasks[0].checklist) == 2
    assert tasks[0].checklist[1].label == "Step 2"


def test_add_checklist_item_does_not_affect_other_tasks() -> None:
    tasks = add_task([], "Task B")
    tasks = add_task(tasks, "Task A")
    tid_a = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_checklist_item(tasks, tid_a, "Item")
    task_b = next(t for t in tasks if t.title == "Task B")
    assert task_b.checklist == []


# --- toggle_checklist_item ---


def test_toggle_checklist_item_marks_checked() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    item_id = tasks[0].checklist[0].id
    tasks = toggle_checklist_item(tasks, tid, item_id)
    assert tasks[0].checklist[0].checked is True


def test_toggle_checklist_item_unchecks() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    item_id = tasks[0].checklist[0].id
    tasks = toggle_checklist_item(tasks, tid, item_id)
    tasks = toggle_checklist_item(tasks, tid, item_id)
    assert tasks[0].checklist[0].checked is False


# --- delete_checklist_item ---


def test_delete_checklist_item_removes_item() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    tasks = add_checklist_item(tasks, tid, "Step 2")
    item_id = tasks[0].checklist[0].id
    tasks = delete_checklist_item(tasks, tid, item_id)
    assert len(tasks[0].checklist) == 1
    assert tasks[0].checklist[0].label == "Step 2"


def test_delete_checklist_item_nonexistent_is_noop() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    tasks = delete_checklist_item(tasks, tid, "not-a-real-id")
    assert len(tasks[0].checklist) == 1


# --- move_checklist_item ---


def test_move_checklist_item_down() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "A")
    tasks = add_checklist_item(tasks, tid, "B")
    tasks = add_checklist_item(tasks, tid, "C")
    item_id = tasks[0].checklist[0].id  # "A"
    tasks = move_checklist_item(tasks, tid, item_id, 1)
    assert [i.label for i in tasks[0].checklist] == ["B", "A", "C"]


def test_move_checklist_item_up() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "A")
    tasks = add_checklist_item(tasks, tid, "B")
    tasks = add_checklist_item(tasks, tid, "C")
    item_id = tasks[0].checklist[2].id  # "C"
    tasks = move_checklist_item(tasks, tid, item_id, -1)
    assert [i.label for i in tasks[0].checklist] == ["A", "C", "B"]


def test_move_checklist_item_clamped_at_boundaries() -> None:
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "A")
    tasks = add_checklist_item(tasks, tid, "B")
    item_id = tasks[0].checklist[0].id
    tasks = move_checklist_item(tasks, tid, item_id, -1)  # already at top
    assert [i.label for i in tasks[0].checklist] == ["A", "B"]


# --- storage round-trip ---


def test_checklist_storage_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_tasks, save_data

    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = add_checklist_item(tasks, tid, "Step 1")
    tasks = toggle_checklist_item(tasks, tid, tasks[0].checklist[0].id)
    tasks = add_checklist_item(tasks, tid, "Step 2")
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    task = next(t for t in loaded if t.id == tid)
    assert len(task.checklist) == 2
    assert task.checklist[0].label == "Step 1"
    assert task.checklist[0].checked is True
    assert task.checklist[1].label == "Step 2"
    assert task.checklist[1].checked is False


def test_checklist_default_empty_for_old_tasks(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Old JSON files without checklist field load without error."""
    import json

    from gtd_tui.storage.file import load_tasks

    data_file = tmp_path / "data.json"
    # Write a task dict without the checklist key
    raw = {
        "tasks": [
            {
                "id": "abc",
                "title": "Old task",
                "notes": "",
                "folder_id": "today",
                "position": 0,
                "completed_at": None,
                "scheduled_date": None,
                "deadline": None,
                "repeat_rule": None,
                "recur_rule": None,
                "created_at": None,
                "is_deleted": False,
            }
        ],
        "folders": [],
    }
    data_file.write_text(json.dumps(raw))
    tasks = load_tasks(data_file=data_file)
    assert tasks[0].checklist == []
