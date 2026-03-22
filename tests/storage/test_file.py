from datetime import date
from pathlib import Path

import pytest

from gtd_tui.gtd.operations import (
    add_task,
    complete_task,
    create_folder,
    set_recur_rule,
    set_repeat_rule,
)
from gtd_tui.gtd.task import RecurRule, RepeatRule
from gtd_tui.storage.file import (
    load_folders,
    load_redo_stack,
    load_tasks,
    load_undo_stack,
    save_data,
    save_tasks,
)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Remember to breathe")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert len(loaded) == 1
    assert loaded[0].title == "Remember to breathe"
    assert loaded[0].notes == ""
    assert loaded[0].folder_id == "today"


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    data_file = tmp_path / "nonexistent.json"
    result = load_tasks(data_file=data_file)
    assert result == []


def test_load_corrupt_file_returns_empty(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    data_file.write_text("not valid json {{{{")
    result = load_tasks(data_file=data_file)
    assert result == []


def test_save_preserves_completed_tasks(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Finished thing")
    task_id = tasks[0].id
    tasks = complete_task(tasks, task_id)
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].folder_id == "logbook"
    assert loaded[0].completed_at is not None
    assert loaded[0].is_complete


def test_save_creates_file_with_restricted_permissions(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    save_tasks([], data_file=data_file)
    mode = oct(data_file.stat().st_mode)[-3:]
    assert mode == "600"


def test_no_temp_files_left_after_save(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Test task")
    save_tasks(tasks, data_file=data_file)
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0] == data_file


def test_save_and_load_preserves_notes(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="These are the notes")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].notes == "These are the notes"


def test_save_and_load_multiple_tasks(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task A")
    tasks = add_task(tasks, "Task B")
    tasks = add_task(tasks, "Task C")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert len(loaded) == 3
    titles = {t.title for t in loaded}
    assert titles == {"Task A", "Task B", "Task C"}


def test_save_preserves_position(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "First")
    tasks = add_task(tasks, "Second")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    positions = {t.title: t.position for t in loaded}
    assert positions["Second"] == 0
    assert positions["First"] == 1


# ---------------------------------------------------------------------------
# Folder persistence (BACKLOG-4)
# ---------------------------------------------------------------------------


def test_save_data_and_load_folders_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    folders = create_folder([], "Work", folder_id="f1")
    save_data([], folders, data_file=data_file)
    loaded = load_folders(data_file=data_file)
    assert len(loaded) == 1
    assert loaded[0].name == "Work"
    assert loaded[0].id == "f1"


def test_load_folders_missing_file_returns_empty(tmp_path: Path) -> None:
    data_file = tmp_path / "nonexistent.json"
    result = load_folders(data_file=data_file)
    assert result == []


def test_load_folders_corrupt_file_returns_empty(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    data_file.write_text("not valid json {{{{")
    result = load_folders(data_file=data_file)
    assert result == []


def test_save_data_preserves_tasks_and_folders(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "My task")
    folders = create_folder([], "Work", folder_id="f1")
    save_data(tasks, folders, data_file=data_file)
    loaded_tasks = load_tasks(data_file=data_file)
    loaded_folders = load_folders(data_file=data_file)
    assert len(loaded_tasks) == 1
    assert loaded_tasks[0].title == "My task"
    assert len(loaded_folders) == 1
    assert loaded_folders[0].name == "Work"


def test_save_tasks_preserves_existing_folders(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    # First save some folders
    folders = create_folder([], "Work", folder_id="f1")
    save_data([], folders, data_file=data_file)
    # Now save tasks without touching folders
    tasks = add_task([], "A task")
    save_tasks(tasks, data_file=data_file)
    # Folders should still be there
    loaded_folders = load_folders(data_file=data_file)
    assert len(loaded_folders) == 1
    assert loaded_folders[0].name == "Work"


def test_load_folders_file_without_folders_key_returns_empty(tmp_path: Path) -> None:
    # Old-format file with only tasks key
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Old task")
    save_tasks(tasks, data_file=data_file)
    # Manually strip the folders key to simulate old file
    import json

    with open(data_file) as f:
        raw = json.load(f)
    raw.pop("folders", None)
    with open(data_file, "w") as f:
        json.dump(raw, f)
    result = load_folders(data_file=data_file)
    assert result == []


def test_folder_position_persists(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    folders = create_folder([], "A", folder_id="f1")
    folders = create_folder(folders, "B", folder_id="f2")
    save_data([], folders, data_file=data_file)
    loaded = load_folders(data_file=data_file)
    by_id = {f.id: f for f in loaded}
    assert by_id["f1"].position == 0
    assert by_id["f2"].position == 1


def test_repeat_rule_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Weekly task")
    rule = RepeatRule(interval=7, unit="days", next_due=date(2026, 4, 1))
    tasks = set_repeat_rule(tasks, tasks[0].id, rule)
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].repeat_rule is not None
    assert loaded[0].repeat_rule.interval == 7
    assert loaded[0].repeat_rule.unit == "days"
    assert loaded[0].repeat_rule.next_due == date(2026, 4, 1)


def test_no_repeat_rule_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Plain task")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].repeat_rule is None


def test_recur_rule_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].recur_rule is not None
    assert loaded[0].recur_rule.interval == 1
    assert loaded[0].recur_rule.unit == "days"


def test_no_recur_rule_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Plain task")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].recur_rule is None


def test_deleted_task_round_trip(tmp_path: Path) -> None:
    from gtd_tui.gtd.operations import delete_task

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Gone task")
    tasks = delete_task(tasks, tasks[0].id)
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].is_deleted is True
    assert loaded[0].folder_id == "logbook"
    assert loaded[0].is_complete is False


def test_non_deleted_task_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Normal task")
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].is_deleted is False


def test_created_at_round_trips(tmp_path):
    """created_at is persisted and reloaded correctly."""
    from gtd_tui.gtd.operations import add_task

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Buy stamps")
    assert tasks[0].created_at is not None
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].created_at is not None
    assert loaded[0].created_at == tasks[0].created_at


