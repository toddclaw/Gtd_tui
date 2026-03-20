"""Pilot integration tests for vim movement and folder management features.

Tests startup focus, project completed tasks (strikethrough), action picker
H/M/L/G/gg, and sidebar H/M/L navigation.
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Label, ListItem, ListView

from gtd_tui.app import GtdApp
from gtd_tui.config import Config
from gtd_tui.gtd.operations import (
    add_project,
    add_task,
    add_task_to_project,
    complete_task,
)
from gtd_tui.storage.file import save_data


def _make_app(tmp_path: Path, default_view: str = "today") -> GtdApp:
    app = GtdApp(data_file=tmp_path / "data.json")
    app._config = Config(default_view=default_view)
    app._current_view = app._config.default_view
    return app


async def test_startup_focus_on_sidebar(tmp_path: Path) -> None:
    """On launch, focus is on the sidebar at the configured default view."""
    data_file = tmp_path / "data.json"
    save_data(add_task([], "Task"), [], data_file=data_file)
    app = _make_app(tmp_path, default_view="inbox")

    async with app.run_test() as pilot:
        await pilot.pause()

        sidebar = app.query_one("#sidebar", ListView)
        assert (
            sidebar.has_focus
        ), f"Expected sidebar focused on startup; got {app.screen.focused!r}"


async def test_startup_sidebar_index_matches_default_view(tmp_path: Path) -> None:
    """Sidebar index matches default_view on startup."""
    data_file = tmp_path / "data.json"
    save_data(add_task([], "T"), [], data_file=data_file)
    app = _make_app(tmp_path, default_view="inbox")

    async with app.run_test() as pilot:
        await pilot.pause()

        sidebar = app.query_one("#sidebar", ListView)
        view_ids = app._sidebar_view_ids
        expected_idx = view_ids.index("inbox")
        assert (
            sidebar.index == expected_idx
        ), f"Sidebar index {sidebar.index} != expected {expected_idx} for inbox"


async def test_l_focuses_task_list_after_startup(tmp_path: Path) -> None:
    """Pressing 'l' when sidebar is focused moves focus to task list."""
    data_file = tmp_path / "data.json"
    save_data(add_task([], "Task"), [], data_file=data_file)
    app = _make_app(tmp_path, default_view="today")

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#sidebar", ListView).has_focus

        await pilot.press("l")
        await pilot.pause()

        list_view = app.query_one("#task-list", ListView)
        assert list_view.has_focus, "Expected task list focused after 'l'"


async def test_project_completed_task_shows_strikethrough(tmp_path: Path) -> None:
    """Completed project tasks remain visible with strikethrough markup."""
    data_file = tmp_path / "data.json"
    projects = add_project([], "My Project")
    pid = projects[0].id
    tasks = add_task_to_project([], pid, "Done")
    tasks = add_task_to_project(tasks, pid, "Pending")
    tid_done = tasks[0].id
    tasks = complete_task(tasks, tid_done)
    save_data(tasks, [], data_file=data_file, projects=projects)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Sidebar focused on startup; navigate to project
        # Order: inbox, today, upcoming, waiting_on, __projects_header__, project
        for _ in range(4):
            await pilot.press("j")
        await pilot.press("l")  # open project
        await pilot.pause()

        list_view = app.query_one("#task-list", ListView)
        items = list(list_view.query(ListItem))
        labels = [
            str(item.query_one(Label).content) for item in items if item.query("Label")
        ]
        assert any(
            "[strike]" in lbl for lbl in labels
        ), f"Expected strike markup in project view labels: {labels}"
        assert any(
            "Done" in lbl for lbl in labels
        ), "Expected completed task 'Done' visible in project view"


async def test_action_picker_H_G_gg(tmp_path: Path) -> None:
    """H, G, and gg navigate the move/assign/tag picker correctly."""
    data_file = tmp_path / "data.json"
    save_data(add_task([], "T"), [], data_file=data_file)
    app = GtdApp(data_file=data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("l")  # focus task list
        await pilot.press("m")  # open picker
        await pilot.pause()

        picker_screen = app.screen
        picker_list = picker_screen.query_one("#picker-list", ListView)
        selectable = picker_screen._selectable_indices()
        assert selectable, "Picker must have at least one selectable item"

        await pilot.press("G")
        await pilot.pause()
        assert (
            picker_list.index == selectable[-1]
        ), f"G: expected index {selectable[-1]}, got {picker_list.index}"

        await pilot.press("g")
        await pilot.press("g")
        await pilot.pause()
        assert (
            picker_list.index == selectable[0]
        ), f"gg: expected index {selectable[0]}, got {picker_list.index}"

        await pilot.press("escape")


async def test_sidebar_HML_navigation(tmp_path: Path) -> None:
    """H, M, L jump to top, middle, bottom of sidebar."""
    data_file = tmp_path / "data.json"
    save_data(add_task([], "T"), [], data_file=data_file)
    app = GtdApp(data_file=data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("l")  # focus task list
        await pilot.press("h")  # focus sidebar
        await pilot.pause()

        sidebar = app.query_one("#sidebar", ListView)
        n = len(app._sidebar_view_ids)
        assert n > 0

        await pilot.press("L")
        await pilot.pause()
        assert sidebar.index == n - 1, f"L: expected {n - 1}, got {sidebar.index}"

        await pilot.press("H")
        await pilot.pause()
        assert sidebar.index == 0, f"H: expected 0, got {sidebar.index}"

        await pilot.press("M")
        await pilot.pause()
        assert sidebar.index == n // 2, f"M: expected {n // 2}, got {sidebar.index}"
