"""Tests for BACKLOG-82: Markdown-rendered notes in detail view.

State machine for the notes field in TaskDetailScreen:
  Proxy (read / markdown)  → Enter          → VimInput COMMAND mode (raw text)
  Proxy (read / markdown)  → i/a/A/o/O      → VimInput INSERT mode  (shortcut)
  VimInput COMMAND mode    → i/a/A/o/O      → VimInput INSERT mode  (vim normal)
  VimInput INSERT mode     → Esc            → VimInput COMMAND mode (no auto-return)
  VimInput COMMAND mode    → Enter (bubble) → Proxy (renders markdown)
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
async def test_esc_from_insert_stays_in_command_mode(tmp_path: Path) -> None:
    """After editing in VimInput (INSERT mode), Esc returns to VimInput COMMAND mode —
    the proxy does NOT reappear until Enter is pressed in command mode."""
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

        # Focus proxy and press i to switch to VimInput INSERT mode
        proxy.focus()
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()

        assert vim_inp.display is True
        assert proxy.display is False

        # Type something then press Esc → VimInput COMMAND mode (proxy stays hidden)
        await pilot.press("space", "e", "d", "i", "t", "e", "d")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert (
            vim_inp.display is True
        ), "VimInput stays visible after Esc (command mode)"
        assert proxy.display is False, "Proxy stays hidden after Esc (not yet Enter)"
        assert (
            vim_inp._vim_mode == "command"
        ), "VimInput should be in command mode after Esc"

        # Press Enter in command mode → proxy reappears with rendered markdown
        await pilot.press("enter")
        await pilot.pause()

        assert proxy.display is True, "Proxy reappears after Enter in command mode"
        assert vim_inp.display is False, "VimInput hides after Enter in command mode"


@pytest.mark.asyncio
async def test_vim_input_focused_after_esc_from_insert(tmp_path: Path) -> None:
    """After Esc from INSERT, VimInput holds focus in command mode.
    The user presses Enter to return to the proxy, or i to re-enter INSERT."""
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
        vim_inp = screen.query_one("#detail-notes-input", VimInput)

        proxy.focus()
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()

        # Esc → VimInput COMMAND mode; VimInput keeps focus
        await pilot.press("escape")
        await pilot.pause()

        assert screen.focused is vim_inp, "VimInput should hold focus after Esc"
        assert vim_inp._vim_mode == "command"

        # From command mode, 'i' re-enters INSERT mode
        await pilot.press("i")
        await pilot.pause()
        assert vim_inp._vim_mode == "insert", "'i' in command mode should enter INSERT"


@pytest.mark.asyncio
async def test_enter_on_proxy_enter_in_command_mode_roundtrip(tmp_path: Path) -> None:
    """Enter on proxy → command mode; Enter in command mode → proxy (full roundtrip)."""
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

        # Enter on proxy → VimInput command mode
        proxy.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert vim_inp.display is True, "VimInput should show after Enter on proxy"
        assert proxy.display is False, "Proxy should hide after Enter on proxy"
        assert vim_inp._vim_mode == "command", "VimInput should be in command mode"

        # Enter in command mode → back to proxy
        await pilot.press("enter")
        await pilot.pause()
        assert proxy.display is True, "Proxy must reappear after Enter in command mode"
        assert (
            vim_inp.display is False
        ), "VimInput must hide after Enter in command mode"
        assert screen.focused is proxy, "Proxy should regain focus"

        # Second Enter on proxy works again
        await pilot.press("enter")
        await pilot.pause()
        assert vim_inp.display is True, "VimInput must show on second Enter on proxy"


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
