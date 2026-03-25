"""Tests for BACKLOG-78: Split view (task list + detail pane).

`\\` toggles a right-side detail pane alongside the task list.
The pane shows the selected task's key fields; `l`/Enter focuses it for notes
editing.  `h` or Esc from COMMAND mode saves notes and returns focus to the
task list.  Split ratio is configurable.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from textual.widgets import Label, ListView

from gtd_tui.app import GtdApp, TaskSplitPane
from gtd_tui.config import load_config
from gtd_tui.gtd.operations import add_task
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CFG_TASK_LIST_FOCUS = replace(load_config(), startup_focus_sidebar=False)


def _app(data_file: Path) -> GtdApp:
    """Create app with task list focused on startup (for tests)."""
    return GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)


def _prepopulate(tmp_path: Path, *titles: str) -> Path:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


# ---------------------------------------------------------------------------
# BACKLOG-78 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_split_pane_hidden_by_default(tmp_path: Path) -> None:
    """The split pane should not be visible when the app first opens."""
    data_file = _prepopulate(tmp_path, "Task one")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        assert pane.display is False, "Split pane should be hidden by default"


@pytest.mark.asyncio
async def test_backslash_toggles_split_pane_visible(tmp_path: Path) -> None:
    """Pressing \\ makes the split pane visible."""
    data_file = _prepopulate(tmp_path, "Task one")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        assert pane.display is True, "Split pane should be visible after pressing \\"


@pytest.mark.asyncio
async def test_backslash_twice_hides_split_pane(tmp_path: Path) -> None:
    """Pressing \\ twice hides the split pane again."""
    data_file = _prepopulate(tmp_path, "Task one")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        assert pane.display is False, "Split pane should be hidden after second \\"


@pytest.mark.asyncio
async def test_split_pane_shows_task_title(tmp_path: Path) -> None:
    """When split view is active, the pane shows the selected task's title."""
    data_file = _prepopulate(tmp_path, "My Important Task")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()

        title_label = app.query_one("#split-title", Label)
        # Label.content property returns the current markup/text content
        title_text = str(title_label.content)
        assert (
            "My Important Task" in title_text
        ), f"Split pane should show task title, got: {title_text!r}"


@pytest.mark.asyncio
async def test_l_focuses_split_pane(tmp_path: Path) -> None:
    """Pressing l when split view is active moves focus to the split pane."""
    data_file = _prepopulate(tmp_path, "Task one")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()

        # task list should have focus by default after opening split view
        list_view = app.query_one("#task-list", ListView)
        assert list_view.has_focus, "Task list should have focus initially"

        await pilot.press("l")
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        # Focus should be inside the pane (on a child widget)
        focused = app.focused
        assert focused is not None
        # The focused widget should be a descendant of the split pane
        assert focused is pane or focused in pane.query(
            "*"
        ), f"Focus should be in split pane, got: {focused}"


@pytest.mark.asyncio
async def test_h_returns_focus_to_task_list(tmp_path: Path) -> None:
    """Pressing h from the split pane returns focus to the task list."""
    data_file = _prepopulate(tmp_path, "Task one")
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()
        await pilot.press("l")  # focus split pane
        await pilot.pause()
        await pilot.press("h")  # return to task list
        await pilot.pause()

        list_view = app.query_one("#task-list", ListView)
        assert (
            list_view.has_focus
        ), "Task list should have focus after pressing h from split pane"


@pytest.mark.asyncio
async def test_notes_saved_on_cursor_change(tmp_path: Path) -> None:
    """Editing notes in the split pane and moving cursor (j) saves the notes.

    Task two is position 0 (first shown), Task one is position 1 (second shown).
    We edit the first visible task (Task two) and verify notes are persisted.
    """
    data_file = tmp_path / "data.json"
    # add_task always inserts at position 0, so "Task two" ends up first in the list.
    tasks = add_task([], "Task one")
    tasks = add_task(tasks, "Task two")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")  # open split view
        await pilot.pause()
        await pilot.press("l")  # focus split pane
        await pilot.pause()

        # Enter insert mode and type some notes
        await pilot.press("i")
        await pilot.pause()
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()

        # Press Escape to return to command mode in the pane — this saves notes
        await pilot.press("escape")
        await pilot.pause()

        # Press h to return to task list
        await pilot.press("h")
        await pilot.pause()

        # The first task shown (Task two, position 0) should now have notes saved.
        # Notes are saved on Esc (mode change) and again on h (ReturnFocus).
        first_shown = next(
            t
            for t in sorted(app._all_tasks, key=lambda t: t.position)
            if t.folder_id == "today"
        )
        assert (
            "hello" in first_shown.notes
        ), f"Notes should be saved after editing, got: {first_shown.notes!r} for '{first_shown.title}'"


# ---------------------------------------------------------------------------
# Regression tests: notes proxy focus after Esc in split pane
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_split_pane_proxy_focused_after_esc(tmp_path: Path) -> None:
    """After Esc from INSERT in split pane, proxy should hold focus.

    Bug: on_vim_input_mode_changed in TaskSplitPane was missing proxy.focus(),
    leaving focus on the now-hidden VimInput.  Subsequent 'i' presses had no
    effect because the key never reached the pane's on_key handler.
    """
    from gtd_tui.app import MarkdownNotesProxy
    from gtd_tui.widgets.vim_input import VimInput

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Some existing notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")  # open split view
        await pilot.pause()
        await pilot.press("l")  # focus split pane
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        proxy = pane.query_one("#split-notes-proxy", MarkdownNotesProxy)

        # Proxy should be visible (task has notes)
        assert proxy.display is True

        # Edit notes
        await pilot.press("i")
        await pilot.pause()

        vim_inp = pane.query_one("#split-notes-input", VimInput)
        assert vim_inp.display is True, "VimInput should show in INSERT mode"

        # Esc back to command/markdown view
        await pilot.press("escape")
        await pilot.pause()

        assert proxy.display is True, "Proxy should be visible after Esc"
        assert vim_inp.display is False, "VimInput should be hidden after Esc"

        # The proxy must hold focus — this is the regression
        focused = app.screen.focused
        assert focused is proxy, f"Proxy should have focus after Esc; got {focused!r}"


@pytest.mark.asyncio
async def test_split_pane_i_works_after_esc(tmp_path: Path) -> None:
    """Pressing 'i' after Esc in split pane should re-enter edit mode.

    This verifies the full user flow: edit → Esc → edit again.
    """
    from gtd_tui.app import MarkdownNotesProxy
    from gtd_tui.widgets.vim_input import VimInput

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Initial notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("backslash")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()

        pane = app.query_one("#split-detail-pane", TaskSplitPane)
        proxy = pane.query_one("#split-notes-proxy", MarkdownNotesProxy)
        vim_inp = pane.query_one("#split-notes-input", VimInput)

        # First edit cycle
        await pilot.press("i")
        await pilot.pause()
        assert vim_inp.display is True
        await pilot.press("escape")
        await pilot.pause()
        assert proxy.display is True

        # Second i press must work — VimInput must become visible again
        await pilot.press("i")
        await pilot.pause()
        assert (
            vim_inp.display is True
        ), "VimInput must reappear on second 'i' press after Esc"
        assert proxy.display is False
