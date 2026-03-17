"""Integration tests for BACKLOG-15: VISUAL mode bulk operations."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Label, ListItem, ListView

from gtd_tui.app import GtdApp
from gtd_tui.gtd.operations import add_task, add_waiting_on_task, create_folder
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path, *titles: str) -> GtdApp:
    """Create an app with tasks in display order: first title = first in list."""
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in reversed(titles):
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return GtdApp(data_file=data_file)


def _status(app: GtdApp) -> str:
    return str(app.query_one("#status", Label).content)


def _list_items(app: GtdApp) -> list[ListItem]:
    return list(app.query_one("#task-list", ListView).query(ListItem))


# ---------------------------------------------------------------------------
# Entering and exiting VISUAL mode
# ---------------------------------------------------------------------------


async def test_v_enters_visual_mode(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        assert pilot.app._visual_mode is True
        assert pilot.app._visual_anchor_idx == 0
        assert "VISUAL" in _status(pilot.app)


async def test_v_on_empty_list_does_not_enter_visual_mode(tmp_path: Path) -> None:
    async with _make_app(tmp_path).run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        assert pilot.app._visual_mode is False


async def test_escape_exits_visual_mode(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        assert pilot.app._visual_mode is True
        await pilot.press("escape")
        await pilot.pause()
        assert pilot.app._visual_mode is False
        assert pilot.app._visual_anchor_idx is None
        assert "VISUAL" not in _status(pilot.app)


async def test_j_extends_selection_downward(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")  # enter visual at index 0
        await pilot.pause()
        await pilot.press("j")  # extend down to index 1
        await pilot.pause()
        lv = pilot.app.query_one("#task-list", ListView)
        assert lv.index == 1
        assert pilot.app._visual_anchor_idx == 0  # anchor unchanged


async def test_k_extends_selection_upward(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("j")  # move to index 1 in NORMAL
        await pilot.pause()
        await pilot.press("v")  # enter visual at index 1
        await pilot.pause()
        await pilot.press("k")  # extend up to index 0
        await pilot.pause()
        lv = pilot.app.query_one("#task-list", ListView)
        assert lv.index == 0
        assert pilot.app._visual_anchor_idx == 1


# ---------------------------------------------------------------------------
# CSS highlight classes
# ---------------------------------------------------------------------------


async def test_visual_selected_rows_have_css_class(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        await pilot.press("j")  # select A+B (indices 0 and 1)
        await pilot.pause()
        items = _list_items(pilot.app)
        assert "visual-selected" in items[0].classes
        assert "visual-selected" in items[1].classes
        assert "visual-selected" not in items[2].classes


async def test_exit_visual_clears_css_classes(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        for item in _list_items(pilot.app):
            assert "visual-selected" not in item.classes


# ---------------------------------------------------------------------------
# Bulk complete
# ---------------------------------------------------------------------------


async def test_bulk_complete_completes_selected_tasks(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")  # select A + B
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        app = pilot.app
        remaining = [t for t in app._all_tasks if t.folder_id != "logbook"]
        completed = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(remaining) == 1
        assert remaining[0].title == "C"
        assert len(completed) == 2
        assert app._visual_mode is False


async def test_bulk_complete_space_key(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        logbook = [t for t in pilot.app._all_tasks if t.folder_id == "logbook"]
        assert len(logbook) == 2


async def test_bulk_complete_is_single_undo_step(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("x")  # complete A + B
        await pilot.pause()
        await pilot.press("u")  # undo — both should come back
        await pilot.pause()
        active = [t for t in pilot.app._all_tasks if t.folder_id != "logbook"]
        assert len(active) == 3


# ---------------------------------------------------------------------------
# Bulk delete
# ---------------------------------------------------------------------------


async def test_bulk_delete_removes_selected_tasks(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        app = pilot.app
        active = [t for t in app._all_tasks if t.folder_id != "logbook"]
        assert len(active) == 1
        assert active[0].title == "C"
        assert app._visual_mode is False


async def test_bulk_delete_is_single_undo_step(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        active = [t for t in pilot.app._all_tasks if t.folder_id != "logbook"]
        assert len(active) == 3


# ---------------------------------------------------------------------------
# Bulk schedule
# ---------------------------------------------------------------------------


async def test_bulk_schedule_applies_date_to_selected_tasks(tmp_path: Path) -> None:
    from datetime import date, timedelta

    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")  # select A + B
        await pilot.pause()
        await pilot.press("s")  # open schedule input (bulk)
        await pilot.pause()
        await pilot.press("+", "3", "d", "enter")  # type "+3d" and submit
        await pilot.pause()
        app = pilot.app
        expected = date.today() + timedelta(days=3)
        scheduled = [t for t in app._all_tasks if t.scheduled_date == expected]
        assert len(scheduled) == 2
        titles = {t.title for t in scheduled}
        assert titles == {"A", "B"}


async def test_bulk_schedule_is_single_undo_step(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        await pilot.press("+", "3", "d", "enter")
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        scheduled = [t for t in pilot.app._all_tasks if t.scheduled_date is not None]
        assert len(scheduled) == 0


# ---------------------------------------------------------------------------
# Bulk move to Waiting On / Today
# ---------------------------------------------------------------------------


async def test_bulk_w_moves_selected_to_waiting_on(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        wo = [t for t in pilot.app._all_tasks if t.folder_id == "waiting_on"]
        today = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        assert len(wo) == 2
        assert len(today) == 1
        assert today[0].title == "C"
        assert pilot.app._visual_mode is False


async def test_bulk_t_moves_selected_to_today(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in ("A", "B", "C"):
        tasks = add_waiting_on_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Navigate to Waiting On view (Inbox=1, Today=2, Upcoming=3, WaitingOn=4)
        await pilot.press("4")
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        today = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        assert len(today) == 2


async def test_bulk_w_is_single_undo_step(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("w")
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        today = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        assert len(today) == 2


# ---------------------------------------------------------------------------
# Bulk move to folder
# ---------------------------------------------------------------------------


async def test_bulk_m_moves_selected_to_chosen_folder(tmp_path: Path) -> None:

    data_file = tmp_path / "data.json"
    tasks: list = []
    folders: list = []
    for title in reversed(("A", "B", "C")):
        tasks = add_task(tasks, title)
    folder_id = "test-folder-id"
    folders = create_folder(folders, "Work", folder_id=folder_id)
    save_data(tasks, folders, data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")  # select A + B
        await pilot.pause()
        await pilot.press("m")  # open folder picker (bulk)
        await pilot.pause()
        # Sidebar is focused. Navigate to "Work" folder.
        # Built-ins: Today(0), Upcoming(1), Waiting On(2), Work(3), Someday(4), Logbook(5)
        await pilot.press("j", "j", "j")  # move to index 3 (Work)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        in_work = [t for t in pilot.app._all_tasks if t.folder_id == folder_id]
        assert len(in_work) == 2
        titles = {t.title for t in in_work}
        assert titles == {"A", "B"}


async def test_bulk_m_is_single_undo_step(tmp_path: Path) -> None:

    data_file = tmp_path / "data.json"
    tasks: list = []
    folders: list = []
    for title in ("A", "B"):
        tasks = add_task(tasks, title)
    folder_id = "test-folder-id-2"
    folders = create_folder(folders, "Work", folder_id=folder_id)
    save_data(tasks, folders, data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")
        await pilot.pause()
        await pilot.press("m")
        await pilot.pause()
        await pilot.press("j", "j", "j")  # navigate to Work
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("u")  # undo
        await pilot.pause()
        in_today = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        assert len(in_today) == 2


# ---------------------------------------------------------------------------
# Block reorder (J / K)
# ---------------------------------------------------------------------------


async def test_J_moves_selected_block_down(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C", "D").run_test() as pilot:
        await pilot.pause()
        await pilot.press("j")  # cursor to index 1 (B)
        await pilot.pause()
        await pilot.press("v", "j")  # visual: anchor=1, extend to 2 (B + C)
        await pilot.pause()
        await pilot.press("J")  # move block down
        await pilot.pause()
        active = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        active_sorted = sorted(active, key=lambda t: t.position)
        titles = [t.title for t in active_sorted]
        assert titles == ["A", "D", "B", "C"]
        assert pilot.app._visual_mode is True  # stays in visual mode


async def test_K_moves_selected_block_up(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C", "D").run_test() as pilot:
        await pilot.pause()
        await pilot.press("j")  # cursor to index 1 (B)
        await pilot.pause()
        await pilot.press("v", "j")  # visual: anchor=1, extend to 2 (B + C)
        await pilot.pause()
        await pilot.press("K")  # move block up
        await pilot.pause()
        active = [
            t
            for t in pilot.app._all_tasks
            if t.folder_id == "today" and t.completed_at is None
        ]
        active_sorted = sorted(active, key=lambda t: t.position)
        titles = [t.title for t in active_sorted]
        assert titles == ["B", "C", "A", "D"]
        assert pilot.app._visual_mode is True


async def test_J_block_move_is_single_undo_step(tmp_path: Path) -> None:
    async with _make_app(tmp_path, "A", "B", "C").run_test() as pilot:
        await pilot.pause()
        await pilot.press("v", "j")  # select A + B
        await pilot.pause()
        await pilot.press("J")  # move down
        await pilot.pause()
        await pilot.press("u")  # undo
        await pilot.pause()
        active = sorted(
            [
                t
                for t in pilot.app._all_tasks
                if t.folder_id == "today" and t.completed_at is None
            ],
            key=lambda t: t.position,
        )
        assert [t.title for t in active] == ["A", "B", "C"]