def test_created_at_missing_defaults_to_none(tmp_path):
    """Old tasks without created_at load without error, defaulting to None."""
    import json

    data_file = tmp_path / "data.json"
    # Write a task dict that lacks created_at (simulates old data).
    payload = {
        "tasks": [
            {
                "id": "abc",
                "title": "Old task",
                "notes": "",
                "folder_id": "today",
                "position": 0,
                "completed_at": None,
                "scheduled_date": None,
                "repeat_rule": None,
                "recur_rule": None,
                "is_deleted": False,
            }
        ],
        "folders": [],
    }
    data_file.write_text(json.dumps(payload))
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].created_at is None


def test_deadline_round_trip(tmp_path: Path) -> None:
    from gtd_tui.gtd.operations import set_deadline

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Buy cake")
    tasks = set_deadline(tasks, tasks[0].id, date(2026, 12, 1))
    save_tasks(tasks, data_file=data_file)
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].deadline == date(2026, 12, 1)


def test_deadline_missing_defaults_to_none(tmp_path: Path) -> None:
    """Old tasks without a deadline key load without error."""
    import json

    data_file = tmp_path / "data.json"
    payload = {
        "tasks": [
            {
                "id": "abc",
                "title": "Old task",
                "notes": "",
                "folder_id": "today",
                "position": 0,
                "completed_at": None,
                "scheduled_date": None,
                "repeat_rule": None,
                "recur_rule": None,
                "is_deleted": False,
            }
        ],
        "folders": [],
    }
    data_file.write_text(json.dumps(payload))
    loaded = load_tasks(data_file=data_file)
    assert loaded[0].deadline is None


# ---------------------------------------------------------------------------
# Encrypted file I/O (BACKLOG-23)
# ---------------------------------------------------------------------------


