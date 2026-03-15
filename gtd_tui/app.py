from __future__ import annotations

import copy
import uuid

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static
from textual import events

from gtd_tui.gtd.dates import InvalidDateError, parse_date_input
from gtd_tui.gtd.operations import (
    add_task,
    complete_task,
    insert_task_after,
    insert_task_before,
    move_task_down,
    move_task_up,
    schedule_task,
    scheduled_tasks,
    today_tasks,
    unschedule_task,
)
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import load_tasks, save_tasks


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-panel {
        width: 54;
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

[bold]Task Actions[/bold]
  o            Add new task after selected (INSERT mode)
  O            Add new task before selected (INSERT mode)
  x / Space    Complete selected task
  s            Schedule selected task
  J / K        Move selected task down / up
  u            Undo last action

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
        self._mode: str = "NORMAL"
        self._input_stage: str = ""  # "title", "notes", or "date"
        self._pending_title: str = ""
        self._pending_task_id: str = ""
        # Parallel to ListView children: Task for task rows, None for separators
        self._list_entries: list[Task | None] = []
        self._undo_stack: list[list[Task]] = []
        self._pending_anchor_id: str = ""
        self._pending_insert_position: str = "after"  # "after" or "before"
        # Placeholder row shown in the list while a new task is being typed
        self._show_placeholder: bool = False
        self._placeholder_list_idx: int | None = None
        # Tracks the first key of a chord (e.g. "g" waiting for "gg")
        self._pending_key: str = ""

    def compose(self) -> ComposeResult:
        yield Label("Today", id="header")
        yield Input(placeholder="Task title...", id="task-input")
        yield ListView(id="task-list")
        yield Label("No tasks — press o to add one", id="empty-hint")
        yield Label("NORMAL  |  Today", id="status")

    def on_mount(self) -> None:
        self._refresh_list()
        self.query_one("#task-list", ListView).focus()

    # ------------------------------------------------------------------ #
    # Rendering helpers                                                    #
    # ------------------------------------------------------------------ #

    def _refresh_list(self, select_task_id: str | None = None) -> None:
        list_view = self.query_one("#task-list", ListView)
        prev_index = list_view.index  # capture before clear resets it

        list_view.clear()
        self._list_entries = []
        self._placeholder_list_idx = None

        active = today_tasks(self._all_tasks)
        snoozed = scheduled_tasks(self._all_tasks)

        total = len(active) + len(snoozed)
        self.query_one("#header", Label).update(f"Today ({total})")

        # Determine where the placeholder row belongs among active tasks.
        # ph_at is the index within `active` before which the placeholder is
        # inserted (so ph_at == len(active) means "after all active tasks").
        ph_at: int | None = None
        if self._show_placeholder:
            ph_at = self._placeholder_insert_idx(active)

        for i, task in enumerate(active):
            if ph_at == i:
                self._placeholder_list_idx = len(self._list_entries)
                self._list_entries.append(None)
                list_view.append(ListItem(Label(" "), classes="placeholder"))
            self._list_entries.append(task)
            list_view.append(ListItem(Label(task.title)))

        if ph_at == len(active):
            self._placeholder_list_idx = len(self._list_entries)
            self._list_entries.append(None)
            list_view.append(ListItem(Label(" "), classes="placeholder"))

        if snoozed:
            self._list_entries.append(None)  # separator
            list_view.append(ListItem(Label("── Scheduled ──")))
            for task in snoozed:
                self._list_entries.append(task)
                date_str = task.scheduled_date.strftime("%b %d %a") if task.scheduled_date else ""
                list_view.append(ListItem(Label(f"{task.title}  [{date_str}]")))

        # Compute the target index now (while _list_entries is current),
        # then defer the actual index + focus update until after Textual has
        # finished processing all the pending mount/remove messages from
        # clear() and append().  Setting index before the DOM settles causes
        # Textual to silently discard it, which makes the highlight vanish.
        target_idx = self._compute_target_index(select_task_id, prev_index)
        if target_idx is not None:
            self.call_after_refresh(self._apply_selection, target_idx)

        empty_hint = self.query_one("#empty-hint", Label)
        if active or snoozed:
            empty_hint.add_class("hidden")
        else:
            empty_hint.remove_class("hidden")

    def _placeholder_insert_idx(self, active: list[Task]) -> int:
        """Index within `active` before which the placeholder row is inserted."""
        if not self._pending_anchor_id:
            return 0
        anchor_idx = next(
            (i for i, t in enumerate(active) if t.id == self._pending_anchor_id), None
        )
        if anchor_idx is None:
            return 0
        return anchor_idx if self._pending_insert_position == "before" else anchor_idx + 1

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

    def _update_status(self, message: str = "") -> None:
        mode = "INSERT" if self._mode == "INSERT" else "NORMAL"
        suffix = f"  {message}" if message else ""
        self.query_one("#status", Label).update(f"{mode}  |  Today{suffix}")

    def _get_selected_task(self) -> Task | None:
        list_view = self.query_one("#task-list", ListView)
        idx = list_view.index
        if idx is None or idx >= len(self._list_entries):
            return None
        return self._list_entries[idx]  # None if on separator

    # ------------------------------------------------------------------ #
    # Key handling                                                         #
    # ------------------------------------------------------------------ #

    def on_key(self, event: events.Key) -> None:
        if self._mode == "INSERT":
            if event.key == "escape":
                self._cancel_input()
        else:
            self._handle_normal_key(event)

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
        elif event.key == "o":
            event.prevent_default()
            self._start_add_task("after")
        elif event.key == "O":
            event.prevent_default()
            self._start_add_task("before")
        elif event.key == "s":
            event.prevent_default()
            self._start_schedule()
        elif event.key == "u":
            event.prevent_default()
            self._undo()
        elif event.key == "x" or event.key == "space":
            event.prevent_default()
            self._complete_selected()
        elif event.key == "colon":
            event.prevent_default()
            self._start_command()
        elif event.key == "q":
            event.prevent_default()
            self.exit()

    def _skip_separator(self, direction: int) -> None:
        """If the current ListView selection is a separator, move past it."""
        list_view = self.query_one("#task-list", ListView)
        idx = list_view.index
        if idx is not None and idx < len(self._list_entries) and self._list_entries[idx] is None:
            if direction == 1:
                list_view.action_cursor_down()
            else:
                list_view.action_cursor_up()

    # ------------------------------------------------------------------ #
    # Task creation flow                                                   #
    # ------------------------------------------------------------------ #

    def _start_add_task(self, insert_position: str = "after") -> None:
        task = self._get_selected_task()
        self._pending_anchor_id = task.id if task is not None else ""
        self._pending_insert_position = insert_position
        self._show_placeholder = True
        self._mode = "INSERT"
        self._input_stage = "title"
        inp = self.query_one("#task-input", Input)
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
            if not self._pending_anchor_id:
                self._all_tasks = add_task(
                    self._all_tasks, self._pending_title, notes=value, task_id=new_id
                )
            elif self._pending_insert_position == "before":
                self._all_tasks = insert_task_before(
                    self._all_tasks, self._pending_anchor_id,
                    self._pending_title, notes=value, task_id=new_id,
                )
            else:
                self._all_tasks = insert_task_after(
                    self._all_tasks, self._pending_anchor_id,
                    self._pending_title, notes=value, task_id=new_id,
                )
            save_tasks(self._all_tasks)
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
            self._refresh_list()  # rebuilds without placeholder; _apply_selection refocuses
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
        inp.placeholder = "Date: YYYY-MM-DD or +1d/+2w/+1m  (empty to clear)..."
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
            self._all_tasks = schedule_task(self._all_tasks, self._pending_task_id, parsed)

        save_tasks(self._all_tasks)
        self._refresh_list()
        self._cancel_input()

    # ------------------------------------------------------------------ #
    # Task completion                                                      #
    # ------------------------------------------------------------------ #

    def _complete_selected(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = complete_task(self._all_tasks, task.id)
        save_tasks(self._all_tasks)
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
        save_tasks(self._all_tasks)
        self._refresh_list(select_task_id=task.id)

    def _move_selected_down(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_task_down(self._all_tasks, task.id)
        save_tasks(self._all_tasks)
        self._refresh_list(select_task_id=task.id)

    # ------------------------------------------------------------------ #
    # Undo                                                                 #
    # ------------------------------------------------------------------ #

    def _undo(self) -> None:
        if not self._undo_stack:
            self._update_status("(nothing to undo)")
            return
        self._all_tasks = self._undo_stack.pop()
        save_tasks(self._all_tasks)
        self._refresh_list()
