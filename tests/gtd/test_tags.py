"""Tests for BACKLOG-30: Tags / Contexts."""

from __future__ import annotations

from gtd_tui.gtd.operations import (
    add_tag,
    add_task,
    all_tags,
    remove_tag,
    set_tags,
    tasks_with_tag,
)


def _tasks_ab() -> list:
    tasks = add_task([], "Task B")
    tasks = add_task(tasks, "Task A")
    return tasks


def test_add_tag_adds_tag() -> None:
    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    task = next(t for t in tasks if t.title == "Task A")
    assert "@home" in task.tags


def test_add_tag_no_duplicate() -> None:
    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    tasks = add_tag(tasks, tid, "@home")
    task = next(t for t in tasks if t.title == "Task A")
    assert task.tags.count("@home") == 1


def test_remove_tag() -> None:
    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    tasks = remove_tag(tasks, tid, "@home")
    task = next(t for t in tasks if t.title == "Task A")
    assert "@home" not in task.tags


def test_set_tags_replaces_all() -> None:
    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = set_tags(tasks, tid, ["@work", "@computer"])
    task = next(t for t in tasks if t.title == "Task A")
    assert task.tags == ["@work", "@computer"]


def test_all_tags_returns_sorted_with_counts() -> None:
    tasks = _tasks_ab()
    tid_a = next(t.id for t in tasks if t.title == "Task A")
    tid_b = next(t.id for t in tasks if t.title == "Task B")
    tasks = add_tag(tasks, tid_a, "@home")
    tasks = add_tag(tasks, tid_b, "@home")
    tasks = add_tag(tasks, tid_a, "@work")
    result = all_tags(tasks)
    assert ("@home", 2) in result
    assert ("@work", 1) in result


def test_all_tags_excludes_logbook() -> None:
    from gtd_tui.gtd.operations import complete_task

    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    tasks = complete_task(tasks, tid)
    result = all_tags(tasks)
    # Task A is now in logbook — @home count should be 0
    assert all(tag != "@home" for tag, _ in result)


def test_tasks_with_tag_returns_matching() -> None:
    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    result = tasks_with_tag(tasks, "@home")
    assert len(result) == 1
    assert result[0].title == "Task A"


def test_tasks_with_tag_excludes_logbook() -> None:
    from gtd_tui.gtd.operations import complete_task

    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = add_tag(tasks, tid, "@home")
    tasks = complete_task(tasks, tid)
    result = tasks_with_tag(tasks, "@home")
    assert result == []


def test_tags_storage_round_trip(tmp_path) -> None:
    from gtd_tui.storage.file import load_tasks, save_data

    tasks = _tasks_ab()
    tid = next(t.id for t in tasks if t.title == "Task A")
    tasks = set_tags(tasks, tid, ["@home", "@work"])
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    task = next(t for t in loaded if t.id == tid)
    assert task.tags == ["@home", "@work"]


def test_tags_default_empty_for_old_tasks(tmp_path) -> None:
    import json

    from gtd_tui.storage.file import load_tasks

    data_file = tmp_path / "data.json"
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
    assert tasks[0].tags == []