def test_save_and_load_encrypted_round_trip(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Secret task")
    save_tasks(tasks, data_file=data_file, password="s3cr3t")
    loaded = load_tasks(data_file=data_file, password="s3cr3t")
    assert len(loaded) == 1
    assert loaded[0].title == "Secret task"


def test_encrypted_file_is_not_plaintext_json(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Secret task")
    save_tasks(tasks, data_file=data_file, password="s3cr3t")
    raw = data_file.read_bytes()
    assert b"Secret task" not in raw


def test_wrong_password_raises_on_load(tmp_path: Path) -> None:
    from gtd_tui.storage.crypto import DecryptionError

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Secret task")
    save_tasks(tasks, data_file=data_file, password="correct")
    with pytest.raises(DecryptionError):
        load_tasks(data_file=data_file, password="wrong")


def test_plaintext_file_loads_without_password(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Public task")
    save_tasks(tasks, data_file=data_file)  # no password
    loaded = load_tasks(data_file=data_file)  # no password
    assert loaded[0].title == "Public task"


def test_encrypted_file_permissions_are_600(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    save_tasks([], data_file=data_file, password="pw")
    mode = oct(data_file.stat().st_mode)[-3:]
    assert mode == "600"


# ---------------------------------------------------------------------------
# BACKLOG-41: undo/redo stack persistence
# ---------------------------------------------------------------------------


def test_undo_stack_round_trip(tmp_path: Path) -> None:
    """Undo stack saved with save_data is restored by load_undo_stack."""
    data_file = tmp_path / "data.json"
    tasks_a = add_task([], "State A")
    tasks_b = add_task([], "State B")
    undo_stack = [(tasks_a, [], [], [])]
    save_data(tasks_b, [], data_file=data_file, undo_stack=undo_stack)
    loaded = load_undo_stack(data_file=data_file)
    assert len(loaded) == 1
    assert loaded[0][0][0].title == "State A"


def test_redo_stack_round_trip(tmp_path: Path) -> None:
    """Redo stack saved with save_data is restored by load_redo_stack."""
    data_file = tmp_path / "data.json"
    tasks_a = add_task([], "Redo State")
    redo_stack = [(tasks_a, [], [], [])]
    save_data([], [], data_file=data_file, redo_stack=redo_stack)
    loaded = load_redo_stack(data_file=data_file)
    assert len(loaded) == 1
    assert loaded[0][0][0].title == "Redo State"


def test_undo_stack_capped_at_20(tmp_path: Path) -> None:
    """load_undo_stack only returns the last 20 entries when more were saved."""
    data_file = tmp_path / "data.json"
    # Build 25 snapshots
    stack = [(add_task([], f"State {i}"), [], [], []) for i in range(25)]
    save_data([], [], data_file=data_file, undo_stack=stack)
    loaded = load_undo_stack(data_file=data_file)
    assert len(loaded) == 20
    # Should be the last 20 (indices 5-24)
    assert loaded[0][0][0].title == "State 5"
    assert loaded[-1][0][0].title == "State 24"


def test_load_undo_stack_missing_file_returns_empty(tmp_path: Path) -> None:
    """load_undo_stack returns [] when the file does not exist."""
    result = load_undo_stack(data_file=tmp_path / "nonexistent.json")
    assert result == []


def test_load_undo_stack_legacy_file_returns_empty(tmp_path: Path) -> None:
    """Files without an undo_stack key load cleanly with an empty stack."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Old task")
    # Save without undo_stack (legacy format)
    save_data(tasks, [], data_file=data_file)
    assert load_undo_stack(data_file=data_file) == []


def test_undo_stack_persists_through_encrypted_file(tmp_path: Path) -> None:
    """Undo stack is stored inside an encrypted file and can be retrieved."""
    data_file = tmp_path / "data.json"
    tasks_a = add_task([], "Encrypted undo state")
    undo_stack = [(tasks_a, [], [], [])]
    save_data([], [], data_file=data_file, password="pw", undo_stack=undo_stack)
    loaded = load_undo_stack(data_file=data_file, password="pw")
    assert len(loaded) == 1
    assert loaded[0][0][0].title == "Encrypted undo state"
