"""Tests for the second feature batch:
- Feature: ? opens HelpScreen from sidebar focus
- Feature: 'r' key initiates task rename (INSERT mode, task_rename stage)
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import GtdApp, HelpScreen
from gtd_tui.gtd.operations import add_project, add_task_to_folder, complete_project
from gtd_tui.storage.file import save_data
from gtd_tui.widgets.vim_input import VimInput

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


async def test_rename_uses_vim_input_not_plain_input(tmp_path: Path) -> None:
    """Regression: rename (r) must use VimInput (#vim-input), not Input (#task-input).

    VimInput provides Esc→command, 2nd Esc→save behavior like o/O.
    """
    tasks = add_task_to_folder([], "inbox", "Task")
    data_file = _save_tasks_to(tmp_path, tasks)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._current_view = "inbox"
        app._refresh_list()
        app.query_one("#task-list", ListView).focus()
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        focused = app.screen.focused
        assert focused is not None
        assert isinstance(focused, VimInput)
        assert (focused.id or "") == "vim-input"


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


async def test_rename_second_esc_saves(tmp_path: Path) -> None:
    """r on task: 1st Esc=command mode, 2nd Esc=saves rename (like o/O)."""
    tasks = add_task_to_folder([], "inbox", "Old title")
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
        assert app._input_stage == "task_rename"
        for _ in range(len("Old title")):
            await pilot.press("backspace")
        for ch in "New title":
            await pilot.press(ch)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert any(t.title == "New title" for t in app._all_tasks)


async def test_rename_ctrl_c_cancels(tmp_path: Path) -> None:
    """Ctrl+C during rename cancels without saving."""
    tasks = add_task_to_folder([], "inbox", "Original")
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
        await pilot.press("c", "h", "a", "n", "g", "e", "d")
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert all(t.title != "changed" for t in app._all_tasks)


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
# Regression: rename (r) Esc behavior matches o/O: 1st Esc→command, 2nd Esc→save
# ---------------------------------------------------------------------------


async def test_rename_single_esc_enters_command_mode(tmp_path: Path) -> None:
    """Single Esc during rename switches to command mode; second Esc saves (like o/O)."""
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
        vim_input = app.query_one("#vim-input", VimInput)
        assert vim_input._vim_mode == "insert"
        await pilot.press("escape")  # first Esc → command mode
        await pilot.pause()
        assert app._mode == "INSERT"
        assert vim_input._vim_mode == "command"
        await pilot.press("escape")  # second Esc → save and return to NORMAL
        await pilot.pause()
        assert app._mode == "NORMAL"
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
        # Inbox → Today → Anytime → WaitingOn → Someday → Reference → [header skipped] → My Project
        # That is 6 j presses (headers are skipped automatically).
        for _ in range(6):
            await pilot.press("j")
            await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Task should now have empty folder_id and belong to the project
        task = pilot.app._all_tasks[0]
        assert task.folder_id == ""
        assert task.project_id == projects[0].id


# ---------------------------------------------------------------------------
# Outcome: rename saves new title (not just sets mode)
# ---------------------------------------------------------------------------


async def test_rename_saves_new_title(tmp_path: Path) -> None:
    """Submitting a rename via Enter should persist the new title."""
    tasks = add_task_to_folder([], "inbox", "Old Title")
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
        # Clear the pre-filled text and type the new title
        for _ in range(len("Old Title")):
            await pilot.press("backspace")
        await pilot.pause()
        for ch in "New Title":
            await pilot.press(ch)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert pilot.app._all_tasks[0].title == "New Title"


# ---------------------------------------------------------------------------
# Regression: completed projects must not appear in m picker
# ---------------------------------------------------------------------------


async def test_completed_project_not_in_move_picker(tmp_path: Path) -> None:
    """The m picker must not include completed projects."""
    tasks = add_task_to_folder([], "inbox", "My Task")
    projects = add_project([], "Active Project")
    projects = add_project(projects, "Done Project")
    projects = complete_project(projects, projects[1].id)  # mark Done Project complete
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
        await pilot.press("m")
        await pilot.pause()
        # ActionPickerScreen should be open
        assert len(pilot.app.screen_stack) == 2
        picker_screen = pilot.app.screen_stack[-1]
        # _picker_entries is a list of (label, payload) tuples
        entry_labels = [label for label, _ in picker_screen._picker_entries]
        picker_text = "\n".join(entry_labels)
        assert "Done Project" not in picker_text
        assert "Active Project" in picker_text
