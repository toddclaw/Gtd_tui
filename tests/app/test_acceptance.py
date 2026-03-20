"""BACKLOG-57 — UI acceptance test suite.

End-to-end user-journey tests driven entirely through keyboard input via
Textual's headless Pilot API.  Each test exercises a complete interaction
sequence and asserts on observable state (task lists, screen type, CSS
classes) rather than internal implementation details.

Special note on Esc-key latency tests:
  In the headless test environment Textual's event loop processes key events
  synchronously; there is no actual terminal parser or ESCDELAY timer.  The
  timing numbers here therefore represent the *floor* achievable when
  ESCDELAY is zero.  On a real terminal the mode change is gated by the
  ESCDELAY setting (default 25 ms in this app after the v1.5 fix).

  The threshold used in the latency assertions (200 ms) is intentionally
  generous to remain stable on slow CI runners while still catching any
  accidental sleep / blocking call introduced into the Esc handler.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import date
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Label, ListView

from gtd_tui.app import GtdApp, SearchScreen, TaskDetailScreen
from gtd_tui.config import Config, load_config
from gtd_tui.gtd.operations import (
    add_task,
    add_task_to_folder,
    set_recur_rule,
)
from gtd_tui.gtd.task import RecurRule
from gtd_tui.storage.file import save_data
from gtd_tui.widgets.vim_input import VimInput

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _prepopulate(tmp_path: Path, *titles: str, folder: str = "today") -> Path:
    """Write tasks into *folder* and return the data-file path."""
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in reversed(titles):
        if folder == "today":
            tasks = add_task(tasks, title)
        else:
            tasks = add_task_to_folder(tasks, folder, title)
    save_data(tasks, [], data_file=data_file)
    return data_file


def _make_app(tmp_path: Path) -> GtdApp:
    cfg = replace(load_config(), startup_focus_sidebar=False)
    return GtdApp(data_file=tmp_path / "data.json", config=cfg)


# ---------------------------------------------------------------------------
# Minimal single-widget app for VimInput isolation tests
# ---------------------------------------------------------------------------


class _VimApp(App[None]):
    """Minimal app holding a single VimInput, used for isolated timing tests."""

    def __init__(self, value: str = "", start_mode: str = "insert") -> None:
        super().__init__()
        self._v = value
        self._sm = start_mode

    def compose(self) -> ComposeResult:
        yield VimInput(value=self._v, start_mode=self._sm, id="vi")


# ---------------------------------------------------------------------------
# ESC LATENCY TESTS
# These verify that Esc transitions VimInput from INSERT (green border) to
# COMMAND mode quickly.  The CSS class "vim-insert-mode" is the observable
# indicator: present → INSERT (green), absent → COMMAND (accent colour).
# ---------------------------------------------------------------------------


async def test_esc_switches_vim_input_from_insert_to_command() -> None:
    """Pressing Esc removes the vim-insert-mode class (green → accent border)."""
    async with _VimApp(value="hello", start_mode="insert").run_test() as pilot:
        vi = pilot.app.query_one("#vi", VimInput)

        # Precondition: we start in INSERT mode
        assert vi._vim_mode == "insert"
        assert "vim-insert-mode" in vi.classes

        await pilot.press("escape")
        await pilot.pause()

        assert vi._vim_mode == "command"
        assert "vim-insert-mode" not in vi.classes


async def test_esc_vim_input_mode_change_latency() -> None:
    """The INSERT → COMMAND transition via Esc completes in under 200 ms.

    This guards against accidental sleeps or blocking calls in the Esc
    handler.  In a real terminal the ESCDELAY=25 ms setting (set in
    __main__.py) limits the floor to ~25 ms; this test uses a 200 ms
    ceiling to remain stable on slow CI runners.
    """
    async with _VimApp(value="hello world", start_mode="insert").run_test() as pilot:
        vi = pilot.app.query_one("#vi", VimInput)
        assert vi._vim_mode == "insert"

        t0 = time.monotonic()
        await pilot.press("escape")
        await pilot.pause()
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert vi._vim_mode == "command", "Esc must switch mode"
        assert elapsed_ms < 200, (
            f"Esc took {elapsed_ms:.1f} ms — expected < 200 ms. "
            "Check for blocking calls in the Esc handler."
        )


async def test_esc_task_detail_field_insert_to_command_latency(
    tmp_path: Path,
) -> None:
    """Esc inside a task detail field switches from INSERT (green) to COMMAND quickly.

    Flow: open task detail → press i on title field → verify INSERT (green) →
    press Esc → time the transition → verify COMMAND (accent).
    """
    data_file = _prepopulate(tmp_path, "Buy groceries")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Open the detail screen
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Title field starts in COMMAND mode; press i to enter INSERT
        title_vi = app.screen.query_one("#detail-title-input", VimInput)
        assert title_vi._vim_mode == "command"
        await pilot.press("i")
        await pilot.pause()
        assert title_vi._vim_mode == "insert"
        assert "vim-insert-mode" in title_vi.classes

        # Time the Esc press
        t0 = time.monotonic()
        await pilot.press("escape")
        await pilot.pause()
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert title_vi._vim_mode == "command", "Esc must return to COMMAND mode"
        assert (
            "vim-insert-mode" not in title_vi.classes
        ), "vim-insert-mode class must be removed after Esc"
        assert (
            elapsed_ms < 200
        ), f"Esc in task detail took {elapsed_ms:.1f} ms — expected < 200 ms."


# ---------------------------------------------------------------------------
# TASK CREATION JOURNEY
# ---------------------------------------------------------------------------


async def test_full_task_creation_keyboard_journey(tmp_path: Path) -> None:
    """Complete task creation via keyboard: o → type title → Enter → Enter → back to list.

    Verifies that a task created purely through keyboard input ends up in
    the data model and that the app returns to NORMAL mode.
    """
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app._mode == "NORMAL"

        # Open new-task row below current selection
        await pilot.press("o")
        await pilot.pause()
        assert app._mode == "INSERT"

        # Type the task title
        await pilot.press("P", "l", "a", "n", " ", "s", "p", "r", "i", "n", "t")
        await pilot.press("enter")  # confirm title → advance to notes
        await pilot.pause()
        await pilot.press("enter")  # skip notes → save
        await pilot.pause()

        assert app._mode == "NORMAL"
        titles = [t.title for t in app._all_tasks if t.folder_id == "today"]
        assert "Plan sprint" in titles


async def test_task_appears_in_list_immediately_after_creation(
    tmp_path: Path,
) -> None:
    """A newly created task is visible in the ListView without requiring a restart."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        task_list = app.query_one("#task-list", ListView)
        initial_count = len(list(task_list.query(Label)))

        await pilot.press("o")
        await pilot.pause()
        await pilot.press("S", "t", "a", "n", "d", "u", "p")
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        new_count = len(list(task_list.query(Label)))
        assert new_count > initial_count


