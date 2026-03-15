from __future__ import annotations

import copy
import uuid
from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from gtd_tui.gtd.dates import InvalidDateError, parse_date_input
from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, Folder
from gtd_tui.gtd.operations import (
    add_task,
    add_task_to_folder,
    add_waiting_on_task,
    complete_task,
    delete_task,
    create_folder,
    delete_folder,
    discard_folder_tasks,
    edit_task,
    folder_tasks,
    insert_task_after,
    insert_task_before,
    InvalidRepeatError,
    logbook_tasks,
    make_repeat_rule,
    move_folder_tasks_to_today,
    move_task_down,
    move_task_to_folder,
    move_task_up,
    move_to_today,
    move_to_waiting_on,
    parse_repeat_input,
    rename_folder,
    schedule_task,
    search_tasks,
    set_recur_rule,
    set_repeat_rule,
    someday_tasks,
    spawn_repeating_tasks,
    today_tasks,
    unschedule_task,
    upcoming_tasks,
    waiting_on_tasks,
)
from gtd_tui.gtd.task import RecurRule, RepeatRule
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import load_folders, load_tasks, save_data


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-panel {
        width: 64;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    """

    _HELP_TEXT = """\
[bold]Navigation[/bold]
  j / k        Move cursor down / up
  g g          Jump to top of list
  G            Jump to bottom of list
  h / l        Focus sidebar / task list
  1–9          Jump to nth sidebar item

[bold]Task Actions[/bold]
  Enter        Open task detail / edit (title, notes, repeat, recurring)
  o            Add new task after selected (INSERT mode)
  O            Add new task before selected (INSERT mode)
  x / Space    Complete selected task
  s            Schedule selected task
  m            Move selected task to a folder (sidebar picker)
  J / K        Move selected task down / up
  w            Move selected task to Waiting On  (Today view)
  t            Move selected task to Today       (Waiting On view)
  u            Undo last action
  Ctrl+R       Redo last undone action
  /            Global search (Esc to cancel, Enter to go to task)

[bold]Sidebar Folder Actions[/bold]
  N            Create new folder
  r            Rename selected folder
  d            Delete selected folder

[bold]INSERT Mode[/bold]
  Enter        Confirm input / advance to next field
  Esc          Cancel and return to NORMAL mode

[bold]Commands  (type : then the command)[/bold]
  :help        Show this help screen

[bold]General[/bold]
  q            Quit

  Press Esc, Enter, or q to close\
"""

    def compose(self) -> ComposeResult:
        yield Static(self._HELP_TEXT, id="help-panel")

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "enter"):
            self.dismiss()


class TaskDetailScreen(ModalScreen[tuple[str, str, str, str] | None]):
    """Detail and edit view for a single task.

    Opens directly in edit mode with inputs pre-filled.
    Enter on each field advances to the next; Enter on Recurring saves and closes.
    Esc always saves and closes (priority binding fires before any widget).

    Dismissed value: (title, notes, repeat_text, recur_text) or None if title
    was cleared.  repeat_text / recur_text are raw strings (e.g. '7 days',
    empty = clear).  If both are non-empty, repeat takes precedence.
    """

    BINDINGS = [
        Binding("escape", "save_and_close", show=False, priority=True),
    ]

    CSS = """
    TaskDetailScreen {
        align: center middle;
    }

    #detail-panel {
        width: 70;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #detail-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .field-label {
        color: $text-muted;
        margin-bottom: 0;
    }

    #detail-title-input {
        margin-bottom: 1;
    }

    #detail-notes-input {
        margin-bottom: 1;
    }

    #detail-status {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, task: Task) -> None:
        super().__init__()
        self._gtd_task = task

    @staticmethod
    def _interval_to_str(interval: int, unit: str) -> str:
        display_unit = unit if interval != 1 else unit.rstrip("s")
        return f"{interval} {display_unit}"

    def compose(self) -> ComposeResult:
        repeat_val = (
            self._interval_to_str(self._gtd_task.repeat_rule.interval, self._gtd_task.repeat_rule.unit)
            if self._gtd_task.repeat_rule else ""
        )
        recur_val = (
            self._interval_to_str(self._gtd_task.recur_rule.interval, self._gtd_task.recur_rule.unit)
            if self._gtd_task.recur_rule else ""
        )
        with Vertical(id="detail-panel"):
            yield Label("Edit Task", id="detail-header")
            yield Label("Title", classes="field-label")
            yield Input(value=self._gtd_task.title, id="detail-title-input")
            yield Label("Notes", classes="field-label")
            yield Input(
                value=self._gtd_task.notes,
                placeholder="(optional)",
                id="detail-notes-input",
            )
            yield Label(
                "Repeat  (calendar-fixed — e.g. 7 days, 2 weeks — empty to clear)",
                classes="field-label",
            )
            yield Input(value=repeat_val, placeholder="(none)", id="detail-repeat-input")
            yield Label(
                "Recurring  (after completion — e.g. 1 day, 3 weeks — empty to clear)",
                classes="field-label",
            )
            yield Input(value=recur_val, placeholder="(none)", id="detail-recur-input")
            yield Label("Enter: next field  Esc: save & close", id="detail-status")

    def on_mount(self) -> None:
        self.query_one("#detail-title-input", Input).focus()

    def action_save_and_close(self) -> None:
        title = self.query_one("#detail-title-input", Input).value.strip()
        notes = self.query_one("#detail-notes-input", Input).value.strip()
        repeat = self.query_one("#detail-repeat-input", Input).value.strip()
        recur = self.query_one("#detail-recur-input", Input).value.strip()
        self.dismiss((title, notes, repeat, recur) if title else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in (
            "detail-title-input",
            "detail-notes-input",
            "detail-repeat-input",
        ):
            self.focus_next()
        elif event.input.id == "detail-recur-input":
            self.action_save_and_close()


class SearchScreen(ModalScreen[str | None]):
    """Global search across all tasks.

    Dismissed value: task_id of the selected task, or None if cancelled.
    """

    BINDINGS = [
        Binding("escape", "cancel", show=False, priority=True),
        Binding("up", "cursor_up", show=False, priority=True),
        Binding("down", "cursor_down", show=False, priority=True),
        Binding("enter", "select", show=False, priority=True),
    ]

    CSS = """
    SearchScreen {
        align: center middle;
    }

    #search-panel {
        width: 72;
        height: 28;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #search-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #search-input {
        margin-bottom: 1;
    }

    #search-results {
        height: 1fr;
    }

    #search-status {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, tasks: list[Task]) -> None:
        super().__init__()
        self._tasks = tasks
        # list of (task_id, display_label, is_separator)
        self._result_entries: list[tuple[str, str, bool]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="search-panel"):
            yield Label("Search", id="search-header")
            yield Input(placeholder="Type to search...", id="search-input")
            yield ListView(id="search-results")
            yield Label("↑/↓ navigate   Enter: go to task   Esc: cancel", id="search-status")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._run_search(event.value)

    def _run_search(self, query: str) -> None:
        results = search_tasks(self._tasks, query)
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        self._result_entries = []

        if not results:
            return

        active_results = [(t, mt) for t, mt in results if t.folder_id != "logbook"]
        logbook_results = [(t, mt) for t, mt in results if t.folder_id == "logbook"]

        def _highlight(text: str, query: str) -> str:
            from rich.markup import escape as rich_escape
            q_lower = query.lower()
            idx = text.lower().find(q_lower)
            if idx == -1:
                return rich_escape(text)
            before = rich_escape(text[:idx])
            match = rich_escape(text[idx : idx + len(query)])
            after = rich_escape(text[idx + len(query) :])
            return f"{before}[bold yellow]{match}[/bold yellow]{after}"

        def _folder_tag(task: Task) -> str:
            folder_map = {
                "today": "Today",
                "waiting_on": "WO",
                "someday": "Someday",
                "upcoming": "Upcoming",
            }
            return folder_map.get(task.folder_id, task.folder_id[:8])

        for task, match_type in active_results:
            tag = _folder_tag(task)
            if match_type == "notes":
                label_text = f"[{tag}] {_highlight(task.title, query)}  [dim](notes)[/dim]"
            else:
                label_text = f"[{tag}] {_highlight(task.title, query)}"
            self._result_entries.append((task.id, task.title, False))
            list_view.append(ListItem(Label(label_text)))

        if active_results and logbook_results:
            self._result_entries.append(("", "", True))
            list_view.append(ListItem(Label("── Logbook ──")))

        for task, match_type in logbook_results:
            if match_type == "notes":
                label_text = f"[Logbook] {_highlight(task.title, query)}  [dim](notes)[/dim]"
            else:
                label_text = f"[Logbook] {_highlight(task.title, query)}"
            self._result_entries.append((task.id, task.title, False))
            list_view.append(ListItem(Label(label_text)))

        if self._result_entries:
            self.call_after_refresh(self._select_first)

    def _select_first(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        for i, (_, _, is_sep) in enumerate(self._result_entries):
            if not is_sep:
                list_view.index = i
                return

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        idx = list_view.index
        if idx is None:
            return
        for i in range(idx - 1, -1, -1):
            if not self._result_entries[i][2]:
                list_view.index = i
                return

    def action_cursor_down(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        idx = list_view.index
        if idx is None:
            self._select_first()
            return
        for i in range(idx + 1, len(self._result_entries)):
            if not self._result_entries[i][2]:
                list_view.index = i
                return

    def action_select(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        idx = list_view.index
        if idx is None or idx >= len(self._result_entries):
            return
        task_id, _, is_sep = self._result_entries[idx]
        if is_sep:
            return
        self.dismiss(task_id)


class GtdApp(App[None]):
    CSS = """
    Screen {
        background: $surface;
    }

    #header {
        height: 1;
        background: $primary-darken-1;
        color: $text;
        padding: 0 2;
        text-style: bold;
    }

    #main-area {
        height: 1fr;
    }

    #sidebar {
        width: 18;
        border-right: solid $panel;
    }

    #content {
        width: 1fr;
    }

    #task-input {
        margin: 0 1;
        display: none;
    }

    #task-input.active {
        display: block;
    }

    #task-list {
        height: 1fr;
        margin: 0 1;
    }

    #empty-hint {
        color: $text-muted;
        margin: 1 2;
    }

    #empty-hint.hidden {
        display: none;
    }

    #status {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 2;
    }
    """

    def __init__(self, data_file: Path | None = None) -> None:
        super().__init__()
        self._data_file: Path | None = data_file
        self._all_tasks: list[Task] = load_tasks(data_file)
        self._all_folders: list[Folder] = load_folders(data_file)
        self._mode: str = "NORMAL"
        self._input_stage: str = (
            ""  # "title", "notes", "date", "command", "folder_name", "folder_rename"
        )
        self._pending_title: str = ""
        self._pending_task_id: str = ""
        self._current_view: str = "today"
        # Parallel to ListView children: Task for rows, None for separators/placeholders
        self._list_entries: list[Task | None] = []
        self._undo_stack: list[list[Task]] = []
        self._redo_stack: list[list[Task]] = []
        self._pending_anchor_id: str = ""
        self._pending_insert_position: str = "after"  # "after" or "before"
        # Placeholder row shown in the list while a new task is being typed
        self._show_placeholder: bool = False
        self._placeholder_list_idx: int | None = None
        # Tracks the first key of a chord (e.g. "g" waiting for "gg")
        self._pending_key: str = ""
        # Sidebar rebuild guard — prevents on_list_view_highlighted from switching views
        self._rebuilding_sidebar: bool = False
        # Move-task-to-folder mode
        self._move_mode: bool = False
        # Delete folder confirmation: non-empty ID means waiting for d/m/Esc
        self._delete_confirm_folder_id: str = ""
        # Rename folder in progress
        self._rename_folder_id: str = ""

    @property
    def _sidebar_view_ids(self) -> list[str]:
        return (
            ["today", "upcoming", "waiting_on"]
            + [f.id for f in sorted(self._all_folders, key=lambda f: f.position)]
            + ["someday", "logbook"]
        )

    def _view_label(self, view_id: str) -> str:
        if view_id == "today":
            return "Today"
        if view_id == "upcoming":
            return "Upcoming"
        if view_id == "waiting_on":
            return "Waiting On"
        if view_id == "someday":
            return "Someday"
        if view_id == "logbook":
            return "Logbook"
        for folder in self._all_folders:
            if folder.id == view_id:
                return folder.name
        return view_id

    def compose(self) -> ComposeResult:
        yield Label("Today", id="header")
        with Horizontal(id="main-area"):
            yield ListView(id="sidebar")
            with Vertical(id="content"):
                yield Input(placeholder="Task title...", id="task-input")
                yield ListView(id="task-list")
                yield Label("No tasks — press o to add one", id="empty-hint")
        yield Label("NORMAL  |  Today", id="status")

    def on_mount(self) -> None:
        self._normalize_folder_positions()
        old_len = len(self._all_tasks)
        self._all_tasks = spawn_repeating_tasks(self._all_tasks)
        if len(self._all_tasks) != old_len:
            self._save()
        self._rebuild_sidebar()
        self._refresh_list()
        self.query_one("#task-list", ListView).focus()

    def _normalize_folder_positions(self) -> None:
        """Ensure every folder's tasks have unique, sequential positions.

        Fixes tasks saved by older versions of the app that always wrote
        position=0 for Waiting On tasks, which makes J/K swapping a no-op.
        """
        from collections import defaultdict

        by_folder: dict[str, list[Task]] = defaultdict(list)
        for task in self._all_tasks:
            by_folder[task.folder_id].append(task)
        needs_save = False
        for folder_tasks_list in by_folder.values():
            folder_tasks_list.sort(key=lambda t: t.position)
            positions = [t.position for t in folder_tasks_list]
            if positions != list(range(len(positions))):
                for i, task in enumerate(folder_tasks_list):
                    task.position = i
                needs_save = True
        if needs_save:
            self._save()

    # ------------------------------------------------------------------ #
    # Sidebar management                                                   #
    # ------------------------------------------------------------------ #

    def _rebuild_sidebar(self) -> None:
        """Repopulate the sidebar from built-ins + user folders."""
        self._rebuilding_sidebar = True
        sidebar = self.query_one("#sidebar", ListView)
        sidebar.clear()
        sidebar.append(ListItem(Label("Today")))
        sidebar.append(ListItem(Label("Upcoming")))
        sidebar.append(ListItem(Label("Waiting On")))
        for folder in sorted(self._all_folders, key=lambda f: f.position):
            sidebar.append(ListItem(Label(folder.name)))
        sidebar.append(ListItem(Label("Someday")))
        sidebar.append(ListItem(Label("Logbook")))
        view_ids = self._sidebar_view_ids
        try:
            idx = view_ids.index(self._current_view)
        except ValueError:
            idx = 0
            self._current_view = "today"
        self.call_after_refresh(self._apply_sidebar_selection, idx)
        self.call_after_refresh(self._clear_rebuilding_flag)

    def _clear_rebuilding_flag(self) -> None:
        self._rebuilding_sidebar = False

    def _apply_sidebar_selection(self, idx: int) -> None:
        self.query_one("#sidebar", ListView).index = idx

    # ------------------------------------------------------------------ #
    # Rendering helpers                                                    #
    # ------------------------------------------------------------------ #

    def _refresh_list(self, select_task_id: str | None = None) -> None:
        list_view = self.query_one("#task-list", ListView)
        prev_index = list_view.index  # capture before clear resets it

        list_view.clear()
        self._list_entries = []
        self._placeholder_list_idx = None

        if self._current_view == "today":
            self._render_today_view(list_view)
        elif self._current_view == "upcoming":
            self._render_upcoming_view(list_view)
        elif self._current_view == "waiting_on":
            self._render_waiting_on_view(list_view)
        elif self._current_view == "someday":
            self._render_someday_view(list_view)
        elif self._current_view == "logbook":
            self._render_logbook_view(list_view)
        else:
            self._render_folder_view(list_view, self._current_view)

        # Compute the target index now (while _list_entries is current),
        # then defer the actual index + focus update until after Textual has
        # finished processing all the pending mount/remove messages from
        # clear() and append().  Setting index before the DOM settles causes
        # Textual to silently discard it, which makes the highlight vanish.
        target_idx = self._compute_target_index(select_task_id, prev_index)
        if target_idx is not None:
            self.call_after_refresh(self._apply_selection, target_idx)

        has_tasks = any(e is not None for e in self._list_entries)
        empty_hint = self.query_one("#empty-hint", Label)
        if has_tasks:
            empty_hint.add_class("hidden")
        else:
            empty_hint.remove_class("hidden")

    def _render_today_view(self, list_view: ListView) -> None:
        all_today = today_tasks(self._all_tasks)
        # Split into today-folder tasks (sortable/reorderable) and tasks from
        # other folders that surface here because they have no scheduled date.
        today_only = [t for t in all_today if t.folder_id == "today"]
        other = [t for t in all_today if t.folder_id != "today"]

        self.query_one("#header", Label).update(f"Today ({len(all_today)})")

        # Placeholder row only applies in the today-folder section.
        ph_at: int | None = None
        if self._show_placeholder:
            ph_at = self._placeholder_insert_idx(today_only)

        for i, task in enumerate(today_only):
            if ph_at == i:
                self._placeholder_list_idx = len(self._list_entries)
                self._list_entries.append(None)
                list_view.append(ListItem(Label(" "), classes="placeholder"))
            self._list_entries.append(task)
            list_view.append(ListItem(Label(task.title)))

        if ph_at == len(today_only):
            self._placeholder_list_idx = len(self._list_entries)
            self._list_entries.append(None)
            list_view.append(ListItem(Label(" "), classes="placeholder"))

        if other:
            self._list_entries.append(None)
            list_view.append(ListItem(Label("── Also Due ──")))
            for task in other:
                self._list_entries.append(task)
                if task.folder_id == "waiting_on":
                    label = f"[W] {task.title}"
                else:
                    folder_label = self._view_label(task.folder_id)
                    label = f"[{folder_label}] {task.title}"
                list_view.append(ListItem(Label(label)))

    def _render_upcoming_view(self, list_view: ListView) -> None:
        tasks = upcoming_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Upcoming ({len(tasks)})")
        for task in tasks:
            date_str = (
                task.scheduled_date.strftime("%b %d %a") if task.scheduled_date else ""
            )
            folder_hint = ""
            if task.folder_id != "today":
                folder_hint = f"  [{self._view_label(task.folder_id)}]"
            self._list_entries.append(task)
            list_view.append(ListItem(Label(f"{task.title}  {date_str}{folder_hint}")))

    def _render_waiting_on_view(self, list_view: ListView) -> None:
        self.query_one("#header", Label).update("Waiting On")
        for task in waiting_on_tasks(self._all_tasks):
            self._list_entries.append(task)
            date_str = (
                f"  [{task.scheduled_date.strftime('%b %d %a')}]"
                if task.scheduled_date
                else ""
            )
            list_view.append(ListItem(Label(f"{task.title}{date_str}")))

    def _render_someday_view(self, list_view: ListView) -> None:
        tasks = someday_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Someday ({len(tasks)})")
        for task in tasks:
            self._list_entries.append(task)
            list_view.append(ListItem(Label(task.title)))

    def _render_logbook_view(self, list_view: ListView) -> None:
        tasks = logbook_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Logbook ({len(tasks)})")
        for task in tasks:
            timestamp = (
                task.completed_at.strftime("%Y-%m-%d %H:%M")
                if task.completed_at
                else "unknown"
            )
            marker = "D" if task.is_deleted else "C"
            self._list_entries.append(task)
            list_view.append(ListItem(Label(f"{marker}  {task.title}  [{timestamp}]")))

    def _render_folder_view(self, list_view: ListView, folder_id: str) -> None:
        label = self._view_label(folder_id)
        tasks = folder_tasks(self._all_tasks, folder_id)
        self.query_one("#header", Label).update(f"{label} ({len(tasks)})")
        for task in tasks:
            self._list_entries.append(task)
            list_view.append(ListItem(Label(task.title)))

    def _placeholder_insert_idx(self, active: list[Task]) -> int:
        """Index within `active` before which the placeholder row is inserted."""
        if not self._pending_anchor_id:
            return 0
        anchor_idx = next(
            (i for i, t in enumerate(active) if t.id == self._pending_anchor_id), None
        )
        if anchor_idx is None:
            return 0
        return (
            anchor_idx if self._pending_insert_position == "before" else anchor_idx + 1
        )

    def _compute_target_index(
        self, select_task_id: str | None, prev_index: int | None
    ) -> int | None:
        """Return the list index that should be highlighted after a rebuild."""
        n = len(self._list_entries)
        if n == 0:
            return None
        if select_task_id is not None:
            for i, entry in enumerate(self._list_entries):
                if entry is not None and entry.id == select_task_id:
                    return i
        # While a placeholder is visible, keep the cursor on it.
        if self._show_placeholder and self._placeholder_list_idx is not None:
            return self._placeholder_list_idx
        # Fall back to previous position clamped to new length,
        # scanning forward then backward past any separator.
        target = min(prev_index, n - 1) if prev_index is not None else 0
        for i in range(target, n):
            if self._list_entries[i] is not None:
                return i
        for i in range(target - 1, -1, -1):
            if self._list_entries[i] is not None:
                return i
        return None

    def _update_placeholder_label(self, text: str) -> None:
        """Update the placeholder row's label text in place (no full rebuild)."""
        if self._placeholder_list_idx is None:
            return
        items = list(self.query_one("#task-list", ListView).query(ListItem))
        if self._placeholder_list_idx < len(items):
            items[self._placeholder_list_idx].query_one(Label).update(text)

    def _apply_selection(self, idx: int) -> None:
        """Set the ListView highlight and restore focus after a DOM rebuild."""
        list_view = self.query_one("#task-list", ListView)
        list_view.index = idx
        sidebar = self.query_one("#sidebar", ListView)
        if self._mode == "NORMAL" and not sidebar.has_focus:
            list_view.focus()

    def _push_undo(self) -> None:
        self._undo_stack.append(copy.deepcopy(self._all_tasks))
        self._redo_stack.clear()

    def _update_status(self, message: str = "") -> None:
        mode = "INSERT" if self._mode == "INSERT" else "NORMAL"
        view_name = self._view_label(self._current_view)
        suffix = f"  {message}" if message else ""
        self.query_one("#status", Label).update(f"{mode}  |  {view_name}{suffix}")

    def _get_selected_task(self) -> Task | None:
        """Return the Task at the current list selection, or None if on a separator."""
        list_view = self.query_one("#task-list", ListView)
        idx = list_view.index
        if idx is None or idx >= len(self._list_entries):
            return None
        return self._list_entries[idx]

    def _save(self) -> None:
        save_data(self._all_tasks, self._all_folders, self._data_file)

    # ------------------------------------------------------------------ #
    # Key handling                                                         #
    # ------------------------------------------------------------------ #

    def on_key(self, event: events.Key) -> None:
        # Don't intercept keys when a modal overlay is active — let the modal handle them.
        if len(self.screen_stack) > 1:
            return
        # Delete-folder confirmation takes priority
        if self._delete_confirm_folder_id:
            self._handle_delete_confirm_key(event)
            return
        if self._mode == "INSERT":
            if event.key == "escape":
                self._cancel_input()
        elif self.query_one("#sidebar", ListView).has_focus:
            self._handle_sidebar_key(event)
        else:
            self._handle_normal_key(event)

    def _handle_sidebar_key(self, event: events.Key) -> None:
        sidebar = self.query_one("#sidebar", ListView)

        # Move-mode: sidebar is acting as a folder picker
        if self._move_mode:
            if event.key == "j":
                event.prevent_default()
                sidebar.action_cursor_down()
            elif event.key == "k":
                event.prevent_default()
                sidebar.action_cursor_up()
            elif event.key in ("l", "enter"):
                event.prevent_default()
                self._confirm_move_task()
            elif event.key == "escape":
                event.prevent_default()
                self._cancel_move_mode()
            return

        if event.key == "j":
            event.prevent_default()
            sidebar.action_cursor_down()
        elif event.key == "k":
            event.prevent_default()
            sidebar.action_cursor_up()
        elif event.key in ("l", "enter"):
            event.prevent_default()
            self.query_one("#task-list", ListView).focus()
        elif event.key == "N":
            event.prevent_default()
            self._start_create_folder()
        elif event.key == "r":
            event.prevent_default()
            self._start_rename_folder()
        elif event.key == "d":
            event.prevent_default()
            self._delete_selected_folder()
        elif event.key.isdigit() and event.key != "0":
            event.prevent_default()
            self._jump_to_view(int(event.key) - 1)
        elif event.key == "slash":
            event.prevent_default()
            self._open_search()
        elif event.key == "u":
            event.prevent_default()
            self._undo()
        elif event.key == "ctrl+r":
            event.prevent_default()
            self._redo()
        elif event.key == "q":
            event.prevent_default()
            self.exit()

    def _handle_normal_key(self, event: events.Key) -> None:
        list_view = self.query_one("#task-list", ListView)

        pending = self._pending_key
        self._pending_key = ""

        if pending == "g" and event.key == "g":
            event.prevent_default()
            if self._list_entries:
                list_view.index = 0
                self._skip_separator(direction=1)
            return
        elif event.key == "g":
            self._pending_key = "g"
            return

        if event.key == "enter":
            event.prevent_default()
            self._open_task_detail()
            return
        elif event.key == "j":
            event.prevent_default()
            list_view.action_cursor_down()
            self._skip_separator(direction=1)
        elif event.key == "k":
            event.prevent_default()
            list_view.action_cursor_up()
            self._skip_separator(direction=-1)
        elif event.key == "G":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                list_view.index = n - 1
                self._skip_separator(direction=-1)
        elif event.key == "J":
            event.prevent_default()
            self._move_selected_down()
        elif event.key == "K":
            event.prevent_default()
            self._move_selected_up()
        elif event.key == "h":
            event.prevent_default()
            self.query_one("#sidebar", ListView).focus()
        elif event.key.isdigit() and event.key != "0":
            event.prevent_default()
            self._jump_to_view(int(event.key) - 1)
        elif event.key == "o":
            event.prevent_default()
            self._start_add_task("after")
        elif event.key == "O":
            event.prevent_default()
            self._start_add_task("before")
        elif event.key == "s":
            event.prevent_default()
            self._start_schedule()
        elif event.key == "m":
            event.prevent_default()
            self._start_move_task()
        elif event.key == "u":
            event.prevent_default()
            self._undo()
        elif event.key == "ctrl+r":
            event.prevent_default()
            self._redo()
        elif event.key == "w" and self._current_view == "today":
            event.prevent_default()
            self._move_selected_to_waiting_on()
        elif event.key == "t" and self._current_view == "waiting_on":
            event.prevent_default()
            self._move_selected_to_today()
        elif event.key == "x" or event.key == "space":
            event.prevent_default()
            self._complete_selected()
        elif event.key == "d":
            event.prevent_default()
            self._delete_selected()
        elif event.key == "slash":
            event.prevent_default()
            self._open_search()
        elif event.key == "colon":
            event.prevent_default()
            self._start_command()
        elif event.key == "q":
            event.prevent_default()
            self.exit()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update the current view when the sidebar selection changes."""
        if event.list_view.id != "sidebar":
            return
        if self._rebuilding_sidebar or self._move_mode:
            return
        idx = event.list_view.index
        if idx is None:
            return
        view_ids = self._sidebar_view_ids
        if idx >= len(view_ids):
            return
        new_view = view_ids[idx]
        if new_view == self._current_view:
            return
        self._current_view = new_view
        self._refresh_list()
        self._update_status()

    def _jump_to_view(self, idx: int) -> None:
        view_ids = self._sidebar_view_ids
        if 0 <= idx < len(view_ids):
            self.query_one("#sidebar", ListView).index = idx
            # on_list_view_highlighted handles the rest

    def _skip_separator(self, direction: int) -> None:
        """If the current ListView selection is a separator, move past it."""
        list_view = self.query_one("#task-list", ListView)
        idx = list_view.index
        if (
            idx is not None
            and idx < len(self._list_entries)
            and self._list_entries[idx] is None
        ):
            if direction == 1:
                list_view.action_cursor_down()
            else:
                list_view.action_cursor_up()

    # ------------------------------------------------------------------ #
    # Task creation flow                                                   #
    # ------------------------------------------------------------------ #

    def _start_add_task(self, insert_position: str = "after") -> None:
        # Upcoming is a read-only smart view — no task creation there.
        if self._current_view == "upcoming":
            self._update_status("(cannot add tasks to Upcoming — use Today or a folder)")
            return
        task = self._get_selected_task()
        # Only anchor on 'today'-folder tasks; other-folder tasks surfacing in
        # Today are not reorderable so fall back to top-of-today insertion.
        if task is not None and task.folder_id == "today":
            self._pending_anchor_id = task.id
        else:
            self._pending_anchor_id = ""
        self._pending_insert_position = insert_position
        self._show_placeholder = True
        self._mode = "INSERT"
        self._input_stage = "title"
        inp = self.query_one("#task-input", Input)
        if self._current_view == "waiting_on":
            inp.placeholder = "Waiting On task title..."
        elif self._current_view == "someday":
            inp.placeholder = "Someday task title..."
        else:
            inp.placeholder = "Task title..."
        inp.add_class("active")
        inp.focus()
        self._update_status()
        self._refresh_list()  # show the placeholder row immediately

    def _start_command(self) -> None:
        self._mode = "INSERT"
        self._input_stage = "command"
        inp = self.query_one("#task-input", Input)
        inp.placeholder = ":"
        inp.add_class("active")
        inp.focus()
        self._update_status(":")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        inp = self.query_one("#task-input", Input)

        if self._input_stage == "title":
            if not value:
                self._cancel_input()
                return
            self._pending_title = value
            inp.clear()
            inp.placeholder = "Notes (Enter to skip)..."
            self._input_stage = "notes"
            # Update the placeholder row to show the title the user just typed
            # so there's visual context while entering notes.
            self._update_placeholder_label(value)

        elif self._input_stage == "notes":
            self._push_undo()
            new_id = str(uuid.uuid4())
            if self._current_view == "waiting_on":
                self._all_tasks = add_waiting_on_task(
                    self._all_tasks, self._pending_title, notes=value
                )
            elif self._current_view in ("someday",) or self._current_view not in BUILTIN_FOLDER_IDS:
                # Someday built-in or any custom folder: append task there
                self._all_tasks = add_task_to_folder(
                    self._all_tasks,
                    self._current_view,
                    self._pending_title,
                    notes=value,
                    task_id=new_id,
                )
            elif not self._pending_anchor_id:
                self._all_tasks = add_task(
                    self._all_tasks, self._pending_title, notes=value, task_id=new_id
                )
            elif self._pending_insert_position == "before":
                self._all_tasks = insert_task_before(
                    self._all_tasks,
                    self._pending_anchor_id,
                    self._pending_title,
                    notes=value,
                    task_id=new_id,
                )
            else:
                self._all_tasks = insert_task_after(
                    self._all_tasks,
                    self._pending_anchor_id,
                    self._pending_title,
                    notes=value,
                    task_id=new_id,
                )
            self._save()
            self._show_placeholder = False  # clear before rebuild
            self._placeholder_list_idx = None
            self._refresh_list(select_task_id=new_id)
            self._cancel_input()

        elif self._input_stage == "date":
            self._apply_date(value)

        elif self._input_stage == "command":
            self._cancel_input()
            if value == "help":
                self.push_screen(HelpScreen())
            elif value:
                self._update_status(f"(unknown command: {value})")

        elif self._input_stage == "folder_name":
            if value:
                new_folder_id = str(uuid.uuid4())
                self._all_folders = create_folder(
                    self._all_folders, value, folder_id=new_folder_id
                )
                self._save()
                self._rebuild_sidebar()
                self._current_view = new_folder_id
                self._refresh_list()
            self._cancel_input()

        elif self._input_stage == "folder_rename":
            if value and self._rename_folder_id:
                self._all_folders = rename_folder(
                    self._all_folders, self._rename_folder_id, value
                )
                self._save()
                self._rebuild_sidebar()
                self._refresh_list()
            self._rename_folder_id = ""
            self._cancel_input()

    def _cancel_input(self) -> None:
        inp = self.query_one("#task-input", Input)
        inp.clear()
        inp.remove_class("active")
        had_placeholder = self._show_placeholder
        self._mode = "NORMAL"
        self._input_stage = ""
        self._pending_title = ""
        self._pending_task_id = ""
        self._pending_anchor_id = ""
        self._pending_insert_position = "after"
        self._show_placeholder = False
        self._placeholder_list_idx = None
        self._update_status()
        if had_placeholder:
            self._refresh_list()  # removes placeholder; _apply_selection refocuses
        else:
            self.query_one("#task-list", ListView).focus()

    # ------------------------------------------------------------------ #
    # Task scheduling flow                                                 #
    # ------------------------------------------------------------------ #

    def _start_schedule(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._pending_task_id = task.id
        self._mode = "INSERT"
        self._input_stage = "date"
        inp = self.query_one("#task-input", Input)
        inp.value = task.scheduled_date.isoformat() if task.scheduled_date else ""
        inp.placeholder = "Date: tomorrow/+3d/monday/YYYY-MM-DD (empty=clear)..."
        inp.add_class("active")
        inp.focus()
        self._update_status()

    def _apply_date(self, value: str) -> None:
        try:
            parsed = parse_date_input(value)
        except InvalidDateError:
            self._update_status("(invalid date)")
            self._cancel_input()
            return

        self._push_undo()
        if parsed is None:
            self._all_tasks = unschedule_task(self._all_tasks, self._pending_task_id)
        else:
            self._all_tasks = schedule_task(
                self._all_tasks, self._pending_task_id, parsed
            )

        self._save()
        self._refresh_list()
        self._cancel_input()

    # ------------------------------------------------------------------ #
    # Task movement                                                        #
    # ------------------------------------------------------------------ #

    def _start_move_task(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._pending_task_id = task.id
        self._move_mode = True
        self.query_one("#sidebar", ListView).focus()
        self._update_status("Move to: j/k select folder, Enter confirm, Esc cancel")

    def _confirm_move_task(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            self._cancel_move_mode()
            return
        target_folder_id = view_ids[idx]
        if target_folder_id == "upcoming":
            self._update_status("(cannot move to Upcoming — schedule a date with 's' instead)")
            self._cancel_move_mode()
            return
        self._push_undo()
        self._all_tasks = move_task_to_folder(
            self._all_tasks, self._pending_task_id, target_folder_id
        )
        self._save()
        self._move_mode = False
        self._pending_task_id = ""
        self._current_view = target_folder_id
        self._rebuild_sidebar()
        self._refresh_list()
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _cancel_move_mode(self) -> None:
        self._move_mode = False
        self._pending_task_id = ""
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _open_task_detail(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        task_id = task.id
        old_repeat = task.repeat_rule
        old_recur = task.recur_rule

        def _on_detail_close(result: tuple[str, str, str, str] | None) -> None:
            if result is None:
                return
            new_title, new_notes, repeat_text, recur_text = result

            # Parse repeat field.
            new_repeat: RepeatRule | None = old_repeat
            try:
                parsed = parse_repeat_input(repeat_text)
                if parsed is None:
                    new_repeat = None
                else:
                    interval, unit = parsed
                    if (
                        old_repeat
                        and old_repeat.interval == interval
                        and old_repeat.unit == unit
                    ):
                        new_repeat = old_repeat  # preserve next_due unchanged
                    else:
                        new_repeat = make_repeat_rule(interval, unit)
            except InvalidRepeatError:
                self._update_status("(invalid repeat — changes saved, repeat unchanged)")
                new_repeat = old_repeat

            # Parse recur field.
            new_recur: RecurRule | None = old_recur
            try:
                parsed_recur = parse_repeat_input(recur_text)  # same format
                if parsed_recur is None:
                    new_recur = None
                else:
                    interval_r, unit_r = parsed_recur
                    new_recur = RecurRule(interval=interval_r, unit=unit_r)
            except InvalidRepeatError:
                self._update_status("(invalid recurring — changes saved, recurring unchanged)")
                new_recur = old_recur

            # Mutual exclusivity: if both are set, repeat wins and recur is cleared.
            if new_repeat is not None and new_recur is not None:
                new_recur = None
                self._update_status("(both repeat and recurring set — repeat takes precedence)")

            title_changed = new_title != task.title or new_notes != task.notes
            repeat_changed = new_repeat != old_repeat
            recur_changed = new_recur != old_recur
            if not title_changed and not repeat_changed and not recur_changed:
                return

            self._push_undo()
            if title_changed:
                self._all_tasks = edit_task(self._all_tasks, task_id, new_title, new_notes)
            if repeat_changed:
                self._all_tasks = set_repeat_rule(self._all_tasks, task_id, new_repeat)
            if recur_changed:
                self._all_tasks = set_recur_rule(self._all_tasks, task_id, new_recur)
            self._save()
            self._refresh_list(select_task_id=task_id)

        self.push_screen(TaskDetailScreen(task), _on_detail_close)

    def _open_search(self) -> None:
        def _on_search_close(task_id: str | None) -> None:
            if task_id is None:
                self.query_one("#task-list", ListView).focus()
                return
            task = next((t for t in self._all_tasks if t.id == task_id), None)
            if task is None:
                self.query_one("#task-list", ListView).focus()
                return
            # Navigate to the task's folder
            if task.folder_id == "logbook":
                self._current_view = "logbook"
            elif task.folder_id == "waiting_on":
                self._current_view = "waiting_on"
            elif task.folder_id == "someday":
                self._current_view = "someday"
            elif task.folder_id == "today":
                self._current_view = "today"
            else:
                self._current_view = task.folder_id
            self._rebuild_sidebar()
            self._refresh_list(select_task_id=task_id)

        self.push_screen(SearchScreen(self._all_tasks), _on_search_close)

    def _move_selected_to_waiting_on(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_to_waiting_on(self._all_tasks, task.id)
        self._save()
        self._refresh_list()

    def _move_selected_to_today(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_to_today(self._all_tasks, task.id)
        self._save()
        self._refresh_list()

    # ------------------------------------------------------------------ #
    # Folder creation / rename / delete                                   #
    # ------------------------------------------------------------------ #

    def _start_create_folder(self) -> None:
        self._mode = "INSERT"
        self._input_stage = "folder_name"
        inp = self.query_one("#task-input", Input)
        inp.placeholder = "New folder name..."
        inp.add_class("active")
        inp.focus()
        self._update_status()

    def _start_rename_folder(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        folder_id = view_ids[idx]
        if folder_id in BUILTIN_FOLDER_IDS:
            self._update_status("(cannot rename built-in folders)")
            return
        self._rename_folder_id = folder_id
        folder = next((f for f in self._all_folders if f.id == folder_id), None)
        current_name = folder.name if folder else ""
        self._mode = "INSERT"
        self._input_stage = "folder_rename"
        inp = self.query_one("#task-input", Input)
        inp.value = current_name
        inp.placeholder = "Folder name..."
        inp.add_class("active")
        inp.focus()
        self._update_status()

    def _delete_selected_folder(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        folder_id = view_ids[idx]
        if folder_id in BUILTIN_FOLDER_IDS:
            self._update_status("(cannot delete built-in folders)")
            return
        tasks_in_folder = folder_tasks(self._all_tasks, folder_id)
        if not tasks_in_folder:
            # Empty folder: delete immediately
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                self._current_view = "today"
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
        else:
            # Non-empty: prompt user
            folder = next((f for f in self._all_folders if f.id == folder_id), None)
            name = folder.name if folder else folder_id
            n = len(tasks_in_folder)
            self._delete_confirm_folder_id = folder_id
            self._update_status(
                f"'{name}' has {n} task(s). [d]elete all  [m]ove to Today  [Esc] cancel"
            )

    def _handle_delete_confirm_key(self, event: events.Key) -> None:
        folder_id = self._delete_confirm_folder_id
        if event.key == "d":
            event.prevent_default()
            self._all_tasks = discard_folder_tasks(self._all_tasks, folder_id)
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                self._current_view = "today"
            self._save()
            self._delete_confirm_folder_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "m":
            event.prevent_default()
            self._all_tasks = move_folder_tasks_to_today(self._all_tasks, folder_id)
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                self._current_view = "today"
            self._save()
            self._delete_confirm_folder_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "escape":
            event.prevent_default()
            self._delete_confirm_folder_id = ""
            self._update_status()

    # ------------------------------------------------------------------ #
    # Task completion                                                      #
    # ------------------------------------------------------------------ #

    def _complete_selected(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = complete_task(self._all_tasks, task.id)
        self._save()
        self._refresh_list()

    def _delete_selected(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = delete_task(self._all_tasks, task.id)
        self._save()
        self._refresh_list()

    # ------------------------------------------------------------------ #
    # Reordering                                                           #
    # ------------------------------------------------------------------ #

    def _move_selected_up(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        if not self._can_reorder(task):
            return
        self._push_undo()
        self._all_tasks = move_task_up(self._all_tasks, task.id)
        self._save()
        self._refresh_list(select_task_id=task.id)

    def _move_selected_down(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        if not self._can_reorder(task):
            return
        self._push_undo()
        self._all_tasks = move_task_down(self._all_tasks, task.id)
        self._save()
        self._refresh_list(select_task_id=task.id)

    def _can_reorder(self, task: Task) -> bool:
        """Return True when J/K reordering makes sense for the selected task."""
        # Upcoming is date-sorted — no manual reordering.
        if self._current_view == "upcoming":
            return False
        # In Today view, only today-folder tasks are positionally ordered;
        # tasks in the "Also Due" section belong to other folders.
        if self._current_view == "today" and task.folder_id != "today":
            return False
        return True

    # ------------------------------------------------------------------ #
    # Undo                                                                 #
    # ------------------------------------------------------------------ #

    def _undo(self) -> None:
        if not self._undo_stack:
            self._update_status("(nothing to undo)")
            return
        self._redo_stack.append(copy.deepcopy(self._all_tasks))
        self._all_tasks = self._undo_stack.pop()
        self._save()
        self._refresh_list()

    def _redo(self) -> None:
        if not self._redo_stack:
            self._update_status("(nothing to redo)")
            return
        self._undo_stack.append(copy.deepcopy(self._all_tasks))
        self._all_tasks = self._redo_stack.pop()
        self._save()
        self._refresh_list()
