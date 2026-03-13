from pathlib import Path

from gtd_tui.gtd.operations import add_task, complete_task
from gtd_tui.storage.file import load_tasks, save_tasks


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
