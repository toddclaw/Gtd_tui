"""Tests for the second feature batch:
- Feature: ? opens HelpScreen from sidebar focus
- Feature: 'r' key initiates task rename (INSERT mode, task_rename stage)
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp, HelpScreen
from gtd_tui.gtd.operations import add_task_to_folder
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _save_tasks_to(tmp_path: Path, tasks: list) -> Path:
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file)
    return data_file


# ---------------------------------------------------------------------------
# Help screen from sidebar
# ---------------------------------------------------------------------------


async def test_help_screen_from_sidebar(tmp_path: Path) -> None:
    """Pressing '?' when the sidebar is focused opens the HelpScreen."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Move focus to the sidebar using 'h'
        await pilot.press("h")
        await pilot.pause()
        # Press '?' to open the help screen
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)


async def test_help_screen_dismisses_on_q(tmp_path: Path) -> None:
    """Pressing 'q' dismisses the HelpScreen and returns to the main screen."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        await pilot.press("q")
        await pilot.pause()
        # After dismissal we should be back on the main app screen
        assert not isinstance(pilot.app.screen, HelpScreen)


# ---------------------------------------------------------------------------
# Rename task from task list ('r' key)
# ---------------------------------------------------------------------------


async def test_rename_task_from_list_enters_insert_mode(tmp_path: Path) -> None:
    """Pressing 'r' on a task in the task list enters INSERT mode at task_rename stage."""
    tasks = add_task_to_folder([], "inbox", "Original Title")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        # Give focus to the task list
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert app._mode == "INSERT"
        assert app._input_stage == "task_rename"


async def test_rename_task_from_list_sets_rename_task_id(tmp_path: Path) -> None:
    """After pressing 'r', _rename_task_id is set to the focused task's id."""
    tasks = add_task_to_folder([], "inbox", "Task to rename")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        # The rename target should be the id of the only task
        assert app._rename_task_id == tasks[0].id


async def test_rename_escape_returns_to_normal_mode(tmp_path: Path) -> None:
    """Pressing Escape during rename cancels and returns to NORMAL mode."""
    tasks = add_task_to_folder([], "inbox", "Cancel me")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert app._mode == "INSERT"
        await pilot.press("escape")
        await pilot.pause()
        assert app._mode == "NORMAL"
