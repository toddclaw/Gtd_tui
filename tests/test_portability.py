"""Tests for gtd_tui/portability.py — export and import helpers."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.task import Task
from gtd_tui.portability import (
    export_csv,
    export_json,
    export_md,
    export_txt,
    import_json,
    import_md,
)
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task(
    title: str,
    folder_id: str = "inbox",
    notes: str = "",
    completed: bool = False,
    scheduled: date | None = None,
    deadline: date | None = None,
    is_deleted: bool = False,
) -> Task:
    return Task(
        title=title,
        folder_id=folder_id,
        notes=notes,
        completed_at=datetime(2024, 1, 1) if completed else None,
        scheduled_date=scheduled,
        deadline=deadline,
        is_deleted=is_deleted,
    )


def _make_folder(name: str) -> Folder:
    return Folder(name=name)


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------


def test_export_json_is_valid_json() -> None:
    tasks = [_make_task("Buy milk")]
    result = export_json(tasks, [])
    data = json.loads(result)
    assert isinstance(data, dict)


def test_export_json_contains_version() -> None:
    result = export_json([], [])
    data = json.loads(result)
    assert data["version"] == 1


def test_export_json_task_round_trip() -> None:
    t = _make_task("Buy milk", folder_id="inbox", notes="whole milk")
    result = export_json([t], [])
    data = json.loads(result)
    assert len(data["tasks"]) == 1
    exported = data["tasks"][0]
    assert exported["title"] == "Buy milk"
    assert exported["notes"] == "whole milk"
    assert exported["folder_id"] == "inbox"


def test_export_json_includes_all_tasks() -> None:
    tasks = [_make_task(f"Task {i}") for i in range(5)]
    result = export_json(tasks, [])
    data = json.loads(result)
    assert len(data["tasks"]) == 5


def test_export_json_omits_builtin_folders() -> None:
    user_folder = _make_folder("My Project")
    all_folders = [user_folder]
    # inbox is a builtin — not passed, but even if present in folders list it is excluded
    result = export_json([], all_folders)
    data = json.loads(result)
    exported_ids = {f["id"] for f in data["folders"]}
    assert user_folder.id in exported_ids


def test_export_json_does_not_include_builtin_folder_ids() -> None:
    from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder

    builtin_folders = [Folder(name=bid, id=bid) for bid in BUILTIN_FOLDER_IDS]
    result = export_json([], builtin_folders)
    data = json.loads(result)
    assert data["folders"] == []


def test_export_json_task_with_dates() -> None:
    t = _make_task(
        "Deadline task",
        scheduled=date(2024, 6, 1),
        deadline=date(2024, 6, 30),
    )
    result = export_json([t], [])
    data = json.loads(result)
    exported = data["tasks"][0]
    assert exported["scheduled_date"] == "2024-06-01"
    assert exported["deadline"] == "2024-06-30"


# ---------------------------------------------------------------------------
# export_txt
# ---------------------------------------------------------------------------


def test_export_txt_one_task_per_line() -> None:
    tasks = [_make_task("Task A"), _make_task("Task B")]
    result = export_txt(tasks, [])
    lines = result.strip().splitlines()
    assert len(lines) == 2


def test_export_txt_format() -> None:
    task = _make_task("Buy milk", folder_id="inbox")
    result = export_txt([task], [])
    assert "Inbox: Buy milk" in result


def test_export_txt_skips_deleted_tasks() -> None:
    tasks = [
        _make_task("Keep me"),
        _make_task("Delete me", is_deleted=True),
    ]
    result = export_txt(tasks, [])
    assert "Keep me" in result
    assert "Delete me" not in result


def test_export_txt_uses_user_folder_name() -> None:
    folder = _make_folder("Work Projects")
    task = _make_task("Write report", folder_id=folder.id)
    result = export_txt([task], [folder])
    assert "Work Projects: Write report" in result


def test_export_txt_empty_returns_empty_string() -> None:
    result = export_txt([], [])
    assert result == ""


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------


def test_export_csv_has_header_row() -> None:
    result = export_csv([], [])
    reader = csv.DictReader(io.StringIO(result))
    assert reader.fieldnames == [
        "folder",
        "title",
        "scheduled_date",
        "deadline",
        "notes",
    ]


def test_export_csv_task_row() -> None:
    task = _make_task(
        "Buy milk",
        folder_id="inbox",
        notes="whole milk",
        scheduled=date(2024, 3, 1),
        deadline=date(2024, 3, 5),
    )
    result = export_csv([task], [])
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["folder"] == "Inbox"
    assert rows[0]["title"] == "Buy milk"
    assert rows[0]["scheduled_date"] == "2024-03-01"
    assert rows[0]["deadline"] == "2024-03-05"
    assert rows[0]["notes"] == "whole milk"


def test_export_csv_skips_deleted_tasks() -> None:
    tasks = [_make_task("Keep"), _make_task("Gone", is_deleted=True)]
    result = export_csv(tasks, [])
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    titles = [r["title"] for r in rows]
    assert "Keep" in titles
    assert "Gone" not in titles


def test_export_csv_empty_dates_are_blank() -> None:
    task = _make_task("No dates")
    result = export_csv([task], [])
    reader = csv.DictReader(io.StringIO(result))
    row = next(reader)
    assert row["scheduled_date"] == ""
    assert row["deadline"] == ""


# ---------------------------------------------------------------------------
# export_md
# ---------------------------------------------------------------------------


def test_export_md_has_folder_heading() -> None:
    task = _make_task("Buy milk", folder_id="inbox")
    result = export_md([task], [])
    assert "## Inbox" in result


def test_export_md_has_task_bullet() -> None:
    task = _make_task("Buy milk", folder_id="inbox")
    result = export_md([task], [])
    assert "- [ ] Buy milk" in result


def test_export_md_completed_task_uses_checked_box() -> None:
    task = _make_task("Done task", completed=True)
    result = export_md([task], [])
    assert "- [x] Done task" in result


def test_export_md_skips_deleted_tasks() -> None:
    tasks = [_make_task("Keep"), _make_task("Gone", is_deleted=True)]
    result = export_md(tasks, [])
    assert "Keep" in result
    assert "Gone" not in result


def test_export_md_notes_are_indented() -> None:
    task = _make_task("Task", notes="A note here")
    result = export_md([task], [])
    assert "  A note here" in result


def test_export_md_multiple_folders() -> None:
    tasks = [
        _make_task("Inbox task", folder_id="inbox"),
        _make_task("Someday task", folder_id="someday"),
    ]
    result = export_md(tasks, [])
    assert "## Inbox" in result
    assert "## Someday" in result


# ---------------------------------------------------------------------------
# import_json
# ---------------------------------------------------------------------------


def test_import_json_adds_new_tasks(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    task = _make_task("New task")
    export_str = export_json([task], [])
    export_file = tmp_path / "export.json"
    export_file.write_text(export_str, encoding="utf-8")

    tasks_added, folders_added = import_json(export_file, data_file)
    assert tasks_added == 1
    assert folders_added == 0


def test_import_json_task_is_persisted(tmp_path: Path) -> None:
    from gtd_tui.storage.file import load_tasks

    data_file = tmp_path / "data.json"
    task = _make_task("Persisted task")
    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([task], []), encoding="utf-8")

    import_json(export_file, data_file)
    loaded = load_tasks(data_file)
    assert any(t.title == "Persisted task" for t in loaded)


def test_import_json_skips_duplicate_task_ids(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    task = _make_task("Existing task")
    save_data([task], [], data_file)

    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([task], []), encoding="utf-8")

    tasks_added, _ = import_json(export_file, data_file)
    assert tasks_added == 0


def test_import_json_adds_new_folders(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    folder = _make_folder("Work")
    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([], [folder]), encoding="utf-8")

    _, folders_added = import_json(export_file, data_file)
    assert folders_added == 1


def test_import_json_skips_duplicate_folder_ids(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    folder = _make_folder("Work")
    save_data([], [folder], data_file)

    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([], [folder]), encoding="utf-8")

    _, folders_added = import_json(export_file, data_file)
    assert folders_added == 0


def test_import_json_never_imports_builtin_folder_ids(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    # Craft a JSON payload that contains a built-in ID in the folders list
    payload = json.dumps(
        {
            "version": 1,
            "folders": [{"id": "inbox", "name": "Inbox", "position": 0}],
            "tasks": [],
        }
    )
    export_file = tmp_path / "export.json"
    export_file.write_text(payload, encoding="utf-8")

    _, folders_added = import_json(export_file, data_file)
    assert folders_added == 0


def test_import_json_missing_file_raises(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    with pytest.raises(FileNotFoundError):
        import_json(tmp_path / "nonexistent.json", data_file)


def test_import_json_merge_preserves_existing_tasks(tmp_path: Path) -> None:
    from gtd_tui.storage.file import load_tasks

    data_file = tmp_path / "data.json"
    existing = _make_task("Existing")
    save_data([existing], [], data_file)

    new_task = _make_task("Imported")
    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([new_task], []), encoding="utf-8")

    import_json(export_file, data_file)
    loaded = load_tasks(data_file)
    titles = {t.title for t in loaded}
    assert "Existing" in titles
    assert "Imported" in titles


# ---------------------------------------------------------------------------
# Round-trip: export_json → import_json
# ---------------------------------------------------------------------------


def test_json_round_trip_preserves_task_fields(tmp_path: Path) -> None:
    from gtd_tui.storage.file import load_tasks

    data_file = tmp_path / "data.json"
    task = _make_task(
        "Round-trip task",
        folder_id="someday",
        notes="Important note",
        scheduled=date(2025, 7, 4),
        deadline=date(2025, 12, 31),
    )

    export_file = tmp_path / "export.json"
    export_file.write_text(export_json([task], []), encoding="utf-8")
    import_json(export_file, data_file)

    loaded = load_tasks(data_file)
    assert len(loaded) == 1
    rt = loaded[0]
    assert rt.title == "Round-trip task"
    assert rt.folder_id == "someday"
    assert rt.notes == "Important note"
    assert rt.scheduled_date == date(2025, 7, 4)
    assert rt.deadline == date(2025, 12, 31)


# ---------------------------------------------------------------------------
# import_md
# ---------------------------------------------------------------------------


def test_import_md_basic() -> None:
    text = "- [ ] Task one\n- [ ] Task two"
    tasks = import_md(text)
    assert len(tasks) == 2
    assert tasks[0].title == "Task one"
    assert tasks[1].title == "Task two"
    assert all(t.folder_id == "inbox" for t in tasks)
    assert all(t.completed_at is None for t in tasks)


def test_import_md_completed() -> None:
    text = "- [x] Done task"
    tasks = import_md(text)
    assert len(tasks) == 1
    assert tasks[0].completed_at is not None


def test_import_md_completed_uppercase_x() -> None:
    text = "- [X] Done task uppercase"
    tasks = import_md(text)
    assert len(tasks) == 1
    assert tasks[0].completed_at is not None


def test_import_md_mixed() -> None:
    text = "- [ ] Active one\n- [x] Completed\n- [ ] Active two"
    tasks = import_md(text)
    assert len(tasks) == 3
    assert tasks[0].completed_at is None
    assert tasks[1].completed_at is not None
    assert tasks[2].completed_at is None


def test_import_md_ignores_non_checklist() -> None:
    text = "## Heading\n\n- [ ] Real task\n\nJust some text\n\n- [ ] Another task"
    tasks = import_md(text)
    assert len(tasks) == 2
    assert tasks[0].title == "Real task"
    assert tasks[1].title == "Another task"


def test_import_md_indented_notes_spaces() -> None:
    text = "- [ ] My task\n  This is a note\n  Second line"
    tasks = import_md(text)
    assert len(tasks) == 1
    assert "This is a note" in tasks[0].notes
    assert "Second line" in tasks[0].notes


def test_import_md_indented_notes_tab() -> None:
    text = "- [ ] My task\n\tTab-indented note"
    tasks = import_md(text)
    assert len(tasks) == 1
    assert "Tab-indented note" in tasks[0].notes


def test_import_md_target_folder() -> None:
    text = "- [ ] Task A\n- [ ] Task B"
    tasks = import_md(text, target_folder_id="today")
    assert all(t.folder_id == "today" for t in tasks)


def test_import_md_positions_are_sequential() -> None:
    text = "- [ ] First\n- [ ] Second\n- [ ] Third"
    tasks = import_md(text)
    assert [t.position for t in tasks] == [0, 1, 2]


def test_import_md_each_task_gets_unique_id() -> None:
    text = "- [ ] Task A\n- [ ] Task B"
    tasks = import_md(text)
    assert tasks[0].id != tasks[1].id


def test_import_md_empty_text_returns_empty_list() -> None:
    assert import_md("") == []


def test_import_md_only_headings_returns_empty_list() -> None:
    assert import_md("## Section\n\n### Sub\n") == []


def test_import_md_note_not_attached_across_blank_line() -> None:
    """A blank line between task and indented text should break note attachment."""
    text = "- [ ] Task\n\n  Not a note (blank line breaks context)"
    tasks = import_md(text)
    assert len(tasks) == 1
    # The indented line is separated by a blank non-indented line,
    # so the blank line resets current_task and the indented line is not a note.
    assert tasks[0].notes == ""


# ---------------------------------------------------------------------------
# import_md: folder heading parsing
# ---------------------------------------------------------------------------


def test_import_md_builtin_heading_assigns_correct_folder() -> None:
    """## Today header routes tasks to the 'today' folder."""
    text = "## Today\n\n- [ ] Buy milk\n- [ ] Call dentist\n"
    tasks = import_md(text)
    assert all(
        t.folder_id == "today" for t in tasks
    ), f"Expected folder_id='today', got: {[t.folder_id for t in tasks]}"


