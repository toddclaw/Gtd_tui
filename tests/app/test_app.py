"""TUI integration tests for GtdApp.

Uses Textual's headless `run_test()` / Pilot API to drive the app through key
events and inspect the resulting DOM and app state.  No real terminal or
subprocess is needed.  Each test uses a `tmp_path`-backed data file so the
user's real data is never touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gtd_tui.app import GtdApp, SearchScreen, TaskDetailScreen
from gtd_tui.gtd.operations import add_task
from gtd_tui.storage.file import save_data
from textual.widgets import Label, ListView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _prepopulate(tmp_path: Path, *titles: str) -> Path:
    """Write tasks to a data file and return the path."""
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


# ---------------------------------------------------------------------------
# Launch / initial state
# ---------------------------------------------------------------------------


async def test_launch_shows_today_header(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        header = app.query_one("#header", Label)
        assert "Today" in str(header.content)


async def test_launch_shows_empty_hint_with_no_tasks(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        hint = app.query_one("#empty-hint", Label)
        assert "hidden" not in hint.classes


async def test_launch_loads_existing_tasks(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Buy milk", "Call dentist")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app._all_tasks) == 2


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------


async def test_press_o_enters_insert_mode(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert app._mode == "INSERT"
        assert app._input_stage == "title"


async def test_add_task_appears_in_task_list(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        # Type "Eat" one character at a time
        await pilot.press("E", "a", "t")
        await pilot.press("enter")   # confirm title, advance to notes
        await pilot.pause()
        await pilot.press("enter")   # skip notes, save task
        await pilot.pause()
        today_tasks = [t for t in app._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Eat" for t in today_tasks)


async def test_add_task_saves_to_data_file(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("R", "u", "n")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    # File must exist and contain the task
    assert data_file.exists()
    from gtd_tui.storage.file import load_tasks
    loaded = load_tasks(data_file)
    assert any(t.title == "Run" for t in loaded)


async def test_press_escape_cancels_task_creation(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        # First Esc: INSERT → COMMAND mode inside VimInput (stays in creation).
        await pilot.press("escape")
        await pilot.pause()
        # Second Esc: COMMAND mode bubbles to GtdApp → cancels the whole creation.
        await pilot.press("escape")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert len(app._all_tasks) == 0


# ---------------------------------------------------------------------------
# Task completion
# ---------------------------------------------------------------------------


async def test_x_completes_selected_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        completed = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(completed) == 1
        assert completed[0].title == "Finish report"


async def test_completing_task_removes_it_from_today(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert len(today) == 0


# ---------------------------------------------------------------------------
# Task deletion
# ---------------------------------------------------------------------------


async def test_d_deletes_selected_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(logbook) == 1
        assert logbook[0].title == "Finish report"
        assert logbook[0].is_deleted is True


async def test_deleted_task_not_marked_complete(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert logbook[0].is_complete is False


async def test_deleting_task_removes_it_from_today(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert len(today) == 0


async def test_deleted_task_persists_to_data_file(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
    from gtd_tui.storage.file import load_tasks
    loaded = load_tasks(data_file)
    assert loaded[0].is_deleted is True
    assert loaded[0].folder_id == "logbook"


# ---------------------------------------------------------------------------
# Task detail modal (BACKLOG-11)
# ---------------------------------------------------------------------------


async def test_enter_opens_task_detail_screen(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Plan sprint")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)


async def test_escape_closes_task_detail_screen(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Plan sprint")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)


async def test_edit_task_title_and_notes(tmp_path: Path) -> None:
    """Open the detail view for 'foo', extend the title to 'foo bar',
    advance to notes, add 'bar', then Esc to save.  Verify both fields persist.

    Title VimInput opens in COMMAND mode (editing existing task).
    'A' enters INSERT at end; type ' bar'; Esc → COMMAND; Enter → submit/advance.
    Notes VimInput also in COMMAND mode; 'i' → INSERT; type 'bar'; Esc → COMMAND.
    Second Esc from notes COMMAND mode bubbles to TaskDetailScreen → save+close.
    """
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open detail view — title VimInput pre-filled with "foo", COMMAND mode
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # 'A' → insert mode at end of "foo", then type " bar"
        await pilot.press("A")
        await pilot.press("space", "b", "a", "r")
        # Esc → back to COMMAND mode (stays in modal)
        await pilot.press("escape")
        await pilot.pause()
        # Enter in COMMAND mode submits VimInput → focus advances to notes
        await pilot.press("enter")
        await pilot.pause()

        # Notes VimInput in COMMAND mode (empty). 'i' → INSERT; type "bar"
        await pilot.press("i")
        await pilot.press("b", "a", "r")
        # Esc → COMMAND mode
        await pilot.press("escape")
        await pilot.pause()
        # Esc in COMMAND mode bubbles to TaskDetailScreen → save and close
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        # Verify the task was updated in memory and persisted
        task = next(t for t in app._all_tasks if t.folder_id != "logbook")
        assert task.title == "foo bar"
        assert task.notes == "bar"

        from gtd_tui.storage.file import load_tasks
        saved = load_tasks(data_file)
        saved_task = next(t for t in saved if t.folder_id != "logbook")
        assert saved_task.title == "foo bar"
        assert saved_task.notes == "bar"


async def test_set_repeat_rule_moves_task_to_upcoming(tmp_path: Path) -> None:
    """Open the detail view for 'foo', navigate to the Repeat field, enter '7 days',
    save, then switch to the Upcoming view and verify the task appears there."""
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open detail view — title input focused
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Advance past title → notes → repeat
        await pilot.press("enter")   # title → notes
        await pilot.pause()
        await pilot.press("enter")   # notes → repeat
        await pilot.pause()

        # Type the repeat interval in the Repeat field
        await pilot.press("7", " ", "d", "a", "y", "s")

        # Advance past repeat → recur, then Escape to save and close
        await pilot.press("enter")   # repeat → recur
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        # The task must still be in Today (it stays actionable)
        from gtd_tui.gtd.operations import today_tasks, upcoming_tasks
        today = today_tasks(app._all_tasks)
        assert any(t.title == "foo" for t in today), "task should remain in Today"

        # AND it must appear in Upcoming (previewing the next_due date)
        upcoming = upcoming_tasks(app._all_tasks)
        assert any(t.title == "foo" for t in upcoming), "task should appear in Upcoming"


# ---------------------------------------------------------------------------
# Search modal (BACKLOG-8)
# ---------------------------------------------------------------------------


async def test_slash_opens_search_screen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)


async def test_escape_closes_search_screen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SearchScreen)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------


async def test_h_focuses_sidebar(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        assert sidebar.has_focus


async def test_l_from_sidebar_focuses_task_list(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")   # move to sidebar
        await pilot.pause()
        await pilot.press("l")   # move back to task list
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        assert task_list.has_focus


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------


async def test_undo_restores_completed_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Write tests")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")     # complete the task
        await pilot.pause()
        await pilot.press("u")     # undo
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Write tests" for t in today)


async def test_undo_with_nothing_to_undo_shows_message(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        status = app.query_one("#status", Label)
        assert "nothing to undo" in str(status.content)


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


async def test_tasks_persist_across_app_restarts(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"

    # First session: add a task
    app1 = GtdApp(data_file=data_file)
    async with app1.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("M", "e", "d", "i", "t", "a", "t", "e")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

    # Second session: load the same data file and verify the task is there
    app2 = GtdApp(data_file=data_file)
    async with app2.run_test() as pilot:
        await pilot.pause()
        today = [t for t in app2._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Meditate" for t in today)
