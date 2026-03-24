"""Integration tests for BACKLOG-54: Snooze / Defer task.

The 'z' key opens a SnoozePickerScreen; selecting an option sets snoozed_until
on the task and hides it from smart views (Today, Upcoming, Anytime).
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp, SnoozePickerScreen
from gtd_tui.gtd.operations import add_task
from gtd_tui.storage.file import save_data
from tests.cfg import CFG_TASK_LIST_FOCUS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepopulate(tmp_path: Path, *titles: str) -> Path:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_z_key_opens_snooze_picker(tmp_path: Path) -> None:
    """Pressing 'z' on a task opens the SnoozePickerScreen modal."""
    data_file = _prepopulate(tmp_path, "Task to snooze")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("z")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SnoozePickerScreen)


async def test_snooze_escape_cancels(tmp_path: Path) -> None:
    """Pressing Escape on the snooze picker closes it without snoozeing."""
    data_file = _prepopulate(tmp_path, "Task to not snooze")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_id = app._all_tasks[0].id
        await pilot.press("z")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SnoozePickerScreen)
        await pilot.press("escape")
        await pilot.pause()
        # Should return to main screen
        assert not isinstance(pilot.app.screen, SnoozePickerScreen)
        # Task should NOT be snoozed
        task = next(t for t in app._all_tasks if t.id == task_id)
        assert task.snoozed_until is None


async def test_snooze_picker_sets_snoozed_until(tmp_path: Path) -> None:
    """Selecting a snooze option sets snoozed_until on the task."""
    data_file = _prepopulate(tmp_path, "Task to snooze")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_id = app._all_tasks[0].id
        await pilot.press("z")
        await pilot.pause()
        assert isinstance(pilot.app.screen, SnoozePickerScreen)
        # Select the first option ("1 hour") by pressing Enter
        snooze_list = pilot.app.screen.query_one("#snooze-list", ListView)
        snooze_list.index = 0
        await pilot.press("enter")
        await pilot.pause()
        # Modal should be dismissed
        assert not isinstance(pilot.app.screen, SnoozePickerScreen)
        # Task should be snoozed
        task = next(t for t in app._all_tasks if t.id == task_id)
        assert task.snoozed_until is not None


async def test_z_key_no_task_selected_does_not_crash(tmp_path: Path) -> None:
    """Pressing 'z' with no tasks in the list does not crash."""
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("z")
        await pilot.pause()
        # Should not open picker when no task is selected
        assert not isinstance(pilot.app.screen, SnoozePickerScreen)
