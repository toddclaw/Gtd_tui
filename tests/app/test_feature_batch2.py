"""Tests for the second feature batch:
- Feature: ? opens HelpScreen from sidebar focus
- Feature: 'r' key initiates task rename (INSERT mode, task_rename stage)
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp, HelpScreen
from gtd_tui.gtd.operations import add_project, add_task_to_folder
from gtd_tui.storage.file import save_data

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _save_tasks_to(tmp_path: Path, tasks: list) -> Path:
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file)
    return data_file


# ---------------------------------------------------------------------------
# Help screen from sidebar
# ---------------------------------------------------------------------------


async def test_help_screen_from_sidebar(tmp_path: Path) -> None:
    """Pressing '?' when the sidebar is focused opens the HelpScreen."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Move focus to the sidebar using 'h'
        await pilot.press("h")
        await pilot.pause()
        # Press '?' to open the help screen
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)


async def test_help_screen_dismisses_on_q(tmp_path: Path) -> None:
    """Pressing 'q' dismisses the HelpScreen and returns to the main screen."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(pilot.app.screen, HelpScreen)
        await pilot.press("q")
        await pilot.pause()
        # After dismissal we should be back on the main app screen
        assert not isinstance(pilot.app.screen, HelpScreen)


# ---------------------------------------------------------------------------
# Rename task from task list ('r' key)
# ---------------------------------------------------------------------------


async def test_rename_task_from_list_enters_insert_mode(tmp_path: Path) -> None:
    """Pressing 'r' on a task in the task list enters INSERT mode at task_rename stage."""
    tasks = add_task_to_folder([], "inbox", "Original Title")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        # Give focus to the task list
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert app._mode == "INSERT"
        assert app._input_stage == "task_rename"


async def test_rename_task_from_list_sets_rename_task_id(tmp_path: Path) -> None:
    """After pressing 'r', _rename_task_id is set to the focused task's id."""
    tasks = add_task_to_folder([], "inbox", "Task to rename")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        # The rename target should be the id of the only task
        assert app._rename_task_id == tasks[0].id


async def test_rename_escape_returns_to_normal_mode(tmp_path: Path) -> None:
    """Pressing Escape during rename cancels and returns to NORMAL mode."""
    tasks = add_task_to_folder([], "inbox", "Cancel me")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert app._mode == "INSERT"
        await pilot.press("escape")
        await pilot.pause()
        assert app._mode == "NORMAL"


# ---------------------------------------------------------------------------
# Regression: y key should yank divider tasks (title == "-" or "=")
# ---------------------------------------------------------------------------


async def test_yank_divider_task(tmp_path: Path) -> None:
    """y key should set _task_register even for divider tasks."""
    tasks = add_task_to_folder([], "inbox", "-")  # divider task
    tasks = add_task_to_folder(tasks, "inbox", "Normal task")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert pilot.app._task_register is not None
        assert pilot.app._task_register.title == "-"


# ---------------------------------------------------------------------------
# Regression: paste (p) inserts duplicate after the currently selected task
# ---------------------------------------------------------------------------


async def test_paste_after_correct_position(tmp_path: Path) -> None:
    """p should insert duplicate immediately after the currently selected task."""
    # Build tasks A, B, C in inbox (add_task_to_folder appends, so add in order)
    tasks: list = []
    for title in ["A", "B", "C"]:
        tasks = add_task_to_folder(tasks, "inbox", title)
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        # Yank A (first task, currently selected)
        await pilot.press("y")
        await pilot.pause()
        # Move to B
        await pilot.press("j")
        await pilot.pause()
        # Paste after B — duplicate of A appears after B
        await pilot.press("p")
        await pilot.pause()
        task_titles = [
            t.title
            for t in sorted(
                [t for t in pilot.app._all_tasks if t.folder_id == "inbox"],
                key=lambda t: t.position,
            )
        ]
        # A, B, A(dup), C — total 4 tasks
        assert len(task_titles) == 4
        assert task_titles[0] == "A"
        assert task_titles[1] == "B"
        assert task_titles[2] == "A"  # duplicate right after B
        assert task_titles[3] == "C"


# ---------------------------------------------------------------------------
# Regression: single Esc during rename returns to NORMAL (not double-Esc)
# ---------------------------------------------------------------------------


async def test_rename_single_esc_returns_to_normal(tmp_path: Path) -> None:
    """A single Esc press during rename should return to NORMAL mode."""
    tasks = add_task_to_folder([], "inbox", "My Task With Long Title")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")  # enter rename mode
        await pilot.pause()
        assert app._mode == "INSERT"
        await pilot.press("escape")  # single Esc
        await pilot.pause()
        assert app._mode == "NORMAL"
        # Original title should be unchanged
        assert pilot.app._all_tasks[0].title == "My Task With Long Title"


# ---------------------------------------------------------------------------
# Regression: : (colon) from sidebar focus enters command mode
# ---------------------------------------------------------------------------


async def test_colon_command_from_sidebar(tmp_path: Path) -> None:
    """Pressing : while sidebar has focus should enter command mode."""
    data_file = _save_tasks_to(tmp_path, [])
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Move focus to sidebar using 'h'
        await pilot.press("h")
        await pilot.pause()
        await pilot.press("colon")
        await pilot.pause()
        assert pilot.app._mode == "INSERT"
        assert pilot.app._input_stage == "command"


# ---------------------------------------------------------------------------
# Regression: assigning task to project removes it from its original folder
# ---------------------------------------------------------------------------


async def test_assign_to_project_removes_from_folder(tmp_path: Path) -> None:
    """Assigning a task to a project should clear the task's folder_id."""
    tasks = add_task_to_folder([], "inbox", "My Task")
    projects = add_project([], "My Project")
    data_file = tmp_path / "data.json"
    save_data(tasks, [], data_file, projects=projects)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        await pilot.pause()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        initial_folder = pilot.app._all_tasks[0].folder_id
        assert initial_folder == "inbox"
        # Open action picker with m
        await pilot.press("m")
        await pilot.pause()
        # Picker is open (screen_stack has 2 entries)
        assert len(pilot.app.screen_stack) == 2
        # Picker starts on Inbox (first selectable). Navigate to My Project:
        # Inbox → Today → WaitingOn → Someday → Reference → [header skipped] → My Project
        # That is 5 j presses (headers are skipped automatically).
        for _ in range(5):
            await pilot.press("j")
            await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Task should now have empty folder_id and belong to the project
        task = pilot.app._all_tasks[0]
        assert task.folder_id == ""
        assert task.project_id == projects[0].id
