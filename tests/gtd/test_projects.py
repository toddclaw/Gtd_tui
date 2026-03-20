"""Tests for BACKLOG-31: Projects."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime

from gtd_tui.gtd.operations import (
    add_project,
    add_task,
    add_task_to_project,
    assign_task_to_project,
    check_auto_complete_project,
    complete_project,
    complete_task,
    delete_project,
    move_project_down,
    move_project_up,
    project_progress,
    project_tasks,
    project_tasks_including_completed,
    rename_project,
    unlink_project_tasks,
)
from gtd_tui.gtd.project import Project


def test_add_project_creates_project() -> None:
    projects = add_project([], "Deploy v2")
    assert len(projects) == 1
    assert projects[0].title == "Deploy v2"
    assert projects[0].completed_at is None


def test_add_project_increments_position() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    assert projects[0].position < projects[1].position


def test_add_project_sets_created_at() -> None:
    projects = add_project([], "P1")
    assert projects[0].created_at is not None


def test_delete_project() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    projects = delete_project(projects, pid)
    assert projects == []


def test_delete_project_unknown_id_noop() -> None:
    projects = add_project([], "P1")
    result = delete_project(projects, "nonexistent")
    assert len(result) == 1


def test_rename_project() -> None:
    projects = add_project([], "Old")
    pid = projects[0].id
    projects = rename_project(projects, pid, "New")
    assert projects[0].title == "New"


def test_rename_project_unknown_id_noop() -> None:
    projects = add_project([], "P1")
    result = rename_project(projects, "nonexistent", "X")
    assert result[0].title == "P1"


def test_complete_project() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    projects = complete_project(projects, pid)
    assert projects[0].completed_at is not None
    assert projects[0].is_complete is True


def test_project_is_complete_false_by_default() -> None:
    p = Project(title="P1")
    assert p.is_complete is False


def test_project_tasks_returns_subtasks() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task([], "Other task")
    tasks = add_task_to_project(tasks, pid, "Sub-task 1")
    tasks = add_task_to_project(tasks, pid, "Sub-task 2")
    result = project_tasks(tasks, pid)
    assert len(result) == 2
    assert all(t.project_id == pid for t in result)


def test_project_tasks_excludes_logbook() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Sub-task")
    tid = tasks[0].id
    tasks = complete_task(tasks, tid)
    result = project_tasks(tasks, pid)
    assert result == []


def test_project_tasks_including_completed_empty() -> None:
    """Empty project returns no tasks."""
    projects = add_project([], "P1")
    pid = projects[0].id
    assert project_tasks_including_completed([], pid) == []
    assert project_tasks_including_completed(add_task([], "Other"), pid) == []


def test_project_tasks_including_completed_only_active() -> None:
    """Only active tasks: same as project_tasks, sorted by position."""
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "B")
    tasks = add_task_to_project(tasks, pid, "A")
    result = project_tasks_including_completed(tasks, pid)
    assert len(result) == 2
    assert [t.title for t in result] == ["B", "A"]  # by position
    assert all(t.folder_id != "logbook" for t in result)


def test_project_tasks_including_completed_only_completed() -> None:
    """Only completed tasks: returned sorted by completed_at ascending."""
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "First")
    tasks = add_task_to_project(tasks, pid, "Second")
    tid1, tid2 = tasks[0].id, tasks[1].id
    tasks = complete_task(tasks, tid1)
    tasks = complete_task(tasks, tid2)
    result = project_tasks_including_completed(tasks, pid)
    assert len(result) == 2
    assert all(t.folder_id == "logbook" for t in result)
    assert result[0].completed_at <= result[1].completed_at


def test_project_tasks_including_completed_mixed_order() -> None:
    """Active first (by position), then completed (by completed_at ascending)."""
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Active1")
    tasks = add_task_to_project(tasks, pid, "Active2")
    tasks = add_task_to_project(tasks, pid, "ToComplete")
    tid = tasks[2].id
    tasks = complete_task(tasks, tid)
    result = project_tasks_including_completed(tasks, pid)
    assert len(result) == 3
    assert result[0].title == "Active1"
    assert result[1].title == "Active2"
    assert result[2].title == "ToComplete"
    assert result[2].folder_id == "logbook"


def test_project_tasks_including_completed_excludes_deleted() -> None:
    """Deleted tasks are excluded."""
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Sub")
    tid = tasks[0].id
    tasks = complete_task(tasks, tid)
    tasks = [replace(t, is_deleted=True) if t.id == tid else t for t in tasks]
    result = project_tasks_including_completed(tasks, pid)
    assert result == []


def test_project_tasks_including_completed_excludes_other_projects() -> None:
    """Tasks from other projects are excluded."""
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid1, pid2 = projects[0].id, projects[1].id
    tasks = add_task_to_project([], pid1, "A")
    tasks = add_task_to_project(tasks, pid2, "B")
    result = project_tasks_including_completed(tasks, pid1)
    assert len(result) == 1
    assert result[0].title == "A"


def test_project_tasks_excludes_other_projects() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid1 = projects[0].id
    pid2 = projects[1].id
    tasks = add_task_to_project([], pid1, "A")
    tasks = add_task_to_project(tasks, pid2, "B")
    assert len(project_tasks(tasks, pid1)) == 1
    assert len(project_tasks(tasks, pid2)) == 1


def test_project_progress_counts_correctly() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "A")
    tasks = add_task_to_project(tasks, pid, "B")
    tasks = add_task_to_project(tasks, pid, "C")
    tid_a = next(t.id for t in tasks if t.title == "A")
    tasks = complete_task(tasks, tid_a)
    done, total = project_progress(tasks, pid)
    assert done == 1
    assert total == 3


def test_project_progress_empty_project() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    done, total = project_progress([], pid)
    assert done == 0
    assert total == 0


def test_auto_complete_project_when_all_done() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "A")
    tasks = add_task_to_project(tasks, pid, "B")
    for t in list(tasks):
        tasks = complete_task(tasks, t.id)
    projects = check_auto_complete_project(tasks, projects, pid)
    assert projects[0].is_complete is True


def test_auto_complete_not_triggered_when_partial() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "A")
    tasks = add_task_to_project(tasks, pid, "B")
    tid_a = next(t.id for t in tasks if t.title == "A")
    tasks = complete_task(tasks, tid_a)
    projects = check_auto_complete_project(tasks, projects, pid)
    assert projects[0].is_complete is False


def test_auto_complete_no_subtasks_does_not_complete() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    projects = check_auto_complete_project([], projects, pid)
    assert projects[0].is_complete is False


def test_assign_task_to_project() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task([], "My task")
    tid = tasks[0].id
    tasks = assign_task_to_project(tasks, tid, pid)
    assert tasks[0].project_id == pid


def test_assign_task_to_project_unassign() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Sub")
    tid = tasks[0].id
    tasks = assign_task_to_project(tasks, tid, None)
    assert tasks[0].project_id is None


def test_add_task_to_project_increments_position() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "A")
    tasks = add_task_to_project(tasks, pid, "B")
    sub = project_tasks(tasks, pid)
    assert sub[0].position < sub[1].position


def test_storage_round_trip(tmp_path) -> None:
    from gtd_tui.storage.file import load_projects, load_tasks, save_data

    projects = add_project([], "Deploy v2")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Write tests")
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file=data_file, projects=projects)
    loaded_projects = load_projects(data_file=data_file)
    loaded_tasks = load_tasks(data_file=data_file)
    assert len(loaded_projects) == 1
    assert loaded_projects[0].title == "Deploy v2"
    assert loaded_projects[0].id == pid
    assert loaded_tasks[0].project_id == pid


def test_storage_round_trip_preserves_deadline(tmp_path) -> None:
    from gtd_tui.storage.file import load_projects, save_data

    projects = add_project([], "P1", deadline=date(2026, 12, 31))
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, projects=projects)
    loaded = load_projects(data_file=data_file)
    assert loaded[0].deadline == date(2026, 12, 31)


def test_storage_round_trip_completed_project(tmp_path) -> None:
    from gtd_tui.storage.file import load_projects, save_data

    projects = add_project([], "P1")
    pid = projects[0].id
    projects = complete_project(projects, pid)
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, projects=projects)
    loaded = load_projects(data_file=data_file)
    assert loaded[0].is_complete is True


def test_project_id_default_none_for_old_tasks(tmp_path) -> None:
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
                "tags": [],
            }
        ],
        "folders": [],
    }
    data_file.write_text(json.dumps(raw))
    tasks = load_tasks(data_file=data_file)
    assert tasks[0].project_id is None


def test_load_projects_missing_file(tmp_path) -> None:
    from gtd_tui.storage.file import load_projects

    result = load_projects(data_file=tmp_path / "nonexistent.json")
    assert result == []


def test_load_projects_no_projects_key(tmp_path) -> None:
    from gtd_tui.storage.file import load_projects

    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({"tasks": [], "folders": []}))
    result = load_projects(data_file=data_file)
    assert result == []


def test_move_project_up_swaps_positions() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid2 = projects[1].id
    projects = move_project_up(projects, pid2)
    ordered = sorted(projects, key=lambda p: p.position)
    assert ordered[0].id == pid2


def test_move_project_down_swaps_positions() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid1 = projects[0].id
    projects = move_project_down(projects, pid1)
    ordered = sorted(projects, key=lambda p: p.position)
    assert ordered[0].title == "P2"
    assert ordered[1].title == "P1"


def test_move_project_up_at_top_is_noop() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid1 = projects[0].id
    original_pos = next(p.position for p in projects if p.id == pid1)
    projects = move_project_up(projects, pid1)
    new_pos = next(p.position for p in projects if p.id == pid1)
    assert new_pos == original_pos


def test_move_project_down_at_bottom_is_noop() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid2 = projects[1].id
    original_pos = next(p.position for p in projects if p.id == pid2)
    projects = move_project_down(projects, pid2)
    new_pos = next(p.position for p in projects if p.id == pid2)
    assert new_pos == original_pos


def test_unlink_project_tasks_clears_project_id() -> None:
    projects = add_project([], "P1")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Sub A")
    tasks = add_task_to_project(tasks, pid, "Sub B")
    tasks = unlink_project_tasks(tasks, pid)
    assert all(t.project_id is None for t in tasks)


def test_unlink_project_tasks_does_not_affect_other_projects() -> None:
    projects = add_project([], "P1")
    projects = add_project(projects, "P2")
    pid1 = projects[0].id
    pid2 = projects[1].id
    tasks = add_task_to_project([], pid1, "A")
    tasks = add_task_to_project(tasks, pid2, "B")
    tasks = unlink_project_tasks(tasks, pid1)
    task_b = next(t for t in tasks if t.title == "B")
    assert task_b.project_id == pid2
