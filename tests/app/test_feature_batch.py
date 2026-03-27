"""Tests for the feature batch:
- Feature 2: Timeout (config integration)
- Feature 4: "Also Due" shows full folder name [Waiting On] not [W]
- Feature 6: Reference folder in sidebar and rendering
- Feature 7: Created date with hours and seconds
- Feature 8: 'w' key works from inbox and user-defined folders
- Feature 10: CalendarScreen smoke test
"""

from __future__ import annotations

import re
import time
from datetime import date, timedelta
from pathlib import Path

from textual.app import App
from textual.widgets import Label, ListView

from gtd_tui.app import CalendarScreen, GtdApp
from gtd_tui.config import Config
from gtd_tui.gtd.folder import REFERENCE_FOLDER_ID, Folder
from gtd_tui.gtd.operations import (
    add_task,
    add_task_to_folder,
    add_waiting_on_task,
    complete_task,
    schedule_task,
)
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _save_tasks(
    tmp_path: Path, tasks: list[Task], folders: list[Folder] | None = None
) -> Path:
    data_file = tmp_path / "data.json"
    save_data(tasks, folders or [], data_file)
    return data_file


# ---------------------------------------------------------------------------
# Feature 2: Config integration in GtdApp
# ---------------------------------------------------------------------------


async def test_app_loads_config_on_init(tmp_path: Path) -> None:
    """GtdApp initialises with a Config object."""
    app = _make_app(tmp_path)
    async with app.run_test():
        assert isinstance(app._config, Config)


