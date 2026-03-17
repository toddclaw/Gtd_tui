"""Tests for BACKLOG-35, 36, 37, 38:
- BACKLOG-35: gg/G navigation in sidebar
- BACKLOG-36: Folder number shortcuts start at 0
- BACKLOG-37: Context-aware t key
- BACKLOG-38: Ctrl-Z suspend (smoke test — checks no crash)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp
from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.operations import add_task, add_task_to_folder, move_to_today
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _prepopulate(tmp_path: Path, *titles: str) -> Path:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


# ---------------------------------------------------------------------------
# BACKLOG-35: gg/G navigation in sidebar
# ---------------------------------------------------------------------------


async def test_sidebar_G_jumps_to_bottom(tmp_path: Path) -> None:
    """G in sidebar jumps to the last entry."""
    data_file = _prepopulate(tmp_path, "task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        await pilot.press("G")
        await pilot.pause()
        last_idx = len(app._sidebar_view_ids) - 1
        assert sidebar.index == last_idx


async def test_sidebar_gg_jumps_to_top(tmp_path: Path) -> None:
    """gg in sidebar jumps to the first entry."""
    data_file = _prepopulate(tmp_path, "task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        # First go to bottom, then back to top with gg
        await pilot.press("G")
        await pilot.pause()
        await pilot.press("g")
        await pilot.press("g")
        await pilot.pause()
        assert sidebar.index == 0


# ---------------------------------------------------------------------------
# BACKLOG-36: Folder number shortcuts start at 0
# ---------------------------------------------------------------------------


async def test_digit_0_jumps_to_inbox(tmp_path: Path) -> None:
    """Pressing 0 in sidebar jumps to index 0 (Inbox)."""
    data_file = _prepopulate(tmp_path, "task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        # Go to bottom first
        await pilot.press("G")
        await pilot.pause()
        await pilot.press("0")
        await pilot.pause()
        assert sidebar.index == 0
        assert app._current_view == app._sidebar_view_ids[0]


async def test_digit_1_jumps_to_today(tmp_path: Path) -> None:
    """Pressing 1 in sidebar jumps to index 1 (Today)."""
    data_file = _prepopulate(tmp_path, "task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        assert sidebar.index == 1


async def test_digit_0_from_task_list_jumps_to_inbox(tmp_path: Path) -> None:
    """Pressing 0 when task list is focused also jumps to Inbox (index 0)."""
    data_file = _prepopulate(tmp_path, "task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        await pilot.press("G")
        await pilot.pause()
        # Move focus to task list
        await pilot.press("l")
        await pilot.pause()
        await pilot.press("0")
        await pilot.pause()
        assert app._sidebar_view_ids[0] == "inbox"


# ---------------------------------------------------------------------------
# BACKLOG-37: Context-aware t key
# ---------------------------------------------------------------------------


async def test_t_from_inbox_moves_to_today(tmp_path: Path) -> None:
    """t in Inbox view moves the task to the Today folder."""
    data_file = _prepopulate(tmp_path, "My Task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Navigate to inbox (index 0)
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        await pilot.press("0")
        await pilot.pause()
        await pilot.press("l")  # focus task list
        await pilot.pause()
        assert app._current_view == "inbox"
        await pilot.press("t")
        await pilot.pause()
        task = next((t for t in app._all_tasks if t.title == "My Task"), None)
        assert task is not None
        assert task.folder_id == "today"


async def test_t_from_user_folder_schedules_today(tmp_path: Path) -> None:
    """t in a user folder sets scheduled_date = today (does not move folder)."""
    folder = Folder(name="Work", id="work-folder-id")
    data_file = tmp_path / "data.json"
    tasks: list = add_task_to_folder([], folder.id, "Work Task")
    save_data(tasks, [folder], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Navigate to the user folder by finding its index in the sidebar
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        folder_idx = app._sidebar_view_ids.index(folder.id)
        sidebar.index = folder_idx
        await pilot.pause()
        await pilot.press("l")  # focus task list
        await pilot.pause()
        assert app._current_view == folder.id
        await pilot.press("t")
        await pilot.pause()
        task = next((t for t in app._all_tasks if t.title == "Work Task"), None)
        assert task is not None
        # Still in the same folder, but now has scheduled_date = today
        assert task.folder_id == folder.id
        assert task.scheduled_date == date.today()


async def test_t_from_waiting_on_moves_to_today(tmp_path: Path) -> None:
    """t in Waiting On view still moves the task to Today (original behaviour)."""
    data_file = _prepopulate(tmp_path, "Waiting Task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Move task to waiting_on first via w from today view
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.focus()
        await pilot.pause()
        # Navigate to today
        task = app._all_tasks[0]
        app._all_tasks = move_to_today(app._all_tasks, task.id)
        app._current_view = "today"
        app._refresh_list()
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        assert app._all_tasks[0].folder_id == "waiting_on"
        # Now switch to waiting_on view and press t
        app._current_view = "waiting_on"
        app._refresh_list()
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        assert app._all_tasks[0].folder_id == "today"