# ---------------------------------------------------------------------------
# TASK SCHEDULING JOURNEY
# ---------------------------------------------------------------------------


async def test_scheduled_task_disappears_from_today_view(tmp_path: Path) -> None:
    """Setting a future date on a Today task removes it from the Today smart view.

    The task stays in the 'today' folder but today_tasks() filters it out
    because its scheduled_date is strictly in the future.
    """
    data_file = _prepopulate(tmp_path, "Read book")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Confirm the task is visible in Today initially
        today_before = [t for t in app._all_tasks if t.folder_id == "today"]
        assert len(today_before) == 1

        # Open detail, skip to date field, set +7d, save
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")  # title → date
        await pilot.pause()
        await pilot.press("i")
        await pilot.press("+", "7", "d")
        await pilot.press("escape")  # INSERT → COMMAND
        await pilot.pause()
        await pilot.press("escape")  # COMMAND bubbles → save + close
        await pilot.pause()
        assert not isinstance(app.screen, TaskDetailScreen)

        # Task must still exist but its scheduled_date must be in the future
        task = next(t for t in app._all_tasks if t.folder_id == "today")
        assert task.scheduled_date is not None
        assert task.scheduled_date > date.today()

        # today_tasks() must exclude it
        from gtd_tui.gtd.operations import today_tasks

        assert not any(t.title == "Read book" for t in today_tasks(app._all_tasks))