async def test_app_tracks_last_activity(tmp_path: Path) -> None:
    """_last_activity is a float set during init."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        before = time.monotonic()
        await pilot.press("j")  # any key should update _last_activity
        assert app._last_activity >= before


async def test_check_timeout_noop_when_disabled(tmp_path: Path) -> None:
    """_check_timeout does nothing when timeout_enabled is False."""
    app = _make_app(tmp_path)
    app._config = Config(timeout_minutes=30, timeout_enabled=False)
    app._last_activity = time.monotonic() - 9999  # simulate long idle
    async with app.run_test():
        # Should not exit — calling _check_timeout manually verifies no crash
        app._check_timeout()
        assert app.is_running  # still running


async def test_check_timeout_exits_when_idle_enough(tmp_path: Path) -> None:
    """_check_timeout calls self.exit() when idle >= limit."""
    app = _make_app(tmp_path)
    app._config = Config(timeout_minutes=1, timeout_enabled=True)
    exited = []

    def _mock_exit(*args, **kwargs):  # type: ignore[override]
        exited.append(True)

    app.exit = _mock_exit  # type: ignore[method-assign]
    app._last_activity = time.monotonic() - 9999  # simulate 2.7h idle
    async with app.run_test():
        app._check_timeout()
    assert exited


# ---------------------------------------------------------------------------
# Feature 4: "Also Due" shows full folder name
# ---------------------------------------------------------------------------


async def test_also_due_waiting_on_shows_waiting_on_label(tmp_path: Path) -> None:
    """In Today view, Waiting On tasks in Also Due show [Waiting On] not [W]."""
    from dataclasses import replace

    from gtd_tui.config import load_config
    from gtd_tui.i18n import t

    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "WO Task")
    # Schedule it for today so it surfaces in Today view
    today = date.today()
    tasks = schedule_task(tasks, tasks[-1].id, today)

    data_file = _save_tasks(tmp_path, tasks)
    # Pin English so the assertion is language-independent (conftest resets language)
    cfg = replace(load_config(), language="en")
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        # At least one label should contain the translated "Waiting On"
        waiting_on_label = t("waiting_on")
        assert any(
            waiting_on_label in lbl for lbl in labels
        ), f"Expected '{waiting_on_label}' in labels: {labels}"
        # None should contain the old "[W] " prefix
        assert not any(
            lbl.strip().startswith("[W]") for lbl in labels
        ), f"Unexpected '[W]' prefix in labels: {labels}"


# ---------------------------------------------------------------------------
# Feature 6: Reference folder
# ---------------------------------------------------------------------------


async def test_reference_folder_appears_in_sidebar(tmp_path: Path) -> None:
    """Reference folder is visible in the sidebar."""
    from gtd_tui.i18n import t

    app = _make_app(tmp_path)
    async with app.run_test():
        sidebar = app.query_one("#sidebar", ListView)
        items = list(sidebar.query(Label))
        labels = [str(item.content) for item in items]
        ref_label = t("reference")
        assert any(
            ref_label in lbl for lbl in labels
        ), f"'{ref_label}' not found in sidebar: {labels}"


async def test_reference_view_renders(tmp_path: Path) -> None:
    """Navigating to Reference view renders the header correctly."""
    from gtd_tui.i18n import t

    tasks: list[Task] = []
    tasks = add_task_to_folder(tasks, REFERENCE_FOLDER_ID, "Ref item 1")
    data_file = _save_tasks(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test():
        app._current_view = REFERENCE_FOLDER_ID
        app._refresh_list()
        header = app.query_one("#header", Label)
        assert t("reference") in str(header.content)


async def test_reference_sidebar_shows_count(tmp_path: Path) -> None:
    """Sidebar shows correct count for Reference folder."""
    from gtd_tui.i18n import t

    tasks: list[Task] = []
    tasks = add_task_to_folder(tasks, REFERENCE_FOLDER_ID, "Ref A")
    tasks = add_task_to_folder(tasks, REFERENCE_FOLDER_ID, "Ref B")
    data_file = _save_tasks(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    # Use all-default counts so the test is independent of the real config file.
    app._config = Config()
    async with app.run_test():
        sidebar = app.query_one("#sidebar", ListView)
        items = list(sidebar.query(Label))
        labels = [str(item.content) for item in items]
        ref_label = t("reference")
        assert any(
            f"{ref_label} (2)" in lbl for lbl in labels
        ), f"'{ref_label} (2)' not found in: {labels}"


# ---------------------------------------------------------------------------
# Feature 7: Created date with hours and seconds
# ---------------------------------------------------------------------------


async def test_logbook_shows_created_datetime(tmp_path: Path) -> None:
    """Logbook entries display created_at with time (HH:MM:SS)."""
    tasks: list[Task] = []
    tasks = add_task(tasks, "Complete me")
    tasks = complete_task(tasks, tasks[0].id)
    data_file = _save_tasks(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "logbook"
        app._refresh_list()
        await pilot.pause()
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        # Should contain something matching HH:MM:SS pattern
        assert any(
            re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", lbl) for lbl in labels
        ), f"No datetime pattern in logbook labels: {labels}"


# ---------------------------------------------------------------------------
# Feature 8: 'w' key from inbox and user folders
# ---------------------------------------------------------------------------


async def test_w_key_from_inbox_moves_to_waiting_on(tmp_path: Path) -> None:
    """'w' key in Inbox view moves the task to Waiting On."""
    tasks: list[Task] = []
    tasks = add_task_to_folder(tasks, "inbox", "Inbox task")
    data_file = _save_tasks(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        # Ensure task list has focus
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        wo_tasks = [t for t in app._all_tasks if t.folder_id == "waiting_on"]
        assert len(wo_tasks) == 1
        assert wo_tasks[0].title == "Inbox task"


async def test_w_key_from_user_folder_moves_to_waiting_on(tmp_path: Path) -> None:
    """'w' key in a user-defined folder moves the task to Waiting On."""
    folders = [Folder(name="Work", id="work-folder-id", position=0)]
    tasks: list[Task] = []
    tasks = add_task_to_folder(tasks, "work-folder-id", "Work task")
    data_file = _save_tasks(tmp_path, tasks, folders)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "work-folder-id"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        wo_tasks = [t for t in app._all_tasks if t.folder_id == "waiting_on"]
        assert len(wo_tasks) == 1
        assert wo_tasks[0].title == "Work task"


async def test_w_key_reference_folder_does_not_move(tmp_path: Path) -> None:
    """'w' key in Reference folder is a no-op (reference items don't get dates)."""
    tasks: list[Task] = []
    tasks = add_task_to_folder(tasks, REFERENCE_FOLDER_ID, "Ref task")
    data_file = _save_tasks(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = REFERENCE_FOLDER_ID
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        ref_tasks = [t for t in app._all_tasks if t.folder_id == REFERENCE_FOLDER_ID]
        assert len(ref_tasks) == 1  # unchanged


# ---------------------------------------------------------------------------
# Feature 10: CalendarScreen smoke test (wrapped in a host App)
# ---------------------------------------------------------------------------


class _CalApp(App["date | None"]):
    """Minimal host app that immediately pushes a CalendarScreen."""

    def __init__(self, initial: date | None = None) -> None:
        super().__init__()
        self._initial = initial
        self.calendar_result: "date | None" = None

    def on_mount(self) -> None:
        def _cb(result: "date | None") -> None:
            self.calendar_result = result
            self.exit(result)

        self.push_screen(CalendarScreen(initial=self._initial), _cb)


async def test_calendar_screen_mounts() -> None:
    """CalendarScreen opens and renders without crashing."""
    initial_date = date(2026, 3, 18)
    async with _CalApp(initial=initial_date).run_test() as pilot:
        cal_screen = pilot.app.screen
        # The screen should have rendered a grid
        grid = cal_screen.query_one("#cal-grid")
        assert grid is not None
        # Navigate right one day
        await pilot.press("l")
        # Navigate down one week
        await pilot.press("j")
        # Go back to previous month
        await pilot.press("H")
        # Confirm — exits the screen
        await pilot.press("enter")


async def test_calendar_screen_navigation_updates_selected() -> None:
    """Navigation keys update _selected on the CalendarScreen."""
    initial = date(2026, 5, 10)
    async with _CalApp(initial=initial).run_test() as pilot:
        cal_screen = pilot.app.screen
        assert isinstance(cal_screen, CalendarScreen)
        # Navigate right one day
        await pilot.press("l")
        assert cal_screen._selected == initial + timedelta(days=1)
        # Navigate back
        await pilot.press("h")
        assert cal_screen._selected == initial


async def test_calendar_screen_confirm_returns_selected_date() -> None:
    """Pressing Enter confirms and returns the selected date."""
    initial = date(2026, 5, 10)
    async with _CalApp(initial=initial).run_test() as pilot:
        cal_screen = pilot.app.screen
        assert isinstance(cal_screen, CalendarScreen)
        await pilot.press("l")  # advance one day
        await pilot.press("enter")
        assert pilot.app.calendar_result == initial + timedelta(days=1)
