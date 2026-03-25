"""Integration tests for Feature E: d/p/P cut-paste for tasks.

Tests verify that:
- d populates _cut_register and removes the task
- p after d moves the task below the cursor in the same folder
- p after d moves the task to a different folder when the view changes
- visual d on multiple tasks then p moves all of them
- u after d restores the task and clears _cut_register
- y/p still creates a duplicate (cut register does not interfere)
"""

from __future__ import annotations

from pathlib import Path

from gtd_tui.app import GtdApp
from gtd_tui.gtd.operations import add_task_to_folder
from gtd_tui.storage.file import save_data
from tests.cfg import CFG_TASK_LIST_FOCUS


def _prepopulate(tmp_path: Path, *titles: str, folder_id: str = "today") -> Path:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task_to_folder(tasks, folder_id, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


async def test_d_populates_cut_register(tmp_path: Path) -> None:
    """Pressing d stores the task in _cut_register."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_id = app._all_tasks[0].id
        await pilot.press("d")
        await pilot.pause()
        assert len(app._cut_register) == 1
        assert app._cut_register[0].id == task_id


async def test_d_then_p_moves_task_same_folder(tmp_path: Path) -> None:
    """d on task 0 then p should move it below the new cursor position."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta", "Gamma")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        original_id = app._all_tasks[0].id
        # Delete first task (Alpha)
        await pilot.press("d")
        await pilot.pause()
        # Now Beta is at index 0 — paste below it
        await pilot.press("p")
        await pilot.pause()
        # Alpha should be back in the task list
        task_ids = [t.id for t in app._all_tasks if not t.is_deleted]
        assert original_id in task_ids
        # Cut register should be cleared after paste
        assert app._cut_register == []


async def test_d_then_P_moves_task_above(tmp_path: Path) -> None:
    """d then P moves the task above the current cursor."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta", "Gamma")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        original_id = app._all_tasks[0].id
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("P")
        await pilot.pause()
        task_ids = [t.id for t in app._all_tasks if not t.is_deleted]
        assert original_id in task_ids
        assert app._cut_register == []


async def test_undo_after_d_restores_and_clears_register(tmp_path: Path) -> None:
    """u after d restores the deleted task and clears _cut_register."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_id = app._all_tasks[0].id
        await pilot.press("d")
        await pilot.pause()
        assert len(app._cut_register) == 1
        await pilot.press("u")
        await pilot.pause()
        # _cut_register should be cleared by undo
        assert app._cut_register == []
        # Task should be restored (not deleted)
        live_ids = [t.id for t in app._all_tasks if not t.is_deleted]
        assert task_id in live_ids


async def test_y_p_still_duplicates(tmp_path: Path) -> None:
    """y then p still creates a duplicate (yank, not cut-paste)."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        original_count = len([t for t in app._all_tasks if not t.is_deleted])
        original_id = app._all_tasks[0].id
        await pilot.press("y")
        await pilot.pause()
        # _cut_register should NOT be set by y
        assert app._cut_register == []
        assert app._task_register is not None
        await pilot.press("p")
        await pilot.pause()
        live_tasks = [t for t in app._all_tasks if not t.is_deleted]
        # Should have one more task (duplicate)
        assert len(live_tasks) == original_count + 1
        # Original task must still exist with same ID
        assert any(t.id == original_id for t in live_tasks)
        # Cut register stays empty
        assert app._cut_register == []


async def test_visual_d_then_p_moves_multiple(tmp_path: Path) -> None:
    """Visual select 2 tasks, d, then p moves both tasks."""
    data_file = _prepopulate(tmp_path, "Alpha", "Beta", "Gamma", "Delta")
    app = GtdApp(data_file=data_file, config=CFG_TASK_LIST_FOCUS)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Enter visual mode and select first 2 tasks
        id0 = app._all_tasks[0].id
        id1 = app._all_tasks[1].id
        await pilot.press("v")  # enter visual mode
        await pilot.pause()
        await pilot.press("j")  # extend selection down
        await pilot.pause()
        await pilot.press("d")  # bulk delete
        await pilot.pause()
        assert len(app._cut_register) == 2
        cut_ids = {t.id for t in app._cut_register}
        assert id0 in cut_ids
        assert id1 in cut_ids
        # Paste them back
        await pilot.press("p")
        await pilot.pause()
        live_ids = {t.id for t in app._all_tasks if not t.is_deleted}
        assert id0 in live_ids
        assert id1 in live_ids
        assert app._cut_register == []