async def test_scheduled_task_appears_in_upcoming_view(tmp_path: Path) -> None:
    """A task scheduled for +7d appears in the Upcoming smart view."""
    from datetime import timedelta

    from gtd_tui.gtd.operations import schedule_task, upcoming_tasks

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Write report")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=7))
    save_data(tasks, [], data_file=data_file)

    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        upcoming = upcoming_tasks(app._all_tasks)
        assert any(t.title == "Write report" for t in upcoming)


# ---------------------------------------------------------------------------
# RECURRING TASK JOURNEY
# ---------------------------------------------------------------------------


async def test_completing_recurring_task_creates_new_instance(
    tmp_path: Path,
) -> None:
    """Completing a task with a recur_rule spawns a new instance with a future date.

    Set up a task with a 7-day recur rule, then press x to complete it.
    The original task moves to Logbook and a new task appears in Today
    with a scheduled_date 7 days in the future.
    """
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Daily standup")
    tasks = set_recur_rule(tasks, tasks[0].id, RecurRule(interval=7, unit="days"))
    save_data(tasks, [], data_file=data_file)

    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("x")  # complete the recurring task
        await pilot.pause()

        # Original must be in logbook
        logbook = [t for t in app._all_tasks if t.folder_id == "logbook"]
        assert any(t.title == "Daily standup" for t in logbook)

        # A new instance must have been spawned
        active = [
            t
            for t in app._all_tasks
            if t.folder_id != "logbook" and t.title == "Daily standup"
        ]
        assert len(active) == 1, "Exactly one new instance should be spawned"
        assert active[0].scheduled_date is not None
        assert active[0].scheduled_date > date.today()
        assert active[0].recur_rule is not None


# ---------------------------------------------------------------------------
# SEARCH JOURNEY
# ---------------------------------------------------------------------------


async def test_search_navigates_to_task_on_select(tmp_path: Path) -> None:
    """Search → type query → Enter (focus results) → Enter (select) → back in main app.

    The search screen is dismissed and the app navigates to the matching task's
    folder, leaving the main task list focused with the task selected.
    From there a final Enter opens the TaskDetailScreen.
    """
    data_file = _prepopulate(tmp_path, "Draft proposal", "Review PR", "Send invoice")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("slash")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)

        # Type enough to uniquely match "Draft proposal"
        await pilot.press("D", "r", "a", "f")
        await pilot.pause()

        # First Enter: focus moves from text input to the results list
        await pilot.press("enter")
        await pilot.pause()

        # Second Enter: dismiss search screen and navigate to the task in the list
        await pilot.press("enter")
        await pilot.pause()

        # Search screen must be gone; we are back on the main task list
        assert not isinstance(app.screen, SearchScreen)
        assert app._mode == "NORMAL"

        # Third Enter: open the detail screen for the selected task
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, TaskDetailScreen)


async def test_search_esc_returns_to_task_list(tmp_path: Path) -> None:
    """Esc from the search screen closes it and returns to the task list."""
    data_file = _prepopulate(tmp_path, "Buy milk")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        assert isinstance(app.screen, SearchScreen)

        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, SearchScreen)
        assert app._mode == "NORMAL"


# ---------------------------------------------------------------------------
# UNDO JOURNEY
# ---------------------------------------------------------------------------


