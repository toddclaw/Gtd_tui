"""TUI integration tests for GtdApp.

Uses Textual's headless `run_test()` / Pilot API to drive the app through key
events and inspect the resulting DOM and app state.  No real terminal or
subprocess is needed.  Each test uses a `tmp_path`-backed data file so the
user's real data is never touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import Label, ListView

from gtd_tui.app import GtdApp, SearchScreen, TaskDetailScreen
from gtd_tui.gtd.operations import add_task, add_task_to_folder, create_folder
from gtd_tui.storage.file import save_data
from gtd_tui.widgets.vim_input import VimInput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _prepopulate(tmp_path: Path, *titles: str) -> Path:
    """Write tasks to a data file and return the path."""
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in titles:
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


# ---------------------------------------------------------------------------
# Launch / initial state
# ---------------------------------------------------------------------------


async def test_launch_shows_today_header(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        header = app.query_one("#header", Label)
        assert "Today" in str(header.content)


async def test_launch_shows_empty_hint_with_no_tasks(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        hint = app.query_one("#empty-hint", Label)
        assert "hidden" not in hint.classes


async def test_launch_loads_existing_tasks(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Buy milk", "Call dentist")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app._all_tasks) == 2


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------


async def test_press_o_enters_insert_mode(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert app._mode == "INSERT"
        assert app._input_stage == "title"


async def test_add_task_appears_in_task_list(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        # Type "Eat" one character at a time
        await pilot.press("E", "a", "t")
        await pilot.press("enter")  # confirm title, advance to notes
        await pilot.pause()
        await pilot.press("enter")  # skip notes, save task
        await pilot.pause()
        today_tasks = [t for t in app._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Eat" for t in today_tasks)


async def test_add_task_saves_to_data_file(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("R", "u", "n")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    # File must exist and contain the task
    assert data_file.exists()
    from gtd_tui.storage.file import load_tasks

    loaded = load_tasks(data_file)
    assert any(t.title == "Run" for t in loaded)


async def test_press_escape_cancels_task_creation(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        # First Esc: INSERT → COMMAND mode inside VimInput (stays in creation).
        await pilot.press("escape")
        await pilot.pause()
        # Second Esc: COMMAND mode bubbles to GtdApp → cancels the whole creation.
        await pilot.press("escape")
        await pilot.pause()
        assert app._mode == "NORMAL"
        assert len(app._all_tasks) == 0


# ---------------------------------------------------------------------------
# Task completion
# ---------------------------------------------------------------------------


async def test_x_completes_selected_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        completed = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(completed) == 1
        assert completed[0].title == "Finish report"


async def test_completing_task_removes_it_from_today(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert len(today) == 0


# ---------------------------------------------------------------------------
# Task deletion
# ---------------------------------------------------------------------------


async def test_d_deletes_selected_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(logbook) == 1
        assert logbook[0].title == "Finish report"
        assert logbook[0].is_deleted is True


async def test_deleted_task_not_marked_complete(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Finish report")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert logbook[0].is_complete is False


async def test_deleting_task_removes_it_from_today(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert len(today) == 0


async def test_deleted_task_persists_to_data_file(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Walk dog")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
    from gtd_tui.storage.file import load_tasks

    loaded = load_tasks(data_file)
    assert loaded[0].is_deleted is True
    assert loaded[0].folder_id == "logbook"


async def test_o_in_logbook_does_not_add_task(tmp_path: Path) -> None:
    """o and O must be no-ops in the Logbook — new tasks cannot be added there."""
    data_file = _prepopulate(tmp_path, "Done task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")  # complete → logbook
        await pilot.pause()
        app._current_view = "logbook"
        app._refresh_list()
        await pilot.pause()
        task_count = len(app._all_tasks)
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("O")
        await pilot.pause()
        assert len(app._all_tasks) == task_count  # no new tasks created
        assert app._mode != "INSERT"  # not in insert mode


async def test_d_in_logbook_purges_entry(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Done task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")  # complete → logbook
        await pilot.pause()
        # Switch to logbook view directly via app state
        app._current_view = "logbook"
        app._refresh_list()
        await pilot.pause()
        await pilot.press("d")  # purge
        await pilot.pause()
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert len(logbook) == 0


# ---------------------------------------------------------------------------
# Task detail modal (BACKLOG-11)
# ---------------------------------------------------------------------------


async def test_enter_opens_task_detail_screen(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Plan sprint")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)


async def test_escape_closes_task_detail_screen(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Plan sprint")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)


async def test_edit_task_title_and_notes(tmp_path: Path) -> None:
    """Open the detail view for 'foo', extend the title to 'foo bar',
    advance through Date to Notes, add 'bar', then Esc to save.

    Title VimInput opens in COMMAND mode.  'A' enters INSERT at end; type ' bar';
    Esc → COMMAND; Enter → submit title → focus Date.  Enter on empty Date → Notes.
    Notes VimInput in COMMAND mode; 'i' → INSERT; type 'bar'; Esc → COMMAND.
    Second Esc from notes COMMAND mode bubbles to TaskDetailScreen → save+close.
    """
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open detail view — title VimInput pre-filled with "foo", COMMAND mode
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # 'A' → insert mode at end of "foo", then type " bar"
        await pilot.press("A")
        await pilot.press("space", "b", "a", "r")
        # Esc → back to COMMAND mode (stays in modal)
        await pilot.press("escape")
        await pilot.pause()
        # Enter in COMMAND mode submits VimInput → focus advances to Date field
        await pilot.press("enter")
        await pilot.pause()
        # Enter on empty Date → focus advances to Deadline field
        await pilot.press("enter")
        await pilot.pause()
        # Enter on empty Deadline → focus advances to Notes
        await pilot.press("enter")
        await pilot.pause()

        # Notes VimInput in COMMAND mode (empty). 'i' → INSERT; type "bar"
        await pilot.press("i")
        await pilot.press("b", "a", "r")
        # Esc → COMMAND mode
        await pilot.press("escape")
        await pilot.pause()
        # Esc in COMMAND mode bubbles to TaskDetailScreen → save and close
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        # Verify the task was updated in memory and persisted
        task = next(t for t in app._all_tasks if t.folder_id != "logbook")
        assert task.title == "foo bar"
        assert task.notes == "bar"

        from gtd_tui.storage.file import load_tasks

        saved = load_tasks(data_file)
        saved_task = next(t for t in saved if t.folder_id != "logbook")
        assert saved_task.title == "foo bar"
        assert saved_task.notes == "bar"


async def test_detail_fields_normalised_on_focus_advance(tmp_path: Path) -> None:
    """Parseable fields are rewritten to canonical form when focus leaves them.

    Date 'tomorrow' → ISO date string.  Invalid repeat → '(invalid)'.
    """
    from datetime import date, timedelta

    data_file = _prepopulate(tmp_path, "Buy milk")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Advance from Title to Date field
        await pilot.press("enter")
        await pilot.pause()

        # Type 'tomorrow' then advance away — Date should normalise to ISO
        await pilot.press("i")
        for ch in "tomorrow":
            await pilot.press(ch)
        await pilot.press("escape")  # back to COMMAND mode
        await pilot.press("j")  # j → normalise + advance to Deadline
        await pilot.pause()

        date_inp = app.screen.query_one("#detail-date-input", VimInput)
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert date_inp.value == expected

        # Now on Deadline — type an invalid value and advance away
        await pilot.press("i")
        for ch in "not-a-date":
            await pilot.press(ch)
        await pilot.press("escape")
        await pilot.press("j")  # j → normalise + advance to Notes
        await pilot.pause()

        deadline_inp = app.screen.query_one("#detail-deadline-input", VimInput)
        assert deadline_inp.value == "(invalid)"

        await pilot.press("escape")  # save & close
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)


async def test_detail_date_someday_moves_task_to_someday_folder(tmp_path: Path) -> None:
    """Entering 'someday' in the Date field of TaskDetailScreen moves the task
    to the Someday folder (case-insensitive, matches [Ss]omeday)."""
    data_file = _prepopulate(tmp_path, "Read a book")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail view
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Navigate from title (COMMAND mode) → Date field
        await pilot.press("enter")
        await pilot.pause()

        # Type "someday" in the Date field (starts in COMMAND mode — 'i' enters INSERT)
        await pilot.press("i")
        for ch in "someday":
            await pilot.press(ch)
        await pilot.press("escape")  # back to COMMAND mode
        await pilot.pause()
        await pilot.press("escape")  # save and close
        await pilot.pause()

        assert not isinstance(app.screen, TaskDetailScreen)
        task = next(t for t in app._all_tasks if t.title == "Read a book")
        assert task.folder_id == "someday"
        assert task.scheduled_date is None


async def test_set_repeat_rule_moves_task_to_upcoming(tmp_path: Path) -> None:
    """Open the detail view for 'foo', navigate to the Repeat field, enter '7 days',
    save, then switch to the Upcoming view and verify the task appears there."""
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open detail view — title input focused
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Advance: title → date (Enter), date → deadline (Enter), deadline → notes (Enter), notes → repeat (Tab)
        await pilot.press("enter")  # title → date
        await pilot.pause()
        await pilot.press("enter")  # date → deadline (empty date, no change)
        await pilot.pause()
        await pilot.press("enter")  # deadline → notes (empty deadline, no change)
        await pilot.pause()
        await pilot.press("tab")  # notes → repeat (multiline: Tab advances)
        await pilot.pause()

        # Repeat is now VimInput in COMMAND mode — enter insert mode first
        await pilot.press("i")  # command → insert mode
        await pilot.press("7", " ", "d", "a", "y", "s")
        await pilot.press("escape")  # insert → command mode
        await pilot.pause()

        # Advance repeat → recur (Enter in command mode fires Submitted)
        await pilot.press("enter")  # repeat → recur
        await pilot.pause()
        # Esc from recur command mode bubbles to screen → save and close
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        # The task must still be in Today (it stays actionable)
        from gtd_tui.gtd.operations import today_tasks, upcoming_tasks

        today = today_tasks(app._all_tasks)
        assert any(t.title == "foo" for t in today), "task should remain in Today"

        # AND it must appear in Upcoming (previewing the next_due date)
        upcoming = upcoming_tasks(app._all_tasks)
        assert any(t.title == "foo" for t in upcoming), "task should appear in Upcoming"


async def test_set_date_via_detail_screen(tmp_path: Path) -> None:
    """Open detail view, type a date in the Date field, save — task is scheduled."""
    from datetime import date, timedelta

    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Skip title (command mode, Enter → date field)
        await pilot.press("enter")
        await pilot.pause()

        # Type '+7d' in Date field (command mode → insert → type → esc)
        await pilot.press("i")
        await pilot.press("+", "7", "d")
        await pilot.press("escape")  # insert → command
        await pilot.pause()
        # Esc from command mode bubbles to screen → save and close
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        task = next(t for t in app._all_tasks if t.folder_id != "logbook")
        assert task.scheduled_date == date.today() + timedelta(days=7)


async def test_j_navigates_to_next_field_in_detail_screen(tmp_path: Path) -> None:
    """Pressing j in command mode on a single-line field moves focus to the next field."""
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail — title focused
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Press j in command mode — focus should move from title to date
        await pilot.press("j")
        await pilot.pause()
        focused = app.screen.focused
        assert focused is not None
        assert focused.id == "detail-date-input"


# ---------------------------------------------------------------------------
# Search modal (BACKLOG-8)
# ---------------------------------------------------------------------------


async def test_slash_opens_search_screen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)


async def test_escape_closes_search_screen(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SearchScreen)


async def test_search_tasks_in_user_folder_no_markup_crash(tmp_path: Path) -> None:
    """Searching when tasks exist in a user-created folder must not raise MarkupError.

    Previously, the search result label used f"[{folder_id[:8]}] ..." which Textual
    parsed as a markup tag.  When the highlight span [bold yellow]...[/bold yellow]
    followed, the closing tag had no matching open tag and raised MarkupError.
    """
    data_file = tmp_path / "data.json"
    folders = create_folder([], "My Projects")
    folder_id = folders[0].id
    tasks = add_task_to_folder([], folder_id, "Schedule a meeting")
    save_data(tasks, folders, data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        # typing "s" matches "Schedule a meeting" in the user folder — this
        # previously caused a MarkupError crash
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SearchScreen)


async def test_search_title_with_brackets_no_markup_crash(tmp_path: Path) -> None:
    """Task titles containing '[' must not cause MarkupError when highlighted.

    Rich's markup_escape only escapes '[' when it forms a complete '[markup]'
    pattern.  A bare '[' left by splitting the title at the match position
    (e.g. '(ab) [cd]' matched on 'c' gives before='(ab) [') was not escaped,
    producing invalid markup like '(ab) [[bold yellow]c[/bold yellow]d]'.
    """
    data_file = _prepopulate(tmp_path, "(ab) [cd] {ef}")

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SearchScreen)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------


async def test_h_focuses_sidebar(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        assert sidebar.has_focus


async def test_l_from_sidebar_focuses_task_list(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")  # move to sidebar
        await pilot.pause()
        await pilot.press("l")  # move back to task list
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        assert task_list.has_focus


async def test_deleting_non_empty_folder_sends_tasks_to_logbook(tmp_path: Path) -> None:
    from textual.events import Key

    from gtd_tui.gtd.operations import add_task_to_folder, create_folder

    data_file = tmp_path / "data.json"
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Create a folder and add a task to it
        app._all_folders = create_folder(app._all_folders, "Work")
        folder_id = app._all_folders[-1].id
        app._all_tasks = add_task_to_folder(app._all_tasks, folder_id, "Work item")
        await pilot.pause()

        # Simulate state after the first 'd' (prompt is showing) and confirm
        app._delete_confirm_folder_id = folder_id
        app._handle_delete_confirm_key(Key("d", character="d"))
        await pilot.pause()

        # Folder gone and task is in logbook as deleted (not just discarded)
        assert not any(f.id == folder_id for f in app._all_folders)
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert any(t.title == "Work item" and t.is_deleted for t in logbook)


async def test_J_K_reorders_folders_in_sidebar(tmp_path: Path) -> None:
    from gtd_tui.gtd.operations import create_folder

    data_file = tmp_path / "data.json"
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Pre-populate two folders directly
        app._all_folders = create_folder(app._all_folders, "Alpha")
        app._all_folders = create_folder(app._all_folders, "Beta")
        app._rebuild_sidebar()
        await pilot.pause()

        # Focus sidebar and navigate to the Beta entry
        await pilot.press("h")
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        # built-ins: Inbox, Today, Upcoming, Waiting On, Alpha, Beta, Someday, Logbook
        # Beta is at index 5 now
        beta_idx = next(
            i
            for i, fid in enumerate(app._sidebar_view_ids)
            if fid
            not in ("inbox", "today", "upcoming", "waiting_on", "someday", "logbook")
            and next(
                (f for f in app._all_folders if f.id == fid and f.name == "Beta"), None
            )
        )
        sidebar.index = beta_idx
        await pilot.pause()
        await pilot.press("K")  # move Beta above Alpha
        await pilot.pause()

        ordered = sorted(app._all_folders, key=lambda f: f.position)
        names = [f.name for f in ordered]
        assert names.index("Beta") < names.index("Alpha")


async def test_o_in_sidebar_creates_folder(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")  # focus sidebar
        await pilot.pause()
        await pilot.press("o")  # open folder creation
        await pilot.pause()
        await pilot.press("W", "o", "r", "k")
        await pilot.press("enter")
        await pilot.pause()
        assert any(f.name == "Work" for f in app._all_folders)
        assert app._current_view == next(
            f.id for f in app._all_folders if f.name == "Work"
        )
        assert app.query_one("#task-list", ListView).has_focus


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------


async def test_undo_restores_completed_task(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Write tests")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("x")  # complete the task
        await pilot.pause()
        await pilot.press("u")  # undo
        await pilot.pause()
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Write tests" for t in today)


async def test_undo_with_nothing_to_undo_shows_message(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("u")
        await pilot.pause()
        status = app.query_one("#status", Label)
        assert "nothing to undo" in str(status.content)


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


async def test_tasks_persist_across_app_restarts(tmp_path: Path) -> None:
    data_file = tmp_path / "data.json"

    # First session: add a task
    app1 = GtdApp(data_file=data_file)
    async with app1.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("M", "e", "d", "i", "t", "a", "t", "e")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

    # Second session: load the same data file and verify the task is there
    app2 = GtdApp(data_file=data_file)
    async with app2.run_test() as pilot:
        await pilot.pause()
        today = [t for t in app2._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Meditate" for t in today)


# ---------------------------------------------------------------------------
# BACKLOG-17: Recurrence marker in task labels
# ---------------------------------------------------------------------------


async def test_recurring_task_shows_recurrence_marker(tmp_path: Path) -> None:
    """Tasks with a repeat_rule should display a ↻ marker in the list."""
    data_file = _prepopulate(tmp_path, "foo")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Open detail, advance to repeat field, set 7 days
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")  # title → date
        await pilot.pause()
        await pilot.press("enter")  # date → deadline
        await pilot.pause()
        await pilot.press("enter")  # deadline → notes
        await pilot.pause()
        await pilot.press("tab")  # notes → repeat (multiline: Tab advances)
        await pilot.pause()
        await pilot.press("i")  # command → insert mode
        await pilot.press("7", " ", "d", "a", "y", "s")
        await pilot.press("escape")  # insert → command mode
        await pilot.press("enter")  # repeat → recur
        await pilot.pause()
        await pilot.press("escape")  # save and close
        await pilot.pause()

        task_list = app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        assert any("↻" in lbl for lbl in labels)


# ---------------------------------------------------------------------------
# BACKLOG-17: H/M/L navigation
# ---------------------------------------------------------------------------


async def test_H_jumps_to_top(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Task 1", "Task 2", "Task 3")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        # Move to last item first
        await pilot.press("G")
        await pilot.pause()
        assert task_list.index == 2
        # H should jump back to top
        await pilot.press("H")
        await pilot.pause()
        assert task_list.index == 0


async def test_L_jumps_to_bottom(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Task 1", "Task 2", "Task 3")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        await pilot.press("L")
        await pilot.pause()
        assert task_list.index == 2


async def test_M_jumps_to_middle(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Task 1", "Task 2", "Task 3", "Task 4", "Task 5")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        await pilot.press("M")
        await pilot.pause()
        # n=5, n//2=2 → index 2
        assert task_list.index == 2


# ---------------------------------------------------------------------------
# BACKLOG-17: "someday" date keyword
# ---------------------------------------------------------------------------


async def test_someday_keyword_moves_task_to_someday_folder(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Low priority task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Press 's' to open schedule input
        await pilot.press("s")
        await pilot.pause()
        # Type "someday" and confirm
        await pilot.press("s", "o", "m", "e", "d", "a", "y")
        await pilot.press("enter")
        await pilot.pause()
        someday = [t for t in app._all_tasks if t.folder_id == "someday"]
        assert any(t.title == "Low priority task" for t in someday)
        today = [t for t in app._all_tasks if t.folder_id == "today"]
        assert not any(t.title == "Low priority task" for t in today)


# ---------------------------------------------------------------------------
# BACKLOG-17: Sidebar task counts
# ---------------------------------------------------------------------------


async def test_sidebar_shows_today_count(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "Task A", "Task B")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        # Find the Today item regardless of its index (Inbox is now first)
        today_label = next(
            str(item.query_one(Label).render())
            for item in sidebar.query("ListItem")
            if "Today" in str(item.query_one(Label).render())
        )
        assert "Today" in today_label
        assert "(2)" in today_label


# ---------------------------------------------------------------------------
# BACKLOG-21: Positional folder insertion with o/O
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_o_inserts_folder_after_selected(tmp_path: Path) -> None:
    """o in sidebar creates a new folder directly after the currently selected folder."""
    from gtd_tui.gtd.operations import create_folder
    from gtd_tui.storage.file import load_folders, save_data

    data_file = tmp_path / "data.json"
    folders = create_folder([], "Alpha")
    folders = create_folder(folders, "Beta")
    save_data([], folders, data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Press h to move focus to sidebar (task-list → sidebar)
        await pilot.press("h")
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        # Alpha is at sidebar index 4: Inbox=0, Today=1, Upcoming=2, WaitingOn=3, Alpha=4
        sidebar.index = 4
        await pilot.pause()
        await pilot.press("o")  # open folder slot after Alpha
        await pilot.pause()
        await pilot.press("m", "i", "d")
        await pilot.press("enter")
        await pilot.pause()

    result = sorted(load_folders(data_file), key=lambda f: f.position)
    names = [f.name for f in result]
    assert "mid" in names
    assert names.index("mid") == names.index("Alpha") + 1


# ---------------------------------------------------------------------------
# BACKLOG-21: created_at set on new tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_task_has_created_at(tmp_path: Path) -> None:
    app = GtdApp(data_file=tmp_path / "data.json")
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("B", "u", "y", " ", "m", "i", "l", "k")
        await pilot.press("enter")
        await pilot.pause()
    today = [
        t for t in app._all_tasks if t.folder_id == "today" and t.title == "Buy milk"
    ]
    assert today
    assert today[0].created_at is not None


# ---------------------------------------------------------------------------
# BACKLOG-21: Multi-line notes in detail view
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notes_support_newlines_in_detail_view(tmp_path: Path) -> None:
    data_file = _prepopulate(tmp_path, "My task")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Open detail
        await pilot.press("enter")
        await pilot.pause()
        # Skip title → date → deadline → notes
        await pilot.press("enter")  # title → date
        await pilot.pause()
        await pilot.press("enter")  # date → deadline
        await pilot.pause()
        await pilot.press("enter")  # deadline → notes
        await pilot.pause()
        # notes VimInput is now focused in COMMAND mode; enter INSERT
        await pilot.press("i")
        await pilot.pause()
        # Type two lines
        await pilot.press("L", "i", "n", "e", "1")
        await pilot.press("enter")  # inserts newline in multiline mode
        await pilot.press("L", "i", "n", "e", "2")
        await pilot.press("escape")  # COMMAND mode
        await pilot.press("escape")  # save and close
        await pilot.pause()
    task = next(t for t in app._all_tasks if t.title == "My task")
    assert "Line1" in task.notes
    assert "Line2" in task.notes
    assert "\n" in task.notes


# ---------------------------------------------------------------------------
# Yank to clipboard (y keybinding)
# ---------------------------------------------------------------------------


async def test_yank_copies_title_to_clipboard(tmp_path: Path) -> None:
    """y with no notes copies just the title."""
    from unittest.mock import patch

    data_file = _prepopulate(tmp_path, "Buy milk")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            await pilot.press("y")
            await pilot.pause()
        mock_copy.assert_called_once_with("Buy milk")


async def test_yank_copies_title_and_notes_to_clipboard(tmp_path: Path) -> None:
    """y with notes copies title + newline + notes."""
    from unittest.mock import patch

    from gtd_tui.gtd.operations import add_task

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Buy milk", notes="whole milk, 2 litres")
    save_data(tasks, [], data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            await pilot.press("y")
            await pilot.pause()
        mock_copy.assert_called_once_with("Buy milk\nwhole milk, 2 litres")


async def test_yank_shows_status_message(tmp_path: Path) -> None:
    """y shows a confirmation in the status bar."""
    from unittest.mock import patch

    data_file = _prepopulate(tmp_path, "Buy milk")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("pyperclip.copy"):
            await pilot.press("y")
            await pilot.pause()
        status = app.query_one("#status", Label)
        assert "yank" in str(status.content).lower()


async def test_yank_shows_unavailable_when_clipboard_missing(tmp_path: Path) -> None:
    """When pyperclip raises, a friendly message is shown instead of a crash."""
    from unittest.mock import patch

    import pyperclip

    data_file = _prepopulate(tmp_path, "Buy milk")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        with patch("pyperclip.copy", side_effect=pyperclip.PyperclipException):
            await pilot.press("y")
            await pilot.pause()
        status = app.query_one("#status", Label)
        assert "clipboard" in str(status.content).lower()


async def test_visual_yank_copies_all_selected_titles(tmp_path: Path) -> None:
    """y in VISUAL mode copies all selected tasks' titles, one per line."""
    from unittest.mock import patch

    data_file = _prepopulate(tmp_path, "Task A", "Task B", "Task C")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Enter VISUAL mode and extend down to select first two tasks
        await pilot.press("v")
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            await pilot.press("y")
            await pilot.pause()
        copied = mock_copy.call_args[0][0]
        assert "Task C" in copied  # first task (newest = top)
        assert "Task B" in copied
        assert "Task A" not in copied


async def test_visual_yank_includes_notes_for_tasks_with_notes(tmp_path: Path) -> None:
    """y in VISUAL mode includes notes beneath each task that has them."""
    from unittest.mock import patch

    from gtd_tui.gtd.operations import add_task

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Alpha", notes="alpha notes")
    tasks = add_task(tasks, "Beta")
    save_data(tasks, [], data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Select both tasks
        await pilot.press("v")
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            await pilot.press("y")
            await pilot.pause()
        copied = mock_copy.call_args[0][0]
        assert "Beta" in copied
        assert "Alpha" in copied
        assert "alpha notes" in copied


async def test_visual_yank_exits_visual_mode(tmp_path: Path) -> None:
    """y in VISUAL mode exits visual mode after copying."""
    from unittest.mock import patch

    data_file = _prepopulate(tmp_path, "Task A", "Task B")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("v")
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        with patch("pyperclip.copy"):
            await pilot.press("y")
            await pilot.pause()
        assert not app._visual_mode


# ---------------------------------------------------------------------------
# BACKLOG-33: Colon command dispatch (:help opens HelpScreen)
# ---------------------------------------------------------------------------


async def test_colon_help_opens_help_screen(tmp_path: Path) -> None:
    """Typing :help<Enter> via the command buffer pushes HelpScreen onto the stack."""
    from textual.widgets import Input

    from gtd_tui.app import HelpScreen

    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Enter colon-command mode
        await pilot.press("colon")
        await pilot.pause()
        assert app._input_stage == "command"
        # Type "help" and submit
        inp = app.query_one("#task-input", Input)
        inp.value = "help"
        await pilot.press("enter")
        await pilot.pause()
        assert any(isinstance(s, HelpScreen) for s in app.screen_stack)


async def test_colon_h_abbreviation_opens_help_screen(tmp_path: Path) -> None:
    """:h is the short form of :help and also opens HelpScreen."""
    from textual.widgets import Input

    from gtd_tui.app import HelpScreen

    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("colon")
        await pilot.pause()
        inp = app.query_one("#task-input", Input)
        inp.value = "h"
        await pilot.press("enter")
        await pilot.pause()
        assert any(isinstance(s, HelpScreen) for s in app.screen_stack)


# ---------------------------------------------------------------------------
# BACKLOG-33: m key in NORMAL mode moves a single task to another folder
# ---------------------------------------------------------------------------


async def test_m_key_normal_mode_moves_task_to_folder(tmp_path: Path) -> None:
    """Pressing m in NORMAL mode, navigating to a folder, then Enter moves the task."""
    data_file = tmp_path / "data.json"
    # Start with a task in Today (default)
    tasks = add_task([], "Move me")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # NORMAL mode, task selected: press m to start single-task move
        await pilot.press("m")
        await pilot.pause()
        assert app._move_mode is True
        # Sidebar is now focused at the current view (today, index 1).
        # Navigate j j j → index 4 = someday, then confirm.
        await pilot.press("j", "j", "j")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        # Task should now be in someday
        someday_tasks = [t for t in app._all_tasks if t.folder_id == "someday"]
        assert any(t.title == "Move me" for t in someday_tasks)
        assert app._current_view == "someday"
        assert not app._move_mode


# ---------------------------------------------------------------------------
# BACKLOG-33: spawn_repeating_tasks fires on launch (on_mount integration)
# ---------------------------------------------------------------------------


async def test_spawn_repeating_tasks_fires_on_launch(tmp_path: Path) -> None:
    """Tasks with a past-due repeat rule get a Today copy spawned on app launch."""
    from datetime import date, timedelta

    from gtd_tui.gtd.operations import set_repeat_rule
    from gtd_tui.gtd.task import RepeatRule

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Daily standup")
    # Make the repeat rule's next_due be yesterday so it fires today
    yesterday = date.today() - timedelta(days=1)
    rule = RepeatRule(interval=1, unit="days", next_due=yesterday)
    tasks = set_repeat_rule(tasks, tasks[0].id, rule)
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # on_mount should have spawned a Today copy (no repeat_rule on the copy)
        today_copies = [
            t
            for t in app._all_tasks
            if t.title == "Daily standup"
            and t.folder_id == "today"
            and t.repeat_rule is None
        ]
        assert len(today_copies) == 1


# ---------------------------------------------------------------------------
# BACKLOG-34: Unified Today view reordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_J_moves_today_home_task_down(tmp_path: Path) -> None:
    """J swaps a today-home task with the one below it via today_position."""

    data_file = tmp_path / "data.json"
    tasks = add_task([], "A")
    tasks = add_task(tasks, "B")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # After mount, today_positions are assigned; B is at top (position 0), A below
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 0  # select B (top)
        await pilot.pause()
        await pilot.press("J")
        await pilot.pause()
        from gtd_tui.gtd.operations import today_tasks

        ordered = today_tasks(app._all_tasks)
        assert ordered[0].title == "A"
        assert ordered[1].title == "B"


@pytest.mark.asyncio
async def test_K_moves_today_home_task_up(tmp_path: Path) -> None:
    """K swaps a today-home task with the one above it via today_position."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "A")
    tasks = add_task(tasks, "B")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        # B is at index 0 (top), A is at index 1
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 1  # select A (bottom)
        await pilot.pause()
        await pilot.press("K")
        await pilot.pause()
        from gtd_tui.gtd.operations import today_tasks

        ordered = today_tasks(app._all_tasks)
        assert ordered[0].title == "A"
        assert ordered[1].title == "B"


@pytest.mark.asyncio
async def test_J_moves_dated_other_task_in_today(tmp_path: Path) -> None:
    """J works on a dated_other task (from a non-today folder) in Today view."""
    from datetime import date

    from gtd_tui.gtd.task import Task as GtdTask

    data_file = tmp_path / "data.json"
    # Create a today-home task and a work-folder task scheduled for today
    tasks = add_task([], "Home task")
    work_task = GtdTask(
        title="Work task",
        folder_id="work",
        scheduled_date=date.today(),
        position=0,
    )
    tasks.append(work_task)
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        from gtd_tui.gtd.operations import today_tasks

        before = today_tasks(app._all_tasks)
        # Select the first task and move it down
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 0
        await pilot.pause()
        first_id = before[0].id
        await pilot.press("J")
        await pilot.pause()
        after = today_tasks(app._all_tasks)
        # The first task should now be at index 1
        assert after[1].id == first_id


@pytest.mark.asyncio
async def test_yank_paste_repositions_task_in_today(tmp_path: Path) -> None:
    """y then p (paste after) repositions the yanked task in Today view."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "C")
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        from gtd_tui.gtd.operations import today_tasks

        # Order after mount: A(0), B(1), C(2)
        ordered = today_tasks(app._all_tasks)
        assert [t.title for t in ordered] == ["A", "B", "C"]

        list_view = app.query_one("#task-list", ListView)
        # Yank A (index 0)
        list_view.index = 0
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        assert app._today_register == ordered[0].id

        # Move cursor to C (index 2) and paste A after it
        list_view.index = 2
        await pilot.pause()
        await pilot.press("p")
        await pilot.pause()
        result = today_tasks(app._all_tasks)
        assert [t.title for t in result] == ["B", "C", "A"]


@pytest.mark.asyncio
async def test_yank_paste_before_repositions_task_in_today(tmp_path: Path) -> None:
    """y then P (paste before) repositions the yanked task in Today view."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "C")
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        from gtd_tui.gtd.operations import today_tasks

        ordered = today_tasks(app._all_tasks)
        assert [t.title for t in ordered] == ["A", "B", "C"]

        list_view = app.query_one("#task-list", ListView)
        # Yank C (index 2)
        list_view.index = 2
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()
        c_id = ordered[2].id
        assert app._today_register == c_id

        # Move cursor to A (index 0) and paste C before it
        list_view.index = 0
        await pilot.pause()
        await pilot.press("P")
        await pilot.pause()
        result = today_tasks(app._all_tasks)
        assert [t.title for t in result] == ["C", "A", "B"]


@pytest.mark.asyncio
async def test_today_register_cleared_on_view_change(tmp_path: Path) -> None:
    """Navigating away from Today view clears the _today_register."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task")
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        list_view = app.query_one("#task-list", ListView)
        list_view.index = 0
        await pilot.pause()
        # Yank to populate register
        await pilot.press("y")
        await pilot.pause()
        assert app._today_register is not None
        # Navigate to Inbox (sidebar index 0)
        sidebar = app.query_one("#sidebar", ListView)
        sidebar.index = 0
        await pilot.pause()
        assert app._today_register is None