def test_import_md_multiple_headings_route_to_correct_folders() -> None:
    """Tasks under different headings land in the matching folder."""
    text = (
        "## Inbox\n\n- [ ] Inbox task\n\n"
        "## Today\n\n- [ ] Today task\n\n"
        "## Someday\n\n- [ ] Someday task\n"
    )
    tasks = import_md(text)
    assert len(tasks) == 3
    by_title = {t.title: t.folder_id for t in tasks}
    assert by_title["Inbox task"] == "inbox"
    assert by_title["Today task"] == "today"
    assert by_title["Someday task"] == "someday"


def test_import_md_user_folder_heading_matches_by_name() -> None:
    """Tasks under a user-folder heading are assigned to that folder's ID."""
    user_folder = _make_folder("Work")
    user_folder_with_id = user_folder.__class__(id="work-uuid", name="Work", position=0)
    text = "## Work\n\n- [ ] Work task\n"
    tasks = import_md(text, folders=[user_folder_with_id])
    assert tasks[0].folder_id == "work-uuid"


def test_import_md_unknown_heading_falls_back_to_target_folder() -> None:
    """An unrecognised heading falls back to target_folder_id."""
    text = "## UnknownFolder\n\n- [ ] Some task\n"
    tasks = import_md(text, target_folder_id="inbox")
    assert tasks[0].folder_id == "inbox"


def test_import_md_heading_case_insensitive() -> None:
    """Heading matching is case-insensitive (e.g. 'today' matches 'today')."""
    text = "## TODAY\n\n- [ ] Task\n"
    tasks = import_md(text)
    assert tasks[0].folder_id == "today"


def test_import_md_tasks_before_heading_use_target_folder() -> None:
    """Tasks before any heading use the target_folder_id fallback."""
    text = "- [ ] Pre-heading task\n\n## Today\n\n- [ ] After heading task\n"
    tasks = import_md(text, target_folder_id="inbox")
    assert tasks[0].folder_id == "inbox"  # before heading
    assert tasks[1].folder_id == "today"  # after ## Today


def test_import_md_heading_parsing_is_md_export_roundtrip() -> None:
    """export_md output can be imported back with folder headings preserved."""
    task_inbox = _make_task("Inbox item", folder_id="inbox")
    task_today = _make_task("Today item", folder_id="today")
    md = export_md([task_inbox, task_today], [])
    tasks = import_md(md)
    by_title = {t.title: t.folder_id for t in tasks}
    assert by_title["Inbox item"] == "inbox"
    assert by_title["Today item"] == "today"
