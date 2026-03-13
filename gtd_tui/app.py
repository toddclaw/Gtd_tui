from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Input, Label, ListItem, ListView
from textual import events

from gtd_tui.gtd.dates import InvalidDateError, parse_date_input
from gtd_tui.gtd.operations import (
    add_task,
    complete_task,
    schedule_task,
    scheduled_tasks,
    today_tasks,
    unschedule_task,
)
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import load_tasks, save_tasks


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

    def _refresh_list(self) -> None:
        list_view = self.query_one("#task-list", ListView)
        list_view.clear()
        self._list_entries = []

        active = today_tasks(self._all_tasks)
        snoozed = scheduled_tasks(self._all_tasks)

        for task in active:
            self._list_entries.append(task)
            list_view.append(ListItem(Label(task.title)))

        if snoozed:
            self._list_entries.append(None)  # separator
            list_view.append(ListItem(Label("── Scheduled ──")))
            for task in snoozed:
                self._list_entries.append(task)
                date_str = task.scheduled_date.strftime("%b %d") if task.scheduled_date else ""
                list_view.append(ListItem(Label(f"{task.title}  [{date_str}]")))

        empty_hint = self.query_one("#empty-hint", Label)
        if active or snoozed:
            empty_hint.add_class("hidden")
        else:
            empty_hint.remove_class("hidden")

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
        elif event.key == "o":
            event.prevent_default()
            self._start_add_task()
        elif event.key == "s":
            event.prevent_default()
            self._start_schedule()
        elif event.key == "x" or event.key == "space":
            event.prevent_default()
            self._complete_selected()
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

    def _start_add_task(self) -> None:
        self._mode = "INSERT"
        self._input_stage = "title"
        inp = self.query_one("#task-input", Input)
        inp.placeholder = "Task title..."
        inp.add_class("active")
        inp.focus()
        self._update_status()

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

        elif self._input_stage == "notes":
            self._all_tasks = add_task(self._all_tasks, self._pending_title, notes=value)
            save_tasks(self._all_tasks)
            self._refresh_list()
            self._cancel_input()

        elif self._input_stage == "date":
            self._apply_date(value)

    def _cancel_input(self) -> None:
        inp = self.query_one("#task-input", Input)
        inp.clear()
        inp.remove_class("active")
        self._mode = "NORMAL"
        self._input_stage = ""
        self._pending_title = ""
        self._pending_task_id = ""
        self._update_status()
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
        self._all_tasks = complete_task(self._all_tasks, task.id)
        save_tasks(self._all_tasks)
        self._refresh_list()