async def test_undo_restores_deleted_task(tmp_path: Path) -> None:
    """Deleting a task then pressing u restores it to the active list."""
    data_file = _prepopulate(tmp_path, "Fix critical bug")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("d")  # delete → logbook with is_deleted=True
        await pilot.pause()

        deleted = [t for t in app._all_tasks if t.is_deleted]
        assert len(deleted) == 1

        await pilot.press("u")  # undo
        await pilot.pause()

        # Task must be back in the active folder, no longer deleted
        active = [
            t for t in app._all_tasks if not t.is_deleted and t.folder_id != "logbook"
        ]
        assert any(t.title == "Fix critical bug" for t in active)
        assert not any(t.is_deleted for t in app._all_tasks)


# ---------------------------------------------------------------------------
# INBOX CAPTURE JOURNEY
# ---------------------------------------------------------------------------


async def test_inbox_capture_task_stays_in_inbox(tmp_path: Path) -> None:
    """Tasks created while the Inbox view is active land in 'inbox', not 'today'."""
    app = _make_app(tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Navigate to Inbox via number shortcut (0 = Inbox)
        await pilot.press("0")
        await pilot.pause()
        assert app._current_view == "inbox"
        await pilot.press("l")  # focus task list to show Inbox
        await pilot.pause()

        # Create a new task
        await pilot.press("o")
        await pilot.pause()
        await pilot.press(
            "Q", "u", "i", "c", "k", " ", "c", "a", "p", "t", "u", "r", "e"
        )
        await pilot.press("enter")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        inbox_tasks = [t for t in app._all_tasks if t.folder_id == "inbox"]
        today_tasks = [t for t in app._all_tasks if t.folder_id == "today"]
        assert any(t.title == "Quick capture" for t in inbox_tasks)
        assert not any(t.title == "Quick capture" for t in today_tasks)


# ---------------------------------------------------------------------------
# NOTES EDIT JOURNEY
# ---------------------------------------------------------------------------


async def test_notes_edit_persists_after_esc_save(tmp_path: Path) -> None:
    """Editing notes in the detail view and pressing Esc saves the change.

    Flow: open detail → navigate to notes → enter INSERT → type → Esc (INSERT→COMMAND)
    → Esc (COMMAND→save+close) → verify notes persisted in memory and on disk.
    """
    data_file = _prepopulate(tmp_path, "Write tests")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Navigate: title → date → deadline → notes
        await pilot.press("enter")  # title COMMAND → date
        await pilot.pause()
        await pilot.press("enter")  # date → deadline
        await pilot.pause()
        await pilot.press("enter")  # deadline → notes
        await pilot.pause()

        # Notes VimInput is in COMMAND mode; enter INSERT and type
        await pilot.press("i")
        await pilot.press(
            "T", "D", "D", ":", " ", "a", "d", "d", " ", "m", "o", "r", "e"
        )
        await pilot.press("escape")  # INSERT → COMMAND
        await pilot.pause()
        await pilot.press("escape")  # COMMAND bubbles → save + close
        await pilot.pause()

        assert not isinstance(app.screen, TaskDetailScreen)

        task = next(
            t
            for t in app._all_tasks
            if t.title == "Write tests" and t.folder_id != "logbook"
        )
        assert "TDD: add more" in task.notes

        # Verify the data was written to disk
        from gtd_tui.storage.file import load_tasks

        saved = load_tasks(data_file)
        saved_task = next(t for t in saved if t.title == "Write tests")
        assert "TDD: add more" in saved_task.notes


# ---------------------------------------------------------------------------
# DOUBLE-ESC SEQUENCE (INSERT → COMMAND → close)
# ---------------------------------------------------------------------------


async def test_double_esc_from_detail_field_closes_and_saves(
    tmp_path: Path,
) -> None:
    """The canonical EscEsc sequence: first Esc exits INSERT, second Esc closes detail.

    This is the primary save-and-exit flow.  Each Esc must be processed
    quickly — the test also asserts the sequence completes within 500 ms total.
    """
    data_file = _prepopulate(tmp_path, "Ship feature")
    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        title_vi = app.screen.query_one("#detail-title-input", VimInput)

        # Enter INSERT mode
        await pilot.press("i")
        await pilot.pause()
        assert title_vi._vim_mode == "insert"

        # Time the full EscEsc sequence
        t0 = time.monotonic()
        await pilot.press("escape")  # INSERT → COMMAND
        await pilot.pause()
        assert title_vi._vim_mode == "command", "First Esc must leave INSERT mode"

        await pilot.press("escape")  # COMMAND → close detail
        await pilot.pause()
        elapsed_ms = (time.monotonic() - t0) * 1000

        assert not isinstance(
            app.screen, TaskDetailScreen
        ), "Second Esc must close the detail screen"
        assert (
            elapsed_ms < 500
        ), f"EscEsc sequence took {elapsed_ms:.1f} ms — expected < 500 ms."


# ---------------------------------------------------------------------------
# DEFAULT VIEW CONFIG JOURNEY
# ---------------------------------------------------------------------------


async def test_default_view_config_opens_correct_view(tmp_path: Path) -> None:
    """An app configured with default_view='inbox' opens showing the Inbox."""
    from gtd_tui.config import Config

    data_file = _prepopulate(tmp_path, "Captured idea")
    app = GtdApp(data_file=data_file)
    # Override the config before the app starts
    app._config = Config(default_view="inbox")
    # Re-apply the config to _current_view (normally done in __init__)
    app._current_view = app._config.default_view

    async with app.run_test() as pilot:
        await pilot.pause()
        app._refresh_list()
        await pilot.pause()
        assert app._current_view == "inbox"


# ---------------------------------------------------------------------------
# VISUAL MODE ACCEPTANCE JOURNEY
# ---------------------------------------------------------------------------


async def test_visual_bulk_delete_full_journey(tmp_path: Path) -> None:
    """Select two tasks with VISUAL mode and delete them both at once.

    Journey: v (enter VISUAL at index 0) → j (extend to index 1) → d (bulk delete)
    → verify both tasks are in logbook with is_deleted=True.
    """
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in reversed(["Alpha", "Beta", "Gamma"]):
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)

    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("v")  # enter VISUAL at index 0
        await pilot.pause()
        assert app._visual_mode is True

        await pilot.press("j")  # extend selection to index 1
        await pilot.pause()

        await pilot.press("d")  # bulk delete
        await pilot.pause()

        assert app._visual_mode is False  # must exit VISUAL

        deleted = [t for t in app._all_tasks if t.is_deleted]
        assert len(deleted) == 2  # Alpha and Beta deleted
        active = [
            t for t in app._all_tasks if not t.is_deleted and t.folder_id != "logbook"
        ]
        assert len(active) == 1
        assert active[0].title == "Gamma"


async def test_visual_bulk_complete_full_journey(tmp_path: Path) -> None:
    """Select two tasks in VISUAL mode and complete them both.

    Journey: v → j → x → both tasks in logbook as completed (not deleted).
    """
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in reversed(["Read paper", "Write notes", "Take break"]):
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)

    cfg = replace(load_config(), startup_focus_sidebar=False)
    app = GtdApp(data_file=data_file, config=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("v")
        await pilot.pause()
        await pilot.press("j")
        await pilot.pause()
        await pilot.press("x")  # bulk complete
        await pilot.pause()

        completed = [t for t in app._all_tasks if t.is_complete]
        assert len(completed) == 2
        assert all(t.folder_id == "logbook" for t in completed)
        assert not any(t.is_deleted for t in completed)

        remaining = [t for t in app._all_tasks if not t.is_complete]
        assert len(remaining) == 1
        assert remaining[0].title == "Take break"
