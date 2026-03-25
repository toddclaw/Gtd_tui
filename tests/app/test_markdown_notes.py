"""Tests for BACKLOG-82: Markdown-rendered notes in detail view.

The TaskDetailScreen notes field shows rendered Markdown (via MarkdownNotesProxy)
when in COMMAND mode.  Pressing i/a/o switches to raw VimInput (INSERT mode).
Esc from INSERT returns to Markdown view.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gtd_tui.app import GtdApp, MarkdownNotesProxy, TaskDetailScreen
from gtd_tui.config import load_config
from gtd_tui.gtd.operations import add_task
from gtd_tui.storage.file import save_data
from gtd_tui.widgets.vim_input import VimInput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app(data_file: Path) -> GtdApp:
    """Create app with task list focused on startup (for tests)."""
    cfg = replace(load_config(), startup_focus_sidebar=False)
    return GtdApp(data_file=data_file, config=cfg)


# ---------------------------------------------------------------------------
# BACKLOG-82 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_markdown_notes_shown_for_task_with_notes(tmp_path: Path) -> None:
    """Open detail screen for a task with notes — proxy should be visible,
    VimInput should be hidden."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "My task", notes="## Some notes\nWith content")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        assert (
            proxy.display is True
        ), "MarkdownNotesProxy should be visible for tasks with notes"
        assert (
            vim_inp.display is False
        ), "VimInput should be hidden when proxy is visible"


@pytest.mark.asyncio
async def test_empty_notes_shows_vim_input_directly(tmp_path: Path) -> None:
    """Open detail screen for a task with empty notes — VimInput should be visible,
    proxy should be hidden."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Empty notes task")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        assert proxy.display is False, "Proxy should be hidden when task has no notes"
        assert (
            vim_inp.display is True
        ), "VimInput should be visible when task has no notes"


@pytest.mark.asyncio
async def test_pressing_i_on_proxy_switches_to_vim_input(tmp_path: Path) -> None:
    """When proxy is focused and i is pressed, VimInput becomes visible and
    proxy becomes hidden."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Some notes here")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        # Proxy is visible initially
        assert proxy.display is True

        # Focus the proxy then press i
        proxy.focus()
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()

        assert proxy.display is False, "Proxy should be hidden after pressing i"
        assert vim_inp.display is True, "VimInput should be visible after pressing i"
        assert screen.focused is vim_inp, "VimInput should have focus after pressing i"


@pytest.mark.asyncio
async def test_esc_from_insert_shows_markdown_again(tmp_path: Path) -> None:
    """After editing in VimInput (INSERT mode), pressing Esc returns to COMMAND mode
    and shows the Markdown proxy again."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Original notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        # Proxy starts visible
        assert proxy.display is True

        # Focus proxy and press i to switch to VimInput
        proxy.focus()
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()

        assert vim_inp.display is True
        assert proxy.display is False

        # VimInput is now in INSERT mode (set_mode called with "insert")
        # Type something
        await pilot.press("space", "e", "d", "i", "t", "e", "d")
        await pilot.pause()

        # Press Esc → VimInput goes to COMMAND mode → proxy should reappear
        await pilot.press("escape")
        await pilot.pause()

        assert proxy.display is True, "Proxy should reappear after Esc from INSERT mode"
        assert (
            vim_inp.display is False
        ), "VimInput should be hidden after Esc from INSERT mode"


@pytest.mark.asyncio
async def test_proxy_focused_after_esc_from_insert(tmp_path: Path) -> None:
    """After Esc from INSERT, the proxy should hold focus so 'i' works again."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Some notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)

        # Navigate to the proxy with j/k from title
        proxy.focus()
        await pilot.pause()

        # Switch to edit mode
        await pilot.press("i")
        await pilot.pause()

        # Esc back to command/markdown view
        await pilot.press("escape")
        await pilot.pause()

        # The proxy should now hold focus so the user can press i again
        assert (
            screen.focused is proxy
        ), "Proxy should have focus after Esc — otherwise 'i' to re-edit is broken"


@pytest.mark.asyncio
async def test_i_on_proxy_works_second_time(tmp_path: Path) -> None:
    """Pressing 'i' on the proxy, then Esc, then 'i' again must open edit mode each time."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Original notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        # First round: i → edit → Esc → back to proxy
        proxy.focus()
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()
        assert vim_inp.display is True, "VimInput must show on first i"
        await pilot.press("escape")
        await pilot.pause()
        assert proxy.display is True, "Proxy must show after first Esc"

        # Second round: i must open edit mode again
        await pilot.press("i")
        await pilot.pause()
        assert vim_inp.display is True, "VimInput must show on second i"
        assert proxy.display is False, "Proxy must be hidden on second i"


@pytest.mark.asyncio
async def test_j_navigation_skips_hidden_notes_vim_input(tmp_path: Path) -> None:
    """j/k from deadline field should land on the proxy (not the hidden VimInput)."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task with notes", notes="Some notes")
    save_data(tasks, [], data_file=data_file)
    app = _app(data_file)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, TaskDetailScreen)

        proxy = screen.query_one("#detail-notes-proxy", MarkdownNotesProxy)

        # Focus the deadline input, then press j — next focusable should be the proxy
        deadline_inp = screen.query_one("#detail-deadline-input", VimInput)
        deadline_inp.focus()
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()

        assert (
            screen.focused is proxy
        ), "j from deadline should land on the notes proxy, not the hidden VimInput"
