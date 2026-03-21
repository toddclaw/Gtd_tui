"""Tests for BACKLOG-27: Inbox folder.

Covers:
- inbox_tasks() returns inbox tasks, not today tasks
- "inbox" in BUILTIN_FOLDER_IDS
- Inbox appears in sidebar
- Tasks can be created in Inbox
- Inbox tasks do not appear in Today
- i key navigates to Inbox from any view
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Label, ListView

from gtd_tui.app import GtdApp
from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS
from gtd_tui.gtd.operations import (
    add_task_to_folder,
    inbox_tasks,
    today_tasks,
)
from gtd_tui.storage.file import save_data
from tests.cfg import CFG_TASK_LIST_FOCUS

# ---------------------------------------------------------------------------
# Unit-level: inbox_tasks / BUILTIN_FOLDER_IDS
# ---------------------------------------------------------------------------


def test_inbox_in_builtin_folder_ids() -> None:
    assert "inbox" in BUILTIN_FOLDER_IDS


def test_inbox_tasks_returns_inbox_tasks() -> None:
    tasks = add_task_to_folder([], "inbox", "Inbox task")
    result = inbox_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Inbox task"


def test_inbox_tasks_sorted_by_position() -> None:
    tasks = add_task_to_folder([], "inbox", "A")
    tasks = add_task_to_folder(tasks, "inbox", "B")
    tasks = add_task_to_folder(tasks, "inbox", "C")
    result = inbox_tasks(tasks)
    positions = [t.position for t in result]
    assert positions == sorted(positions)


def test_inbox_tasks_not_in_today() -> None:
    """Inbox tasks must never surface in the Today smart view."""
    tasks = add_task_to_folder([], "inbox", "Inbox task")
    assert inbox_tasks(tasks)[0].title == "Inbox task"
    assert all(t.title != "Inbox task" for t in today_tasks(tasks))


def test_inbox_tasks_not_in_today_even_with_date() -> None:
    """Inbox tasks with a scheduled date must still stay out of Today."""
    from datetime import date, timedelta

    tasks = add_task_to_folder([], "inbox", "Past due inbox task")
    from gtd_tui.gtd.operations import schedule_task

    tasks = schedule_task(tasks, tasks[0].id, date.today() - timedelta(days=1))
    assert all(t.title != "Past due inbox task" for t in today_tasks(tasks))


# ---------------------------------------------------------------------------
# TUI-level: sidebar renders Inbox, i key jumps to Inbox
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json", config=CFG_TASK_LIST_FOCUS)


def _prepopulate_inbox(tmp_path: Path, *titles: str) -> Path:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task_to_folder(tasks, "inbox", title)
    save_data(tasks, [], data_file=data_file)
    return data_file


async def test_inbox_appears_in_sidebar(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        labels = [
            str(item.query_one(Label).render()) for item in sidebar.query("ListItem")
        ]
        assert any("Inbox" in lbl for lbl in labels)


async def test_inbox_is_first_sidebar_item(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        view_ids = app._sidebar_view_ids
        assert view_ids[0] == "inbox"


async def test_i_key_jumps_to_inbox(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Start in today view
        assert app._current_view == "today"
        await pilot.press("i")
        await pilot.pause()
        assert app._current_view == "inbox"


async def test_create_task_in_inbox(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Navigate to Inbox
        await pilot.press("i")
        await pilot.pause()
        assert app._current_view == "inbox"
        # Create a task
        await pilot.press("o")
        await pilot.pause()
        assert app._mode == "INSERT"
        await pilot.press("I", "n", "b", "o", "x", "T", "a", "s", "k")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        inbox = [t for t in app._all_tasks if t.folder_id == "inbox"]
        assert any(t.title == "InboxTask" for t in inbox)


async def test_inbox_tasks_not_shown_in_today_view(tmp_path: Path) -> None:
    data_file = _prepopulate_inbox(tmp_path, "Secret inbox task")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Verify in app state
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert all(t.title != "Secret inbox task" for t in today)
        # Verify rendering — task list in today view shows no inbox items
        assert app._current_view == "today"
        entries = [e for e in app._list_entries if e is not None]
        assert all(e.title != "Secret inbox task" for e in entries)
