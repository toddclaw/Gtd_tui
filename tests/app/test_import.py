"""Integration tests for Feature D: Import tasks from .md (checkbox format).

Tests cover:
- Ctrl+I opens the ImportMdScreen modal
"""

from __future__ import annotations

from pathlib import Path

from gtd_tui.app import GtdApp, ImportMdScreen
from gtd_tui.storage.file import save_data
from tests.cfg import CFG_TASK_LIST_FOCUS


def _empty_data(tmp_path: Path) -> Path:
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)
    return data_file


async def test_ctrl_i_opens_import_screen(tmp_path: Path) -> None:
    """Pressing Ctrl+I from the task list opens the ImportMdScreen modal."""
    data_file = _empty_data(tmp_path)
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+i")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ImportMdScreen)


async def test_import_md_screen_cancel_returns_to_main(tmp_path: Path) -> None:
    """Pressing Escape on the ImportMdScreen closes it without importing."""
    data_file = _empty_data(tmp_path)
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+i")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ImportMdScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, ImportMdScreen)
        assert app._all_tasks == []


async def test_import_md_file_merges_tasks(tmp_path: Path) -> None:
    """Providing a valid .md file path and confirming imports tasks."""
    data_file = _empty_data(tmp_path)
    md_file = tmp_path / "tasks.md"
    md_file.write_text("- [ ] Imported task one\n- [x] Imported done task\n")

    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+i")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ImportMdScreen)
        # Type the path in the input
        from textual.widgets import Input

        inp = pilot.app.screen.query_one("#import-path", Input)
        inp.value = str(md_file)
        await pilot.press("enter")
        await pilot.pause()
        # Modal should be dismissed
        assert not isinstance(pilot.app.screen, ImportMdScreen)
        titles = [t.title for t in app._all_tasks]
        assert "Imported task one" in titles
        assert "Imported done task" in titles
        # One task should be completed
        done = [t for t in app._all_tasks if t.completed_at is not None]
        assert len(done) == 1
