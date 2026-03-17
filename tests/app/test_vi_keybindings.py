"""Tests for BACKLOG-26: missing vi keybindings.

Covers:
- Ctrl+d / Ctrl+u  half-page scroll in task list
- n / N            search match navigation
- Ctrl+c           cancel INSERT mode (alias for Escape)
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp
from gtd_tui.gtd.operations import add_task
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
# Ctrl+c cancels INSERT mode
# ---------------------------------------------------------------------------


async def test_ctrl_c_cancels_insert_mode(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert app._mode == "INSERT"
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app._mode == "NORMAL"


async def test_ctrl_c_does_not_save_partial_task(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("T", "a", "s", "k")
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert all(t.title != "Task" for t in app._all_tasks)


# ---------------------------------------------------------------------------
# Ctrl+d / Ctrl+u half-page scroll
# ---------------------------------------------------------------------------


async def test_ctrl_d_moves_cursor_down(tmp_path: Path) -> None:
    """Ctrl+d should move the cursor down from position 0."""
    titles = [f"Task {i}" for i in range(20)]
    data_file = _prepopulate(tmp_path, *titles)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 0
        await pilot.pause()
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert list_view.index is not None
        assert list_view.index > 0


async def test_ctrl_u_moves_cursor_up(tmp_path: Path) -> None:
    """Ctrl+u should move the cursor up from a non-zero position."""
    titles = [f"Task {i}" for i in range(20)]
    data_file = _prepopulate(tmp_path, *titles)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        list_view = app.query_one("#task-list", ListView)
        # Start at the bottom
        list_view.index = len(app._list_entries) - 1
        await pilot.pause()
        start_idx = list_view.index
        await pilot.press("ctrl+u")
        await pilot.pause()
        assert list_view.index is not None
        assert list_view.index < start_idx


async def test_ctrl_d_at_bottom_stays_at_bottom(tmp_path: Path) -> None:
    """Ctrl+d at the last item should not go out of bounds."""
    data_file = _prepopulate(tmp_path, "Only task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        list_view = app.query_one("#task-list", ListView)
        list_view.index = len(app._list_entries) - 1
        await pilot.pause()
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert list_view.index == len(app._list_entries) - 1


async def test_ctrl_u_at_top_stays_at_top(tmp_path: Path) -> None:
    """Ctrl+u at the first item should not go below 0."""
    data_file = _prepopulate(tmp_path, "Only task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 0
        await pilot.pause()
        await pilot.press("ctrl+u")
        await pilot.pause()
        assert list_view.index == 0


# ---------------------------------------------------------------------------
# n / N search match navigation
# ---------------------------------------------------------------------------


async def test_n_navigates_to_next_search_match(tmp_path: Path) -> None:
    """n should cycle through stored search matches."""
    data_file = _prepopulate(tmp_path, "Alpha task", "Beta task", "Alpha second")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Manually inject search state (simulates a prior / search for "Alpha")
        from gtd_tui.gtd.operations import search_tasks

        results = search_tasks(app._all_tasks, "Alpha")
        app._last_search_query = "Alpha"
        app._search_match_ids = [t.id for t, _ in results]
        app._search_match_idx = 0
        await pilot.press("n")
        await pilot.pause()
        # Index should have advanced by 1
        assert app._search_match_idx == 1


async def test_N_navigates_to_previous_search_match(tmp_path: Path) -> None:
    """N should cycle backwards through stored search matches."""
    data_file = _prepopulate(tmp_path, "Alpha task", "Beta task", "Alpha second")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        from gtd_tui.gtd.operations import search_tasks

        results = search_tasks(app._all_tasks, "Alpha")
        app._last_search_query = "Alpha"
        app._search_match_ids = [t.id for t, _ in results]
        app._search_match_idx = 1
        await pilot.press("N")
        await pilot.pause()
        assert app._search_match_idx == 0


async def test_n_wraps_around(tmp_path: Path) -> None:
    """n at the last match should wrap to the first."""
    data_file = _prepopulate(tmp_path, "Alpha task", "Alpha second")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        from gtd_tui.gtd.operations import search_tasks

        results = search_tasks(app._all_tasks, "Alpha")
        app._last_search_query = "Alpha"
        app._search_match_ids = [t.id for t, _ in results]
        app._search_match_idx = len(app._search_match_ids) - 1
        await pilot.press("n")
        await pilot.pause()
        assert app._search_match_idx == 0


async def test_n_is_noop_without_prior_search(tmp_path: Path) -> None:
    """n with no stored search state should not crash."""
    data_file = _prepopulate(tmp_path, "Task A")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # No search state set — press n should silently do nothing
        await pilot.press("n")
        await pilot.pause()
        assert app._mode == "NORMAL"
