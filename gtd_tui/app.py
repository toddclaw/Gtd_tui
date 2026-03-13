from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Input, Label, ListItem, ListView
from textual import events

from gtd_tui.gtd.operations import add_task, complete_task, today_tasks
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
        self._input_stage: str = ""  # "title" or "notes"
        self._pending_title: str = ""

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
        tasks = today_tasks(self._all_tasks)
        for task in tasks:
            list_view.append(ListItem(Label(task.title)))
        empty_hint = self.query_one("#empty-hint", Label)
        if tasks:
            empty_hint.add_class("hidden")
        else:
            empty_hint.remove_class("hidden")

    def _update_status(self) -> None:
        mode = "INSERT" if self._mode == "INSERT" else "NORMAL"
        self.query_one("#status", Label).update(f"{mode}  |  Today")

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
        elif event.key == "k":
            event.prevent_default()
            list_view.action_cursor_up()
        elif event.key == "G":
            event.prevent_default()
            n = len(today_tasks(self._all_tasks))
            if n > 0:
                list_view.index = n - 1
        elif event.key == "o":
            event.prevent_default()
            self._start_add_task()
        elif event.key == "x" or event.key == "space":
            event.prevent_default()
            self._complete_selected()
        elif event.key == "q":
            event.prevent_default()
            self.exit()

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

    def _cancel_input(self) -> None:
        inp = self.query_one("#task-input", Input)
        inp.clear()
        inp.remove_class("active")
        self._mode = "NORMAL"
        self._input_stage = ""
        self._pending_title = ""
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    # ------------------------------------------------------------------ #
    # Task completion                                                      #
    # ------------------------------------------------------------------ #

    def _complete_selected(self) -> None:
        list_view = self.query_one("#task-list", ListView)
        idx = list_view.index
        if idx is None:
            return
        tasks = today_tasks(self._all_tasks)
        if 0 <= idx < len(tasks):
            self._all_tasks = complete_task(self._all_tasks, tasks[idx].id)
            save_tasks(self._all_tasks)
            self._refresh_list()
