from __future__ import annotations

import copy
import uuid

from textual import events
from textual.app import App, ComposeResult
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
    create_folder,
    delete_folder,
    discard_folder_tasks,
    folder_tasks,
    insert_task_after,
    insert_task_before,
    move_folder_tasks_to_today,
    move_task_down,
    move_task_to_folder,
    move_task_up,
    move_to_today,
    move_to_waiting_on,
    rename_folder,
    schedule_task,
    someday_tasks,
    today_tasks,
    unschedule_task,
    upcoming_tasks,
    waiting_on_tasks,
)
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
  o            Add new task after selected (INSERT mode)
  O            Add new task before selected (INSERT mode)
  x / Space    Complete selected task
  s            Schedule selected task
  m            Move selected task to a folder (sidebar picker)
  J / K        Move selected task down / up  (Today)
  w            Move selected task to Waiting On  (Today view)
  t            Move selected task to Today       (Waiting On view)
  u            Undo last action
  Ctrl+R       Redo last undone action

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

    def __init__(self) -> None:
        super().__init__()
        self._all_tasks: list[Task] = load_tasks()
        self._all_folders: list[Folder] = load_folders()
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
            + ["someday"]
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
        self._rebuild_sidebar()
        self._refresh_list()
        self.query_one("#task-list", ListView).focus()

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
        if self._mode == "NORMAL":
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
        save_data(self._all_tasks, self._all_folders)

    # ------------------------------------------------------------------ #
    # Key handling                                                         #
    # ------------------------------------------------------------------ #

    def on_key(self, event: events.Key) -> None:
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

        if event.key == "j":
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

    # ------------------------------------------------------------------ #
    # Reordering                                                           #
    # ------------------------------------------------------------------ #

    def _move_selected_up(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_task_up(self._all_tasks, task.id)
        self._save()
        self._refresh_list(select_task_id=task.id)

    def _move_selected_down(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_task_down(self._all_tasks, task.id)
        self._save()
        self._refresh_list(select_task_id=task.id)

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
