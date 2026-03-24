from __future__ import annotations

import copy
import os
import signal
import subprocess
import time
import uuid
from dataclasses import replace
from datetime import date
from pathlib import Path

import pyperclip
from rich.markup import escape as markup_escape
from rich.text import Text as RichText
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import Input, Label, ListItem, ListView, Static

from gtd_tui.config import Config, default_config_path, load_config, save_default_config
from gtd_tui.gtd.area import Area
from gtd_tui.gtd.dates import (
    InvalidDateError,
    format_date,
    format_date_relative,
    parse_date_input,
)
from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, REFERENCE_FOLDER_ID, Folder
from gtd_tui.gtd.operations import (
    InvalidRepeatError,
    add_area,
    add_project,
    add_tag_to_task,
    add_task,
    add_task_to_folder,
    add_task_to_project,
    add_waiting_on_task,
    all_tags,
    assign_folder_to_area,
    assign_project_to_area,
    assign_task_to_project,
    check_auto_complete_project,
    clear_deadline,
    complete_task,
    deadline_status,
    delete_area,
    delete_folder,
    delete_project,
    delete_task,
    edit_task,
    folder_tasks,
    format_parsed_repeat,
    format_recur_rule,
    format_repeat_rule,
    inbox_tasks,
    insert_folder,
    insert_folder_task_after,
    insert_folder_task_before,
    insert_task_after,
    insert_task_before,
    insert_waiting_on_task_after,
    insert_waiting_on_task_before,
    is_divider_task,
    logbook_tasks,
    make_repeat_rule_from_parsed,
    move_area_down,
    move_area_up,
    move_block_down,
    move_block_up,
    move_folder_down,
    move_folder_tasks_to_today,
    move_folder_up,
    move_project_down,
    move_project_up,
    move_tag_down,
    move_tag_up,
    move_task_down,
    move_task_to_folder,
    move_task_up,
    move_to_today,
    move_to_waiting_on,
    parse_repeat_input,
    project_progress,
    project_tasks,
    project_tasks_including_completed,
    purge_logbook_task,
    reference_tasks,
    rename_area,
    rename_folder,
    rename_project,
    schedule_task,
    search_tasks,
    set_deadline,
    set_recur_rule,
    set_repeat_rule,
    set_tags,
    someday_tasks,
    spawn_repeating_tasks,
    tasks_with_tag,
    today_tasks,
    unlink_project_tasks,
    unschedule_task,
    upcoming_tasks,
    waiting_on_tasks,
    weekly_review_tasks,
)
from gtd_tui.gtd.project import Project
from gtd_tui.gtd.task import ChecklistItem, RecurRule, RepeatRule, Task
from gtd_tui.storage.file import (
    UndoStack,
    default_data_file_path,
    load_areas,
    load_collapsed_areas,
    load_folders,
    load_projects,
    load_redo_stack,
    load_tag_order,
    load_tasks,
    load_undo_stack,
    save_data,
)
from gtd_tui.storage.rotating_backup import maybe_backup_after_save
from gtd_tui.text.processing import fix_capitalization, fix_spelling
from gtd_tui.widgets.vim_input import VimInput


def _project_deadline_label(project: Project) -> tuple[str, str] | None:
    """Return (label, severity) for a project deadline, or None if no deadline.

    severity is one of 'overdue', 'soon', 'ok'.
    """
    if project.deadline is None:
        return None
    today = date.today()
    delta = (project.deadline - today).days
    label = f"due {format_date(project.deadline)}"
    if delta < 0:
        return (label, "overdue")
    elif delta <= 3:
        return (label, "soon")
    else:
        return (label, "ok")


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-scroll {
        width: 66;
        height: 30;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    """

    _HELP_TEXT = """\
[bold]Navigation[/bold]
  j / k        Move cursor down / up
  H / M / L    Jump to top / middle / bottom of list
  g g          Jump to top of list
  G            Jump to bottom of list
  Ctrl+d       Half-page down
  Ctrl+u       Half-page up
  h / l        Focus sidebar / task list
  i            Jump to Inbox
  0            Jump to sidebar item 0 (Inbox) — use h then j/k for other views

[bold]Task Actions[/bold]
  Enter        Open task detail / edit
  o            Add new task after selected
  O            Add new task before selected
  x / Space    Complete selected task
  d            Delete selected task
  r            Quick-rename selected task (inline, without opening detail)
  s            Schedule selected task (supports today, +3d, tomorrow, next monday, someday)
  m            Move / assign / tag — opens picker (folder → move, project → assign, tag → add)
  J / K        Move selected task down / up
  w            Move task to Waiting On  (Today view)
  t            Move to Today (Waiting On / Inbox) or schedule for today (user folders)
  y            Yank task to clipboard AND to internal register
  p / P        Paste a duplicate of yanked task below / above current position
  u            Undo last action
  Ctrl+R       Redo last undone action
  /            Global search  (plain → auto-detect regex; //pat → case-sensitive regex)
  n / N        Next / previous search match
  W            Weekly review (tasks completed in past 7 days)
  ?            Open this help screen
  5j / 3k      Count prefix: repeat any motion or J/K N times (e.g. 5j moves down 5)
  Dividers     Create a task titled - or = to insert a visual divider line

[bold]VISUAL Mode  (press v to enter)[/bold]
  v            Enter VISUAL mode — anchor selection at cursor
  j / k        Extend selection down / up
  H / M / L    Jump to top / middle / bottom of list (extends selection)
  x / Space    Complete all selected tasks
  d            Delete all selected tasks
  s            Schedule all selected tasks
  m            Move / assign / tag all selected tasks (same picker as NORMAL mode)
  w            Move all selected tasks to Waiting On
  t            Move to Today (Waiting On / Inbox) or schedule for today (user folders)
  y            Yank all selected tasks to clipboard (title + notes, blank line between)
  J / K        Move selected block down / up
  u            Undo last bulk action (exits VISUAL mode)
  Esc          Cancel selection and return to NORMAL mode

[bold]Task Detail View (opened with Enter)[/bold]
  j / k        Move to next / previous field
  i / a        Enter INSERT mode at / after cursor
  o / O        Edit field from end / start (single-line)
              or open new line below / above (notes)
  Enter        Confirm and advance to next field
  Ctrl+E       Open notes field in $EDITOR (nano if unset) — notes field must be focused
  Esc          Save and close
  Deadline     Hard due date — [bold red]red[/bold red] if overdue, [yellow]yellow[/yellow] if ≤3 days
  y            Yank current line to clipboard and internal register
  p / P        Paste register after / before cursor (or below / above in notes)

[bold]Sidebar Actions (sidebar focused)[/bold]
  H / M / L    Jump to top / middle / bottom of sidebar
  g g          Jump to top of sidebar
  G            Jump to bottom of sidebar
  o / O        Create new folder after / before selected
  A            Create new Area of responsibility
  r            Rename selected folder / project / area (pre-fills current name)
  d            Delete selected folder or project
  J / K        Reorder selected folder, project, or tag (area-scoped for folders/projects)
  m            Assign selected folder or project to an Area
  Enter        Collapse / expand Area (when on an Area header)
  ?            Open help screen

[bold]Projects (sidebar focused)[/bold]
  N            Create new project (works from anywhere in the sidebar)
  d            Delete selected project; if it has tasks prompts:
               [d]elete all tasks  [k]eep tasks unlinked  [Esc] cancel
  Enter / l    Open project sub-task list

[bold]INSERT Mode (task creation o/O)[/bold]
  Esc          Return to COMMAND mode (2nd Esc saves and exits)
  Enter        Save and exit
  Ctrl+c       Cancel without saving  (blank title also cancels)

[bold]Renames (r on task / folder / project / area)[/bold]
  Esc          Same as o/O: 1st Esc → COMMAND mode, 2nd Esc → save and exit
  Enter        Save and exit
  Ctrl+c       Cancel without saving

[bold]Commands  (type : then the command)[/bold]
  :help / :h   Show this help screen

[bold]CLI[/bold]
  gtd-tui -s             Print today's tasks to stdout and exit
  gtd-tui --backup-now   Create a one-shot backup of the data file and exit

[bold]General[/bold]
  q            Quit
  Ctrl+Z       Suspend to background (resume with fg)
  Config       ~/.config/gtd_tui/config.toml — [backup] rotating copies of data.json;
               [text] optional spell check / capitalization on save (see comments in file)

  j / k to scroll  ·  Esc, Enter, or q to close\
"""

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-scroll"):
            yield Static(self._HELP_TEXT)

    def on_key(self, event: events.Key) -> None:
        scroll = self.query_one("#help-scroll", VerticalScroll)
        if event.key == "j":
            scroll.scroll_down()
            event.prevent_default()
        elif event.key == "k":
            scroll.scroll_up()
            event.prevent_default()
        elif event.key in ("escape", "q", "enter"):
            self.dismiss()


class WeeklyReviewScreen(ModalScreen[None]):
    """Modal showing tasks completed in the past 7 days.

    Note: completed tasks all share folder_id='logbook' regardless of their
    origin folder, so results are shown as a flat chronological list rather
    than grouped by folder.
    """

    CSS = """
    WeeklyReviewScreen {
        align: center middle;
    }

    #review-scroll {
        width: 66;
        height: 30;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    """

    def __init__(self, tasks: list[Task]) -> None:
        super().__init__()
        self._tasks = tasks

    def _build_review_text(self) -> str:

        items = weekly_review_tasks(self._tasks)
        if not items:
            return "[dim]No tasks completed in the past 7 days.[/dim]"
        lines = [f"[bold]Completed in the past 7 days ({len(items)})[/bold]\n"]
        for task in items:
            done = (
                task.completed_at.strftime("%Y-%m-%d %H:%M")
                if task.completed_at
                else "unknown"
            )
            lines.append(f"  {markup_escape(task.title)}  [dim][{done}][/dim]")
        return "\n".join(lines)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="review-scroll"):
            yield Static(self._build_review_text())

    def on_key(self, event: events.Key) -> None:
        scroll = self.query_one("#review-scroll", VerticalScroll)
        if event.key == "j":
            scroll.scroll_down()
            event.prevent_default()
        elif event.key == "k":
            scroll.scroll_up()
            event.prevent_default()
        elif event.key in ("escape", "q", "enter", "W"):
            self.dismiss()


class TaskDetailScreen(
    ModalScreen[tuple[str, str, str, str, str, str, str, list[ChecklistItem]] | None]
):
    """Detail and edit view for a single task.

    Opens directly in edit mode with inputs pre-filled.
    j/k in COMMAND mode navigate between fields; Enter on single-line fields
    advances to the next; Esc always saves and closes.

    Dismissed value:
        (title, notes, date_text, deadline_text, repeat_text, recur_text, tags_raw,
         checklist)
    or None if title was cleared.  date_text / deadline_text are ISO (YYYY-MM-DD) or
    any parse_date_input format; empty = clear.  repeat_text / recur_text are raw
    strings (e.g. '7 days', empty = clear).  tags_raw is a comma-separated string.
    """

    BINDINGS = [
        # Not priority — VimInput absorbs Esc in INSERT mode itself; in COMMAND
        # mode it lets Esc bubble here so we can save and close.
        Binding("escape", "save_and_close", show=False),
        Binding("ctrl+c", "save_and_close", show=False),
        # priority=True so it fires before VimInput's ctrl+e end-of-line handler.
        Binding("ctrl+e", "open_external_editor", show=False, priority=True),
    ]

    CSS = """
    TaskDetailScreen {
        align: center middle;
    }

    #detail-panel {
        width: 70;
        height: 95%;
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

    #detail-date-input {
        margin-bottom: 1;
    }

    #detail-deadline-input {
        margin-bottom: 1;
    }

    #detail-notes-input {
        height: 7;
        margin-bottom: 1;
    }

    #detail-repeat-input {
        margin-bottom: 1;
    }

    #detail-recur-input {
        margin-bottom: 1;
    }

    #detail-checklist-header {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 0;
    }

    #detail-checklist-list {
        height: auto;
        max-height: 8;
        margin-bottom: 0;
        border: none;
    }

    #detail-checklist-list > ListItem.--highlight {
        background: $accent 40%;
    }

    #detail-checklist-new {
        margin-bottom: 1;
    }

    #detail-tags-input {
        margin-bottom: 1;
    }

    #detail-created {
        color: $text-muted;
        margin-top: 1;
    }

    #detail-status {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, task: Task) -> None:
        super().__init__()
        self._gtd_task = task
        self._checklist: list[ChecklistItem] = copy.deepcopy(task.checklist)
        # True when the user has pressed Enter to enter checklist item-navigation mode
        self._checklist_active: bool = False
        # Undo history for checklist mutations within this detail screen
        self._checklist_history: list[list[ChecklistItem]] = []
        # Non-empty item id when user is renaming a checklist item
        self._renaming_checklist_item_id: str = ""

    def compose(self) -> ComposeResult:
        repeat_val = (
            format_repeat_rule(self._gtd_task.repeat_rule)
            if self._gtd_task.repeat_rule
            else ""
        )
        recur_val = (
            format_recur_rule(self._gtd_task.recur_rule)
            if self._gtd_task.recur_rule
            else ""
        )
        date_val = (
            self._gtd_task.scheduled_date.isoformat()
            if self._gtd_task.scheduled_date
            else ""
        )
        deadline_val = (
            self._gtd_task.deadline.isoformat() if self._gtd_task.deadline else ""
        )
        with VerticalScroll(id="detail-panel"):
            yield Label("Edit Task", id="detail-header")
            yield Label("Title", classes="field-label")
            yield VimInput(
                value=self._gtd_task.title,
                start_mode="command",
                start_at_beginning=True,
                id="detail-title-input",
            )
            yield Label(
                "Date  (e.g. today, 2026-03-20, tomorrow, +7d, someday — empty to clear)",
                classes="field-label",
            )
            yield VimInput(
                value=date_val,
                placeholder="(none)",
                start_mode="command",
                id="detail-date-input",
            )
            yield Label(
                "Deadline  (hard due date — empty to clear)", classes="field-label"
            )
            yield VimInput(
                value=deadline_val,
                placeholder="(none)",
                start_mode="command",
                id="detail-deadline-input",
            )
            yield Label(
                "Notes  (Enter = newline  Ctrl+E = open in $EDITOR)",
                classes="field-label",
            )
            yield VimInput(
                value=self._gtd_task.notes,
                placeholder="(optional)",
                start_mode="command",
                multiline=True,
                start_at_beginning=True,
                id="detail-notes-input",
            )
            yield Label(
                "Checklist  (o: add  x/Space: toggle  d: delete  r: rename  J/K: reorder)",
                classes="field-label",
                id="detail-checklist-header",
            )
            yield ListView(id="detail-checklist-list")
            yield VimInput(
                value="",
                placeholder="Add checklist item…",
                start_mode="command",
                id="detail-checklist-new",
            )
            yield Label(
                "Repeat  (calendar-fixed — e.g. 7 days, M-F, MWF, TR, weekends, every Mon, every other Tue, 4th Thu, monthly, quarterly — empty to clear)",
                classes="field-label",
            )
            yield VimInput(
                value=repeat_val,
                placeholder="(none)",
                start_mode="command",
                id="detail-repeat-input",
            )
            yield Label(
                "Recurring  (after completion — e.g. 1 day, M-F, MWF, TR, every Mon, every other Tue, 4th Thu — empty to clear)",
                classes="field-label",
            )
            yield VimInput(
                value=recur_val,
                placeholder="(none)",
                start_mode="command",
                id="detail-recur-input",
            )
            yield Label(
                "Tags  (comma-separated, e.g. @home, @work — empty to clear)",
                classes="field-label",
            )
            yield VimInput(
                value=", ".join(self._gtd_task.tags),
                placeholder="(none)",
                start_mode="command",
                id="detail-tags-input",
            )
            if self._gtd_task.created_at:
                yield Label(
                    f"Created: {self._gtd_task.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                    id="detail-created",
                )
            yield Label(
                "j/k: next/prev field  Ctrl+E on notes: open $EDITOR  Enter on checklist: edit items  Esc: save & close",
                id="detail-status",
            )

    def on_mount(self) -> None:
        app = self.app
        if hasattr(app, "_spell_check_as_you_type_fn"):
            for wid, field in [
                ("#detail-title-input", "titles"),
                ("#detail-notes-input", "notes"),
            ]:
                inp = self.query_one(wid, VimInput)
                inp.set_spell_check_on_space(
                    app._spell_check_as_you_type_fn(field)  # type: ignore[union-attr]
                )
        self.query_one("#detail-title-input", VimInput).focus()
        self._render_checklist()

    @staticmethod
    def _checklist_label_text(item: "ChecklistItem") -> RichText:
        check = "[X]" if item.checked else "[ ]"
        return RichText(f"{check} {item.label}")

    def _checklist_push_undo(self) -> None:
        self._checklist_history.append(copy.deepcopy(self._checklist))

    def _render_checklist(
        self, restore_index: int | None = None, force_rebuild: bool = False
    ) -> None:
        """Refresh the checklist ListView with minimal DOM churn.

        Same count (toggle/reorder): update labels in place — highlight stays.
        One item deleted: update N-1 labels in place, remove the last DOM node
          — highlight is set synchronously on the already-mounted items.
        One item added: append a single new DOM node at the end.
        Any other delta or *force_rebuild*: full clear + rebuild (uses
          call_after_refresh for the index because DOM changes are async).
        """
        lv = self.query_one("#detail-checklist-list", ListView)
        existing = list(lv.query(ListItem))
        delta = len(self._checklist) - len(existing)

        if not force_rebuild and delta == 0:
            # In-place update — no DOM nodes added or removed.
            for list_item, checklist_item in zip(existing, self._checklist):
                list_item.query_one(Label).update(
                    self._checklist_label_text(checklist_item)
                )
            if restore_index is not None and self._checklist:
                lv.index = min(max(restore_index, 0), len(self._checklist) - 1)

        elif not force_rebuild and delta == -1:
            # One deleted: update survivors in place, drop the last DOM node.
            for list_item, checklist_item in zip(existing, self._checklist):
                list_item.query_one(Label).update(
                    self._checklist_label_text(checklist_item)
                )
            existing[-1].remove()
            if restore_index is not None and self._checklist:
                lv.index = min(max(restore_index, 0), len(self._checklist) - 1)

        elif not force_rebuild and delta == 1:
            # One added: just append the new node.
            lv.append(
                ListItem(
                    Label(self._checklist_label_text(self._checklist[-1]), markup=False)
                )
            )

        else:
            # Full rebuild (undo or multi-item change).
            lv.clear()
            for item in self._checklist:
                lv.append(
                    ListItem(Label(self._checklist_label_text(item), markup=False))
                )
            if restore_index is not None and self._checklist:
                target = min(max(restore_index, 0), len(self._checklist) - 1)
                self.call_after_refresh(lambda t=target: setattr(lv, "index", t))

    def _normalize_field(self, widget_id: str) -> None:
        """Rewrite a parseable field to its canonical form so the user can
        confirm their input was understood before closing the modal.
        Always returns the field to COMMAND mode afterwards."""
        inp = self.query_one(f"#{widget_id}", VimInput)
        raw = inp.value.strip()
        if not raw:
            inp.set_mode("command")
            return
        if widget_id in ("detail-date-input", "detail-deadline-input"):
            if widget_id == "detail-date-input" and raw.lower() == "someday":
                inp.value = "someday"
            else:
                try:
                    parsed = parse_date_input(raw)
                    inp.value = parsed.isoformat() if parsed else ""
                except InvalidDateError:
                    inp.value = "(invalid)"
        elif widget_id in ("detail-repeat-input", "detail-recur-input"):
            try:
                parsed_repeat = parse_repeat_input(raw)
                if parsed_repeat is None:
                    inp.value = ""
                else:
                    inp.value = format_parsed_repeat(parsed_repeat)
            except InvalidRepeatError:
                inp.value = "(invalid)"
        inp.set_mode("command")

    async def action_open_external_editor(self) -> None:
        """Open the notes field in $EDITOR (Ctrl+E).  Only acts when notes is focused."""
        import tempfile

        notes_input = self.query_one("#detail-notes-input", VimInput)
        if self.focused is not notes_input:
            return

        editor = os.environ.get("EDITOR", "nano")
        current_notes = notes_input.value

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(current_notes)
            tmp_path = f.name

        try:
            with self.app.suspend():
                result = subprocess.run([editor, tmp_path])  # noqa: S603
            if result.returncode == 0:
                with open(tmp_path, encoding="utf-8") as f:
                    notes_input.value = f.read().rstrip("\n")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def action_save_and_close(self) -> None:
        title = self.query_one("#detail-title-input", VimInput).value.strip()
        date_text = self.query_one("#detail-date-input", VimInput).value.strip()
        deadline_text = self.query_one("#detail-deadline-input", VimInput).value.strip()
        # Preserve internal newlines in notes; only strip leading/trailing whitespace.
        notes = (
            self.query_one("#detail-notes-input", VimInput).value.strip("\n").rstrip()
        )
        repeat = self.query_one("#detail-repeat-input", VimInput).value.strip()
        recur = self.query_one("#detail-recur-input", VimInput).value.strip()
        tags_raw = self.query_one("#detail-tags-input", VimInput).value.strip()
        self.dismiss(
            (
                title,
                notes,
                date_text,
                deadline_text,
                repeat,
                recur,
                tags_raw,
                self._checklist,
            )
            if title
            else None
        )

    def on_vim_input_submitted(self, event: VimInput.Submitted) -> None:
        if event.vim_input.id in (
            "detail-title-input",
            "detail-date-input",
            "detail-deadline-input",
            "detail-repeat-input",
            "detail-tags-input",
        ):
            self._normalize_field(event.vim_input.id)
            self.focus_next()
        elif event.vim_input.id == "detail-recur-input":
            self._normalize_field("detail-recur-input")
            self.action_save_and_close()
        elif event.vim_input.id == "detail-checklist-new":
            label = event.vim_input.value.strip()
            app = self.app
            if hasattr(app, "_normalize_user_text"):
                label = app._normalize_user_text("checklist", label)  # type: ignore[union-attr]
            if self._renaming_checklist_item_id:
                item_id = self._renaming_checklist_item_id
                self._renaming_checklist_item_id = ""
                if label:
                    self._checklist_push_undo()
                    self._checklist = [
                        (
                            ChecklistItem(id=it.id, label=label, checked=it.checked)
                            if it.id == item_id
                            else it
                        )
                        for it in self._checklist
                    ]
                    self._render_checklist()
                event.vim_input.value = ""
                event.vim_input.set_mode("command")
                lv = self.query_one("#detail-checklist-list", ListView)
                lv.focus()
                self._checklist_active = True
            else:
                if label:
                    self._checklist.append(ChecklistItem(label=label))
                    self._render_checklist()
                event.vim_input.value = ""
                event.vim_input.set_mode("insert")  # stay ready for the next item

    def on_key(self, event: events.Key) -> None:
        focused = self.focused

        # Esc on the add-item input: exit to checklist list (don't save & close).
        # VimInput absorbs Esc in INSERT mode (switches to COMMAND); when it's
        # already in COMMAND mode the key bubbles here — redirect focus instead.
        if (
            event.key == "escape"
            and isinstance(focused, VimInput)
            and focused.id == "detail-checklist-new"
        ):
            lv = self.query_one("#detail-checklist-list", ListView)
            lv.focus()
            if self._checklist:
                last = len(self._checklist) - 1
                self.call_after_refresh(lambda t=last: setattr(lv, "index", t))
                self._checklist_active = True
            event.stop()
            event.prevent_default()
            return

        # Checklist item-navigation mode (activated by Enter on the list).
        if (
            self._checklist_active
            and isinstance(focused, ListView)
            and focused.id == "detail-checklist-list"
        ):
            if event.key in ("escape", "enter"):
                self._checklist_active = False
                event.stop()
                event.prevent_default()
                return
            if event.key == "j":
                focused.action_cursor_down()
                event.stop()
                event.prevent_default()
                return
            if event.key == "k":
                focused.action_cursor_up()
                event.stop()
                event.prevent_default()
                return
            if event.key == "u":
                if self._checklist_history:
                    self._checklist = self._checklist_history.pop()
                    self._render_checklist(
                        restore_index=focused.index or 0, force_rebuild=True
                    )
                event.stop()
                event.prevent_default()
                return
            if event.key in ("x", "space"):
                cur: int | None = focused.index
                if cur is not None and 0 <= cur < len(self._checklist):
                    self._checklist_push_undo()
                    item = self._checklist[cur]
                    self._checklist[cur] = ChecklistItem(
                        id=item.id, label=item.label, checked=not item.checked
                    )
                    self._render_checklist(restore_index=cur)
                event.stop()
                event.prevent_default()
                return
            if event.key == "d":
                cur = focused.index
                if cur is not None and 0 <= cur < len(self._checklist):
                    self._checklist_push_undo()
                    self._checklist.pop(cur)
                    restore = max(0, cur - 1) if cur > 0 else 0
                    self._render_checklist(restore_index=restore)
                event.stop()
                event.prevent_default()
                return
            if event.key == "r":
                cur = focused.index
                if cur is not None and 0 <= cur < len(self._checklist):
                    item = self._checklist[cur]
                    self._renaming_checklist_item_id = item.id
                    new_inp = self.query_one("#detail-checklist-new", VimInput)
                    new_inp.value = item.label
                    new_inp.focus()
                    new_inp.set_mode("insert")
                    self._checklist_active = False
                event.stop()
                event.prevent_default()
                return
            if event.key in ("o", "O"):
                new_inp = self.query_one("#detail-checklist-new", VimInput)
                new_inp.focus()
                new_inp.set_mode("insert")
                self._checklist_active = False
                event.stop()
                event.prevent_default()
                return
            if event.key == "J":
                cur = focused.index
                if cur is not None and cur < len(self._checklist) - 1:
                    self._checklist_push_undo()
                    self._checklist[cur], self._checklist[cur + 1] = (
                        self._checklist[cur + 1],
                        self._checklist[cur],
                    )
                    self._render_checklist(restore_index=cur + 1)
                event.stop()
                event.prevent_default()
                return
            if event.key == "K":
                cur = focused.index
                if cur is not None and cur > 0:
                    self._checklist_push_undo()
                    self._checklist[cur], self._checklist[cur - 1] = (
                        self._checklist[cur - 1],
                        self._checklist[cur],
                    )
                    self._render_checklist(restore_index=cur - 1)
                event.stop()
                event.prevent_default()
                return
            # All other keys are consumed to prevent unintended field navigation.
            event.stop()
            event.prevent_default()
            return

        # Enter on the checklist list (not yet active): enter item-navigation mode.
        if (
            not self._checklist_active
            and isinstance(focused, ListView)
            and focused.id == "detail-checklist-list"
            and event.key == "enter"
            and self._checklist
        ):
            self._checklist_active = True
            if focused.index is None:
                focused.index = 0
            event.stop()
            event.prevent_default()
            return

        # ? on a date field: open the calendar picker
        if (
            event.key == "question_mark"
            and isinstance(focused, VimInput)
            and focused.id in ("detail-date-input", "detail-deadline-input")
        ):
            event.stop()
            event.prevent_default()
            field_id = focused.id

            def _on_calendar_close(result: "date | None") -> None:
                if result is None:
                    return
                inp = self.query_one(f"#{field_id}", VimInput)
                inp.value = result.isoformat()
                inp.set_mode("command")

            # Parse the current value as an initial date if possible.
            raw = focused.value.strip()
            try:
                initial = parse_date_input(raw) if raw else None
            except InvalidDateError:
                initial = None
            self.app.push_screen(CalendarScreen(initial=initial), _on_calendar_close)
            return

        # j/k field navigation (checklist list treated as a single field).
        if event.key == "j":
            if isinstance(focused, VimInput):
                self._normalize_field(focused.id or "")
            self.focus_next()
            event.stop()
            event.prevent_default()
        elif event.key == "k":
            if isinstance(focused, VimInput):
                self._normalize_field(focused.id or "")
            self.focus_previous()
            event.stop()
            event.prevent_default()


class SearchScreen(ModalScreen[tuple[str | None, str]]):
    """Global search across all tasks.

    Dismissed value: (task_id, query) where task_id is the selected task or
    None if cancelled, and query is the search string at dismiss time.
    """

    BINDINGS = [
        Binding("escape", "cancel", show=False, priority=True),
        Binding("ctrl+c", "cancel", show=False, priority=True),
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
        self._last_query: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="search-panel"):
            yield Label("Search", id="search-header")
            yield Input(placeholder="Type to search...", id="search-input")
            yield ListView(id="search-results")
            yield Label(
                "Enter: jump to results   ↑/↓/n/N: navigate   Enter: go to task   Esc: cancel",
                id="search-status",
            )

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self._run_search(event.value)

    async def _run_search(self, query: str) -> None:
        self._last_query = query
        results = search_tasks(self._tasks, query)
        list_view = self.query_one("#search-results", ListView)
        await list_view.clear()
        self._result_entries = []

        if not results:
            return

        active_results = [(t, mt) for t, mt in results if t.folder_id != "logbook"]
        logbook_results = [(t, mt) for t, mt in results if t.folder_id == "logbook"]

        def _escape(text: str) -> str:
            """Escape all [ in user text so Textual never treats them as markup."""
            return text.replace("[", "\\[")

        def _highlight(text: str, query: str) -> str:
            """Highlight the match in text. Handles // prefix and regex patterns."""
            import re as _re

            case_sensitive = query.startswith("//")
            pattern = query[2:] if case_sensitive else query
            if not pattern:
                return _escape(text)
            try:
                flags = 0 if case_sensitive else _re.IGNORECASE
                m = _re.search(pattern, text, flags)
                if m is None:
                    return _escape(text)
                before = _escape(text[: m.start()])
                match_text = _escape(text[m.start() : m.end()])
                after = _escape(text[m.end() :])
                return f"{before}[bold yellow]{match_text}[/bold yellow]{after}"
            except _re.error:
                # Fallback: plain substring search
                haystack = text if case_sensitive else text.lower()
                needle = pattern if case_sensitive else pattern.lower()
                idx = haystack.find(needle)
                if idx == -1:
                    return _escape(text)
                before = _escape(text[:idx])
                match_text = _escape(text[idx : idx + len(pattern)])
                after = _escape(text[idx + len(pattern) :])
                return f"{before}[bold yellow]{match_text}[/bold yellow]{after}"

        def _folder_tag(task: Task) -> str:
            folder_map = {
                "today": "Today",
                "waiting_on": "WO",
                "someday": "Someday",
                "upcoming": "Upcoming",
            }
            return folder_map.get(task.folder_id, task.folder_id[:8])

        new_items: list[ListItem] = []

        for task, match_type in active_results:
            tag = _folder_tag(task)
            tag_prefix = markup_escape(f"[{tag}]")
            if match_type == "notes":
                label_text = (
                    f"{tag_prefix} {_highlight(task.title, query)}  [dim](notes)[/dim]"
                )
            else:
                label_text = f"{tag_prefix} {_highlight(task.title, query)}"
            self._result_entries.append((task.id, task.title, False))
            new_items.append(ListItem(Label(label_text)))

        if active_results and logbook_results:
            self._result_entries.append(("", "", True))
            new_items.append(ListItem(Label("── Logbook ──")))

        for task, match_type in logbook_results:
            tag_prefix = markup_escape("[Logbook]")
            if match_type == "notes":
                label_text = (
                    f"{tag_prefix} {_highlight(task.title, query)}  [dim](notes)[/dim]"
                )
            else:
                label_text = f"{tag_prefix} {_highlight(task.title, query)}"
            self._result_entries.append((task.id, task.title, False))
            new_items.append(ListItem(Label(label_text)))

        if new_items:
            await list_view.extend(new_items)
            self._select_first()

    def _select_first(self) -> None:
        list_view = self.query_one("#search-results", ListView)
        for i, (_, _, is_sep) in enumerate(self._result_entries):
            if not is_sep:
                list_view.index = i
                return

    def action_cancel(self) -> None:
        self.dismiss((None, self._last_query))

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

    def on_key(self, event: events.Key) -> None:
        """Handle j/k/n/N navigation when the search input is not focused."""
        inp = self.query_one("#search-input", Input)
        if inp.has_focus:
            return  # let Input receive all keystrokes while typing
        if event.key in ("n", "j"):
            event.prevent_default()
            self.action_cursor_down()
        elif event.key in ("N", "k"):
            event.prevent_default()
            self.action_cursor_up()

    def action_select(self) -> None:
        inp = self.query_one("#search-input", Input)
        list_view = self.query_one("#search-results", ListView)
        if inp.has_focus:
            # First Enter: move focus to results so n/N/Enter can navigate them.
            # Also force the highlight — the DOM is settled by the time the user
            # presses Enter, so _select_first() is reliable here.
            list_view.focus()
            self._select_first()
            return
        idx = list_view.index
        if idx is None or idx >= len(self._result_entries):
            return
        task_id, _, is_sep = self._result_entries[idx]
        if is_sep:
            return
        self.dismiss((task_id, self._last_query))


class AreaPickerScreen(ModalScreen[str | None]):
    """Pick an area to assign to a folder or project."""

    BINDINGS = [
        Binding("escape", "cancel", show=False, priority=True),
        Binding("ctrl+c", "cancel", show=False, priority=True),
        Binding("enter", "select", show=False, priority=True),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    CSS = """
    AreaPickerScreen {
        align: center middle;
    }

    #area-picker-panel {
        width: 50;
        height: auto;
        max-height: 20;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #area-picker-header {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #area-picker-list {
        height: auto;
        max-height: 12;
    }
    """

    def __init__(self, areas: list[Area]) -> None:
        super().__init__()
        self._areas = areas

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="area-picker-panel"):
            yield Label("Assign to Area", id="area-picker-header")
            yield ListView(id="area-picker-list")

    def on_mount(self) -> None:
        lv = self.query_one("#area-picker-list", ListView)
        lv.append(ListItem(Label("(No area)")))
        for area in self._areas:
            lv.append(ListItem(Label(markup_escape(area.name))))
        lv.focus()
        lv.index = 0

    def action_select(self) -> None:
        lv = self.query_one("#area-picker-list", ListView)
        idx = lv.index
        if idx is None:
            return
        if idx == 0:
            self.dismiss(None)  # unassign
        else:
            self.dismiss(self._areas[idx - 1].id)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_cursor_down(self) -> None:
        self.query_one("#area-picker-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#area-picker-list", ListView).action_cursor_up()


class CalendarScreen(ModalScreen["date | None"]):
    """Modal calendar for date selection.

    Navigation:
        h / l         previous / next day
        j / k         next / previous week
        H / L         previous / next month
        Enter         confirm selected date
        q / Escape    cancel (returns None)

    The result is a ``date`` object or ``None`` when cancelled.
    """

    CSS = """
    CalendarScreen {
        align: center middle;
    }

    #cal-panel {
        width: 36;
        height: 14;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #cal-header {
        text-style: bold;
        color: $primary;
        text-align: center;
    }

    #cal-grid {
        height: 1fr;
    }

    #cal-status {
        height: 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", show=False, priority=True),
        Binding("q", "cancel", show=False, priority=True),
        Binding("enter", "confirm", show=False, priority=True),
    ]

    def __init__(self, initial: "date | None" = None) -> None:
        super().__init__()
        import calendar as _cal

        self._today: date = date.today()
        self._selected: date = initial if initial is not None else self._today
        self._month_year: tuple[int, int] = (
            self._selected.year,
            self._selected.month,
        )
        self._calendar = _cal.Calendar(firstweekday=0)  # Monday first

    def compose(self) -> ComposeResult:
        with Vertical(id="cal-panel"):
            yield Label("", id="cal-header")
            yield Static("", id="cal-grid")
            yield Label(
                "h/l: day  j/k: week  H/L: month  Enter: select  q: cancel",
                id="cal-status",
            )

    def on_mount(self) -> None:
        self._render_calendar()

    def _render_calendar(self) -> None:
        import calendar as _cal

        year, month = self._month_year
        header = self.query_one("#cal-header", Label)
        header.update(f"{_cal.month_name[month]} {year}")

        weeks = self._calendar.monthdayscalendar(year, month)
        day_headers = "Mo Tu We Th Fr Sa Su"
        lines = [day_headers]
        for week in weeks:
            row_parts = []
            for day in week:
                if day == 0:
                    row_parts.append("  ")
                elif date(year, month, day) == self._today:
                    row_parts.append(f"[bold]{day:2d}[/bold]")
                elif date(year, month, day) == self._selected:
                    row_parts.append(f"[reverse]{day:2d}[/reverse]")
                else:
                    row_parts.append(f"{day:2d}")
            lines.append(" ".join(row_parts))
        self.query_one("#cal-grid", Static).update("\n".join(lines))

    def _clamp_to_month(self, d: date) -> date:
        """Clamp a date to the valid range of the current displayed month."""
        import calendar as _cal

        year, month = self._month_year
        last_day = _cal.monthrange(year, month)[1]
        if d.year != year or d.month != month:
            # After navigation, the selected date may be outside the displayed month
            return d
        return date(year, month, min(d.day, last_day))

    def on_key(self, event: events.Key) -> None:
        import calendar as _cal
        from datetime import timedelta

        year, month = self._month_year
        sel = self._selected
        handled = True

        if event.key == "h":
            sel = sel - timedelta(days=1)
        elif event.key == "l":
            sel = sel + timedelta(days=1)
        elif event.key == "j":
            sel = sel + timedelta(weeks=1)
        elif event.key == "k":
            sel = sel - timedelta(weeks=1)
        elif event.key == "H":
            # Previous month
            if month == 1:
                year, month = year - 1, 12
            else:
                month -= 1
            last_day = _cal.monthrange(year, month)[1]
            sel = date(year, month, min(sel.day, last_day))
        elif event.key == "L":
            # Next month
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1
            last_day = _cal.monthrange(year, month)[1]
            sel = date(year, month, min(sel.day, last_day))
        else:
            handled = False

        if handled:
            event.prevent_default()
            self._selected = sel
            self._month_year = (sel.year, sel.month)
            self._render_calendar()

    def action_confirm(self) -> None:
        self.dismiss(self._selected)

    def action_cancel(self) -> None:
        self.dismiss(None)


_BORDER_COLORS: dict[str, tuple[str, str]] = {
    "yellow_grey": ("yellow", "bright_black"),
    "red_grey": ("red", "bright_black"),
}

_BLOCK_CHAR = "█"


class _FocusableEmptyHint(Label):
    """Label that can receive focus when the task list is empty so 'o' adds task not folder."""

    can_focus = True


class ColorBorderStrip(Static, can_focus=False):
    """Renders a strip of alternating-color block characters for a screen border."""

    DEFAULT_CSS = """
    ColorBorderStrip {
        background: transparent;
    }
    ColorBorderStrip.horizontal {
        height: 1;
        width: 1fr;
    }
    ColorBorderStrip.vertical {
        width: 1;
        height: 1fr;
    }
    """

    def __init__(
        self,
        style: str,
        block_size: int,
        orientation: str,
        border_text: str = "",
    ) -> None:
        super().__init__(classes=orientation)
        self._border_style = style
        self._block_size = max(1, block_size)
        self._orientation = orientation
        self._border_text = border_text

    def render(self) -> RichText:
        colors = _BORDER_COLORS.get(self._border_style, ("white", "bright_black"))
        primary_color = colors[0]
        if self._orientation == "horizontal":
            length = self.size.width or 80
            result = RichText()
            text = self._border_text
            if text:
                padded = f" {text} "
                text_len = len(padded)
                left_len = (length - text_len) // 2
                right_len = length - text_len - left_len
                for i in range(left_len):
                    result.append(
                        _BLOCK_CHAR, style=colors[(i // self._block_size) % 2]
                    )
                result.append(padded, style=f"on {primary_color} bold")
                right_start = left_len + text_len
                for i in range(right_start, right_start + right_len):
                    result.append(
                        _BLOCK_CHAR, style=colors[(i // self._block_size) % 2]
                    )
            else:
                for i in range(length):
                    result.append(
                        _BLOCK_CHAR, style=colors[(i // self._block_size) % 2]
                    )
            return result
        else:
            length = self.size.height or 24
            result = RichText()
            for i in range(length):
                result.append(_BLOCK_CHAR, style=colors[(i // self._block_size) % 2])
            return result


_THEMES: dict[str, dict[str, str]] = {
    "blue": {
        "primary": "#0178D4",
        "primary_dark": "#014A8A",
        "accent": "#0EA5E9",
    },
    "red": {
        "primary": "#C0392B",
        "primary_dark": "#8B1A13",
        "accent": "#E74C3C",
    },
    "yellow": {
        "primary": "#D4A017",
        "primary_dark": "#8A6800",
        "accent": "#F4C430",
    },
    "green": {
        "primary": "#1E8A3E",
        "primary_dark": "#0F5225",
        "accent": "#27AE60",
    },
}


class _ActionPickerScreen(ModalScreen["tuple[str, str] | None"]):
    """Modal that lets the user pick a move target: folder, project, or tag.

    Returns ``("folder", folder_id)``, ``("project", project_id)``,
    ``("tag", tag_name)``, or ``None`` on cancel.
    """

    DEFAULT_CSS = """
    _ActionPickerScreen {
        align: center middle;
    }
    #picker-outer {
        width: 50;
        height: 28;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }
    #picker-header {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    #picker-list {
        height: 1fr;
    }
    """

    def __init__(
        self,
        entries: "list[tuple[str, tuple[str, str] | None]]",
    ) -> None:
        """*entries*: list of ``(label, payload)`` where ``payload=None`` is a header."""
        super().__init__()
        self._picker_entries = entries

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-outer"):
            yield Label(
                "Move / Assign / Tag  (j/k H/M/L/G/gg Enter Esc)",
                id="picker-header",
            )
            yield ListView(id="picker-list")

    def on_mount(self) -> None:
        self._picker_pending_g = False
        lv = self.query_one("#picker-list", ListView)
        for label, payload in self._picker_entries:
            if payload is None:
                lv.append(
                    ListItem(Label(f"[dim]{label}[/dim]"), classes="section-header")
                )
            else:
                lv.append(ListItem(Label(label)))
        # Move cursor to first selectable item.
        for i, (_, payload) in enumerate(self._picker_entries):
            if payload is not None:
                lv.index = i
                break

    def _selectable_indices(self) -> list[int]:
        """Return indices of selectable rows (skip section headers)."""
        return [
            i
            for i, (_, payload) in enumerate(self._picker_entries)
            if payload is not None
        ]

    def on_key(self, event: events.Key) -> None:
        lv = self.query_one("#picker-list", ListView)
        n = len(self._picker_entries)
        selectable = self._selectable_indices()

        # gg chord: g then g
        pending = getattr(self, "_picker_pending_g", False)
        if pending and event.key == "g":
            self._picker_pending_g = False
            event.prevent_default()
            if selectable:
                lv.index = selectable[0]
            return
        self._picker_pending_g = False
        if event.key == "g":
            self._picker_pending_g = True
            return

        if event.key == "j":
            event.prevent_default()
            idx = (lv.index or 0) + 1
            while idx < n and self._picker_entries[idx][1] is None:
                idx += 1
            if idx < n:
                lv.index = idx
        elif event.key == "k":
            event.prevent_default()
            idx = (lv.index or 0) - 1
            while idx >= 0 and self._picker_entries[idx][1] is None:
                idx -= 1
            if idx >= 0:
                lv.index = idx
        elif event.key == "H":
            event.prevent_default()
            if selectable:
                lv.index = selectable[0]
        elif event.key in ("G", "L"):
            event.prevent_default()
            if selectable:
                lv.index = selectable[-1]
        elif event.key == "M":
            event.prevent_default()
            if selectable:
                lv.index = selectable[len(selectable) // 2]
        elif event.key in ("enter", "l"):
            event.prevent_default()
            idx = lv.index or 0
            if idx < n:
                payload = self._picker_entries[idx][1]
                if payload is not None:
                    self.dismiss(payload)
        elif event.key in ("escape", "q"):
            event.prevent_default()
            self.dismiss(None)


def _build_action_picker_entries(
    folders: "list",
    projects: "list",
    tags: "list[tuple[str, int]]",
) -> "list[tuple[str, tuple[str, str] | None]]":
    """Build the entry list for ``_ActionPickerScreen``."""
    from gtd_tui.gtd.folder import BUILTIN_FOLDER_IDS, REFERENCE_FOLDER_ID

    entries: list[tuple[str, tuple[str, str] | None]] = []

    entries.append(("── Folders ──", None))
    builtin_folders = [
        ("Inbox", "inbox"),
        ("Today", "today"),
        ("Waiting On", "waiting_on"),
        ("Someday", "someday"),
        ("Reference", REFERENCE_FOLDER_ID),
    ]
    for name, fid in builtin_folders:
        entries.append((name, ("folder", fid)))
    for folder in folders:
        if folder.id not in BUILTIN_FOLDER_IDS:
            entries.append((folder.name, ("folder", folder.id)))

    if projects:
        entries.append(("── Projects ──", None))
        for project in projects:
            entries.append((project.title, ("project", project.id)))

    if tags:
        entries.append(("── Tags (add) ──", None))
        for tag_name, _ in tags:
            entries.append((tag_name, ("tag", tag_name)))

    return entries


class GtdApp(App[None]):
    ESCAPE_TO_MINIMIZE = False  # prevent Textual's minimize-on-Esc delay

    BINDINGS = [
        Binding("escape", "cancel_insert_mode", priority=True, show=False),
        Binding("ctrl+c", "cancel_task_input", priority=True, show=False),
    ]

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

    #vim-input {
        margin: 0 1;
        display: none;
    }

    #vim-input.active {
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

    #task-list > ListItem.visual-selected {
        background: $accent 30%;
    }

    .sidebar-section-header {
        color: $text-muted;
        text-style: bold;
    }

    .sidebar-area-header {
        color: $text;
        text-style: bold;
    }

    #task-list > ListItem.section-header {
        background: $boost;
        color: $text-muted;
    }

    #border-outer {
        height: 1fr;
    }

    #app-inner {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(
        self,
        data_file: Path | None = None,
        password: str | None = None,
        tmux_tip: bool = False,
        config: Config | None = None,
    ) -> None:
        # _config must be set before super().__init__() because get_css_variables()
        # can be called during Textual's stylesheet initialisation.
        self._config: Config = config if config is not None else load_config()
        super().__init__()
        self._data_file: Path | None = data_file
        self._password: str | None = password
        self._tmux_tip: bool = tmux_tip
        self._all_tasks: list[Task] = load_tasks(data_file, password=password)
        self._all_folders: list[Folder] = load_folders(data_file, password=password)
        self._all_projects: list[Project] = load_projects(data_file, password=password)
        self._all_areas: list[Area] = load_areas(data_file, password=password)
        self._tag_order: list[str] = load_tag_order(data_file, password=password)
        self._collapsed_areas: set[str] = load_collapsed_areas(
            data_file, password=password
        )
        self._last_activity: float = time.monotonic()
        self._mode: str = "NORMAL"
        self._input_stage: str = (
            ""  # "title", "notes", "date", "command", "folder_name", "folder_rename", "project_name", "project_rename"
        )
        self._pending_title: str = ""
        self._pending_task_id: str = ""
        self._current_view: str = self._config.default_view
        # Parallel to ListView children: Task for rows, None for separators/placeholders
        self._list_entries: list[Task | None] = []
        self._undo_stack: UndoStack = load_undo_stack(data_file, password=password)
        self._redo_stack: UndoStack = load_redo_stack(data_file, password=password)
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
        # Rename project in progress
        self._rename_project_id: str = ""
        # Rename area in progress
        self._rename_area_id: str = ""
        # Delete project confirmation: non-empty ID means waiting for d/k/Esc
        self._delete_confirm_project_id: str = ""
        # Delete area confirmation: non-empty ID means waiting for d/Esc
        self._delete_confirm_area_id: str = ""
        # Task register: holds a yanked Task for duplication via p/P
        self._task_register: Task | None = None
        # Task rename from list: holds the task id being renamed
        self._rename_task_id: str = ""
        # Count prefix buffer for task-list navigation (e.g. "5j")
        self._count_buf: str = ""
        # Positional folder creation: anchor + position tracked during name entry
        self._folder_insert_position: str = "end"  # "after", "before", "end"
        self._folder_insert_anchor_id: str = ""
        # Sidebar placeholder shown while a folder name is being typed
        self._sidebar_placeholder_insert: str = ""  # same values as above; "" = none
        self._sidebar_placeholder_anchor_id: str = ""
        # VISUAL mode state
        self._visual_mode: bool = False
        self._visual_anchor_idx: int | None = None
        # On first mount, focus sidebar instead of task list (cleared after _apply_selection)
        self._initial_mount: bool = False
        # Pending task IDs for bulk operations (schedule, move)
        self._pending_task_ids: list[str] = []
        # Search navigation state (n / N)
        self._last_search_query: str = ""
        self._search_match_ids: list[str] = []
        self._search_match_idx: int = 0
        self._last_backup_monotonic: float = 0.0

    def _normalize_user_text(self, category: str, text: str) -> str:
        """Apply configured capitalization and spell correction for *category* keys."""
        if not text:
            return text
        t = self._config.text
        cap = (
            t.capitalization_fix_enabled
            and bool(getattr(t, f"capitalization_fix_{category}", False))
            and t.capitalization_fix_on_submit
        )
        spell = (
            t.spell_check_enabled
            and bool(getattr(t, f"spell_check_{category}", False))
            and t.spell_check_on_submit
        )
        result = text
        if cap:
            result = fix_capitalization(
                result, sentence_case=t.capitalization_sentence_case
            )
        if spell:
            result = fix_spelling(result)
        return result

    def _spell_check_as_you_type_fn(self, category: str):
        """Return spell-check callback for Space in INSERT, or None if disabled."""
        t = self._config.text
        if (
            not t.spell_check_enabled
            or not t.spell_check_as_you_type
            or not bool(getattr(t, f"spell_check_{category}", False))
        ):
            return None
        return fix_spelling

    @property
    def _sidebar_view_ids(self) -> list[str]:
        """Ordered list of view IDs parallel to the sidebar ListView items.

        When a new-folder placeholder is active, '__new_folder__' is included
        at the position where the placeholder row appears.
        """
        user_folders = sorted(self._all_folders, key=lambda f: f.position)
        ids: list[str] = ["inbox", "today", "upcoming", "waiting_on"]

        # Sort areas, all user folders, and active projects by position
        areas_sorted = sorted(self._all_areas, key=lambda a: a.position)
        active_projects_sorted = sorted(
            [p for p in self._all_projects if not p.is_complete],
            key=lambda p: p.position,
        )

        # Uncategorized (no area_id) user folders — with placeholder support
        uncategorized_folders = [f for f in user_folders if f.area_id is None]

        pos = self._sidebar_placeholder_insert
        anchor = self._sidebar_placeholder_anchor_id

        # Area sections (collapsible)
        for area in areas_sorted:
            ids.append(f"area:{area.id}")
            if area.id not in self._collapsed_areas:
                # Folders in this area (no placeholder support within areas for now)
                for f in user_folders:
                    if f.area_id == area.id:
                        ids.append(f.id)
                # Projects in this area
                for p in active_projects_sorted:
                    if p.area_id == area.id:
                        ids.append(f"project:{p.id}")

        # Uncategorized folders (no area_id), with placeholder support
        if not pos:
            ids += [f.id for f in uncategorized_folders]
        else:
            anchor_idx = next(
                (i for i, f in enumerate(uncategorized_folders) if f.id == anchor),
                None,
            )
            if pos == "end" or anchor_idx is None:
                ids += [f.id for f in uncategorized_folders]
                ids.append("__new_folder__")
            elif pos == "after":
                ids += [f.id for f in uncategorized_folders[: anchor_idx + 1]]
                ids.append("__new_folder__")
                ids += [f.id for f in uncategorized_folders[anchor_idx + 1 :]]
            else:  # "before"
                ids += [f.id for f in uncategorized_folders[:anchor_idx]]
                ids.append("__new_folder__")
                ids += [f.id for f in uncategorized_folders[anchor_idx:]]

        # Uncategorized projects (no area_id)
        uncategorized_projects = [
            p for p in active_projects_sorted if p.area_id is None
        ]
        if uncategorized_projects:
            ids.append("__projects_header__")
            ids += [f"project:{p.id}" for p in uncategorized_projects]

        ids += ["someday", REFERENCE_FOLDER_ID, "logbook"]
        tag_list = all_tags(self._all_tasks)
        if tag_list:
            ids.append("__tags_header__")
            # Use persisted order; append any new tags not yet in the order
            existing_tags = {tag for tag, _ in tag_list}
            ordered = [t for t in self._tag_order if t in existing_tags]
            ordered += sorted(existing_tags - set(ordered))
            ids += [f"tag:{tag}" for tag in ordered]
        return ids

    def _view_label(self, view_id: str) -> str:
        if view_id == "inbox":
            return "Inbox"
        if view_id == "today":
            return "Today"
        if view_id == "upcoming":
            return "Upcoming"
        if view_id == "waiting_on":
            return "Waiting On"
        if view_id == "someday":
            return "Someday"
        if view_id == REFERENCE_FOLDER_ID:
            return "Reference"
        if view_id == "logbook":
            return "Logbook"
        if view_id.startswith("area:"):
            area_id = view_id[5:]
            area = next((a for a in self._all_areas if a.id == area_id), None)
            return area.name if area else view_id
        if view_id.startswith("tag:"):
            return view_id[4:]
        if view_id.startswith("project:"):
            project_id = view_id[8:]
            proj = next((p for p in self._all_projects if p.id == project_id), None)
            return proj.title if proj else view_id
        for folder in self._all_folders:
            if folder.id == view_id:
                return folder.name
        return view_id

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        theme_name = self._config.theme
        if theme_name != "blue":
            t = _THEMES.get(theme_name, _THEMES["blue"])
            # Build a temporary Theme just to let Textual derive all variants
            # (primary-darken-1, accent-lighten-1, etc.) from the new base colors.
            custom = Theme(
                name="_gtd_custom",
                primary=t["primary"],
                accent=t["accent"],
                dark=True,
            )
            variables.update(custom.to_color_system().generate())
        return variables

    def _compose_main_content(self) -> ComposeResult:
        """Yield the core app widgets (header, sidebar+content, status)."""
        yield Label("Today", id="header")
        with Horizontal(id="main-area"):
            yield ListView(id="sidebar")
            with Vertical(id="content"):
                yield VimInput(placeholder="Task title...", id="vim-input")
                yield Input(placeholder="Task title...", id="task-input")
                yield ListView(id="task-list")
                yield _FocusableEmptyHint(
                    "No tasks — press o to add one", id="empty-hint"
                )
        yield Label("NORMAL  |  Today", id="status")

    def compose(self) -> ComposeResult:
        border = self._config.border_style
        bsize = self._config.border_block_size
        btext = self._config.border_text
        if border == "none":
            yield from self._compose_main_content()
        else:
            yield ColorBorderStrip(border, bsize, "horizontal", border_text=btext)
            with Horizontal(id="border-outer"):
                yield ColorBorderStrip(border, bsize, "vertical")
                with Vertical(id="app-inner"):
                    yield from self._compose_main_content()
                yield ColorBorderStrip(border, bsize, "vertical")
            yield ColorBorderStrip(border, bsize, "horizontal", border_text=btext)

    def on_mount(self) -> None:
        cfg_path = default_config_path()
        if not cfg_path.exists():
            try:
                save_default_config(cfg_path)
            except OSError:
                pass
        self._normalize_folder_positions()
        old_len = len(self._all_tasks)
        self._all_tasks = spawn_repeating_tasks(self._all_tasks)
        if len(self._all_tasks) != old_len:
            self._save()
        self._rebuild_sidebar()
        self._initial_mount = True
        self._refresh_list()
        self.set_interval(60, self._check_timeout)
        if self._tmux_tip:
            self._update_status(
                "tmux detected — for faster Esc: set-environment -g ESCDELAY 25 in ~/.tmux.conf"
            )

    def _check_timeout(self) -> None:
        """Called every 60 seconds; exits the app when idle too long."""
        if not self._config.timeout_enabled:
            return
        idle = time.monotonic() - self._last_activity
        limit = self._config.timeout_minutes * 60
        if idle >= limit:
            self.exit()
        elif idle >= (self._config.timeout_minutes - 5) * 60:
            # Show remaining time in status bar during the last 5 minutes.
            remaining = max(0, int((limit - idle) / 60))
            self._update_status(f"(auto-quit in {remaining}m)")

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

    def _rebuild_sidebar(self, cursor_view_id: str | None = None) -> None:
        """Repopulate the sidebar from built-ins + user folders.

        *cursor_view_id*, if provided, overrides *_current_view* when
        determining which sidebar row to highlight after the rebuild.
        Use this to keep the cursor on a non-task view such as an Area header.
        """
        self._rebuilding_sidebar = True
        sidebar = self.query_one("#sidebar", ListView)
        sidebar.clear()

        folder_map = {f.id: f for f in self._all_folders}
        counts = self._config.counts

        def _n(count: int) -> str:
            return f" ({count})"

        for view_id in self._sidebar_view_ids:
            if view_id == "inbox":
                suffix = _n(len(inbox_tasks(self._all_tasks))) if counts.inbox else ""
                sidebar.append(ListItem(Label(f"Inbox{suffix}")))
            elif view_id == "today":
                suffix = _n(len(today_tasks(self._all_tasks))) if counts.today else ""
                sidebar.append(ListItem(Label(f"Today{suffix}")))
            elif view_id == "upcoming":
                suffix = (
                    _n(len(upcoming_tasks(self._all_tasks))) if counts.upcoming else ""
                )
                sidebar.append(ListItem(Label(f"Upcoming{suffix}")))
            elif view_id == "waiting_on":
                suffix = (
                    _n(len(waiting_on_tasks(self._all_tasks)))
                    if counts.waiting_on
                    else ""
                )
                sidebar.append(ListItem(Label(f"Waiting On{suffix}")))
            elif view_id == "someday":
                suffix = (
                    _n(len(someday_tasks(self._all_tasks))) if counts.someday else ""
                )
                sidebar.append(ListItem(Label(f"Someday{suffix}")))
            elif view_id == REFERENCE_FOLDER_ID:
                suffix = (
                    _n(len(reference_tasks(self._all_tasks)))
                    if counts.reference
                    else ""
                )
                sidebar.append(ListItem(Label(f"Reference{suffix}")))
            elif view_id == "logbook":
                suffix = (
                    _n(len(logbook_tasks(self._all_tasks))) if counts.logbook else ""
                )
                sidebar.append(ListItem(Label(f"Logbook{suffix}")))
            elif view_id == "__new_folder__":
                sidebar.append(ListItem(Label("▸ …", classes="sidebar-placeholder")))
            elif view_id == "__projects_header__":
                sidebar.append(
                    ListItem(Label("── Projects ──", classes="sidebar-section-header"))
                )
            elif view_id.startswith("project:"):
                project_id = view_id[8:]
                project = next(
                    (p for p in self._all_projects if p.id == project_id), None
                )
                if project:
                    done, total = project_progress(self._all_tasks, project_id)
                    title_escaped = markup_escape(project.title)
                    dl = _project_deadline_label(project)
                    if dl is None:
                        dl_text = ""
                    elif dl[1] == "overdue":
                        dl_text = f"  [bold red]{markup_escape(dl[0])}[/bold red]"
                    elif dl[1] == "soon":
                        dl_text = f"  [yellow]{markup_escape(dl[0])}[/yellow]"
                    else:
                        dl_text = f"  {markup_escape(dl[0])}"
                    indent = "│ ◆ " if project.area_id else "  ◆ "
                    progress = f" ({done}/{total})" if counts.projects else ""
                    sidebar.append(
                        ListItem(Label(f"{indent}{title_escaped}{progress}{dl_text}"))
                    )
            elif view_id.startswith("area:"):
                area_id = view_id[5:]
                area = next((a for a in self._all_areas if a.id == area_id), None)
                if area:
                    collapsed = area_id in self._collapsed_areas
                    indicator = "▸" if collapsed else "▾"
                    sidebar.append(
                        ListItem(
                            Label(
                                f"{indicator} {markup_escape(area.name)}",
                                classes="sidebar-area-header",
                            )
                        )
                    )
            elif view_id == "__tags_header__":
                sidebar.append(
                    ListItem(Label("── Tags ──", classes="sidebar-section-header"))
                )
            elif view_id.startswith("tag:"):
                tag_name = view_id[4:]
                if counts.tags:
                    tag_count = sum(
                        1
                        for t in self._all_tasks
                        if tag_name in t.tags
                        and t.folder_id != "logbook"
                        and not t.is_deleted
                    )
                    tag_suffix = f" ({tag_count})"
                else:
                    tag_suffix = ""
                sidebar.append(
                    ListItem(Label(f"  {markup_escape(tag_name)}{tag_suffix}"))
                )
            else:
                folder = folder_map.get(view_id)
                if folder:
                    prefix = "│ " if folder.area_id else ""
                    folder_suffix = (
                        _n(len(folder_tasks(self._all_tasks, folder.id)))
                        if counts.user_folders
                        else ""
                    )
                    sidebar.append(
                        ListItem(Label(f"{prefix}{folder.name}{folder_suffix}"))
                    )

        view_ids = self._sidebar_view_ids
        target = cursor_view_id or self._current_view
        try:
            idx = view_ids.index(target)
        except ValueError:
            idx = 0
            if cursor_view_id is None:
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

    @staticmethod
    def _task_label(task: Task) -> str:
        """Build the display label for a task row, with recurrence and deadline markers."""
        if is_divider_task(task):
            char = "─" if task.title.strip() == "-" else "═"
            return f"[dim]{char * 60}[/dim]"
        rule = task.repeat_rule or task.recur_rule
        if rule is not None and (rule.days_of_week or rule.nth_weekday is not None):
            short = (
                format_repeat_rule(rule)
                if isinstance(rule, RepeatRule)
                else format_recur_rule(rule)
            )
            marker = f" ↻ {short}"
        elif rule is not None:
            marker = " ↻"
        else:
            marker = ""
        dl = deadline_status(task)
        if dl is None:
            dl_suffix = ""
        elif dl[1] == "overdue":
            dl_suffix = f"  [bold red]{markup_escape(dl[0])}[/bold red]"
        elif dl[1] == "soon":
            dl_suffix = f"  [yellow]{markup_escape(dl[0])}[/yellow]"
        else:
            dl_suffix = f"  {markup_escape(dl[0])}"
        tag_suffix = ""
        if task.tags:
            tag_suffix = "  " + "  ".join(
                f"[cyan]{markup_escape(tag)}[/cyan]" for tag in task.tags
            )
        checklist_suffix = ""
        if task.checklist:
            done = sum(1 for i in task.checklist if i.checked)
            checklist_suffix = f"  [dim][{done}/{len(task.checklist)}][/dim]"
        return f"{markup_escape(task.title)}{marker}{tag_suffix}{checklist_suffix}{dl_suffix}"

    def _refresh_list(self, select_task_id: str | None = None) -> None:
        list_view = self.query_one("#task-list", ListView)
        prev_index = list_view.index  # capture before clear resets it

        list_view.clear()
        self._list_entries = []
        self._placeholder_list_idx = None

        if self._current_view == "inbox":
            self._render_inbox_view(list_view)
        elif self._current_view == "today":
            self._render_today_view(list_view)
        elif self._current_view == "upcoming":
            self._render_upcoming_view(list_view)
        elif self._current_view == "waiting_on":
            self._render_waiting_on_view(list_view)
        elif self._current_view == "someday":
            self._render_someday_view(list_view)
        elif self._current_view == REFERENCE_FOLDER_ID:
            self._render_reference_view(list_view)
        elif self._current_view == "logbook":
            self._render_logbook_view(list_view)
        elif self._current_view.startswith("tag:"):
            self._render_tag_view(list_view, self._current_view[4:])
        elif self._current_view.startswith("project:"):
            self._render_project_view(list_view, self._current_view[8:])
        else:
            self._render_folder_view(list_view, self._current_view)

        # Compute the target index now (while _list_entries is current),
        # then defer the actual index + focus update until after Textual has
        # finished processing all the pending mount/remove messages from
        # clear() and append().  Setting index before the DOM settles causes
        # Textual to silently discard it, which makes the highlight vanish.
        target_idx = self._compute_target_index(select_task_id, prev_index)
        has_tasks = any(e is not None for e in self._list_entries)
        if target_idx is not None or not has_tasks:
            self.call_after_refresh(
                self._apply_selection, target_idx if target_idx is not None else 0
            )
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
            list_view.append(ListItem(Label(self._task_label(task))))

        if ph_at == len(today_only):
            self._placeholder_list_idx = len(self._list_entries)
            self._list_entries.append(None)
            list_view.append(ListItem(Label(" "), classes="placeholder"))

        if other:
            self._list_entries.append(None)
            list_view.append(ListItem(Label("── Also Due ──")))
            for task in other:
                self._list_entries.append(task)
                folder_label = self._view_label(task.folder_id)
                # Use \[ to prevent Rich from parsing [FolderName] as a style tag.
                label = f"\\[{markup_escape(folder_label)}] {self._task_label(task)}"
                list_view.append(ListItem(Label(label)))

    def _render_upcoming_view(self, list_view: ListView) -> None:
        tasks = upcoming_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Upcoming ({len(tasks)})")
        today = date.today()

        def _effective_date(t: Task) -> date | None:
            if t.scheduled_date is not None:
                return t.scheduled_date
            if t.repeat_rule is not None:
                return t.repeat_rule.next_due
            return None

        def _section_key(d: date) -> str:
            delta = (d - today).days
            if delta == 1:
                return "Tomorrow"
            if 2 <= delta <= 7:
                return d.strftime("%A")
            if delta <= 31 and d.month == today.month and d.year == today.year:
                return "This Month"
            if d.year == today.year:
                return d.strftime("%B")
            return d.strftime("%B %Y")

        last_section: str | None = None
        for task in tasks:
            eff_date = _effective_date(task)
            if eff_date is not None:
                section = _section_key(eff_date)
                if section != last_section:
                    last_section = section
                    self._list_entries.append(None)
                    list_view.append(
                        ListItem(Label(f"── {section} ──"), classes="section-header")
                    )
            date_str = (
                format_date_relative(eff_date, today=today)
                if eff_date is not None
                else ""
            )
            folder_hint = ""
            if task.folder_id != "today":
                folder_hint = f"  \\[{markup_escape(self._view_label(task.folder_id))}]"
            self._list_entries.append(task)
            list_view.append(
                ListItem(Label(f"{self._task_label(task)}  {date_str}{folder_hint}"))
            )

    def _render_simple_list(self, list_view: ListView, tasks: list[Task], label_fn) -> None:  # type: ignore[type-arg]
        """Render a flat ordered task list with placeholder support."""
        ph_at: int | None = None
        if self._show_placeholder:
            ph_at = self._placeholder_insert_idx(tasks)

        for i, task in enumerate(tasks):
            if ph_at == i:
                self._placeholder_list_idx = len(self._list_entries)
                self._list_entries.append(None)
                list_view.append(ListItem(Label(" "), classes="placeholder"))
            self._list_entries.append(task)
            list_view.append(ListItem(Label(label_fn(task))))

        if ph_at == len(tasks):
            self._placeholder_list_idx = len(self._list_entries)
            self._list_entries.append(None)
            list_view.append(ListItem(Label(" "), classes="placeholder"))

    def _render_waiting_on_view(self, list_view: ListView) -> None:
        tasks = waiting_on_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Waiting On ({len(tasks)})")

        def _wo_label(task: Task) -> str:
            date_str = (
                f"  [{format_date_relative(task.scheduled_date)}]"
                if task.scheduled_date
                else ""
            )
            return f"{self._task_label(task)}{date_str}"

        self._render_simple_list(list_view, tasks, _wo_label)

    def _render_inbox_view(self, list_view: ListView) -> None:
        tasks = inbox_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Inbox ({len(tasks)})")
        self._render_simple_list(list_view, tasks, self._task_label)

    def _render_someday_view(self, list_view: ListView) -> None:
        tasks = someday_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Someday ({len(tasks)})")
        self._render_simple_list(list_view, tasks, self._task_label)

    def _render_reference_view(self, list_view: ListView) -> None:
        tasks = reference_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Reference ({len(tasks)})")
        self._render_simple_list(list_view, tasks, self._task_label)

    def _render_logbook_view(self, list_view: ListView) -> None:
        tasks = logbook_tasks(self._all_tasks)
        self.query_one("#header", Label).update(f"Logbook ({len(tasks)})")
        for task in tasks:
            done = (
                task.completed_at.strftime("%Y-%m-%d %H:%M")
                if task.completed_at
                else "unknown"
            )
            created = (
                f"  created {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                if task.created_at
                else ""
            )
            marker = "D" if task.is_deleted else "C"
            self._list_entries.append(task)
            list_view.append(
                ListItem(
                    Label(f"{marker}  {markup_escape(task.title)}  [{done}]{created}")
                )
            )

    def _render_folder_view(self, list_view: ListView, folder_id: str) -> None:
        label = self._view_label(folder_id)
        tasks = folder_tasks(self._all_tasks, folder_id)
        self.query_one("#header", Label).update(f"{label} ({len(tasks)})")
        self._render_simple_list(list_view, tasks, self._task_label)

    def _render_tag_view(self, list_view: ListView, tag_name: str) -> None:
        tasks = tasks_with_tag(self._all_tasks, tag_name)
        self.query_one("#header", Label).update(
            f"{markup_escape(tag_name)} ({len(tasks)})"
        )
        self._render_simple_list(list_view, tasks, self._task_label)

    def _render_project_view(self, list_view: ListView, project_id: str) -> None:
        project = next((p for p in self._all_projects if p.id == project_id), None)
        if project is None:
            self.query_one("#header", Label).update("Project")
            return
        done, total = project_progress(self._all_tasks, project_id)
        self.query_one("#header", Label).update(
            f"{markup_escape(project.title)} ({done}/{total})"
        )
        tasks = project_tasks_including_completed(self._all_tasks, project_id)

        def _project_task_label(task: Task) -> str:
            base = self._task_label(task)
            return f"[strike]{base}[/strike]" if task.is_complete else base

        self._render_simple_list(list_view, tasks, _project_task_label)

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
        has_tasks = any(e is not None for e in self._list_entries)
        if has_tasks:
            list_view.index = idx
        sidebar = self.query_one("#sidebar", ListView)
        has_tasks = any(e is not None for e in self._list_entries)
        if getattr(self, "_initial_mount", False):
            self._initial_mount = False
            if self._config.startup_focus_sidebar:
                sidebar.focus()
            elif has_tasks:
                list_view.focus()
            else:
                self.query_one("#empty-hint", _FocusableEmptyHint).focus()
        elif self._mode == "NORMAL" and not sidebar.has_focus:
            if has_tasks:
                list_view.focus()
            else:
                self.query_one("#empty-hint", _FocusableEmptyHint).focus()

    _UNDO_CAP = 20

    def _push_undo(self) -> None:
        self._undo_stack.append(
            (
                copy.deepcopy(self._all_tasks),
                copy.deepcopy(self._all_folders),
                copy.deepcopy(self._all_projects),
                copy.deepcopy(self._all_areas),
            )
        )
        if len(self._undo_stack) > self._UNDO_CAP:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _update_status(self, message: str = "") -> None:
        if self._mode == "INSERT":
            mode = "INSERT"
        elif self._visual_mode:
            n = len(self._visual_selected_tasks)
            mode = f"VISUAL ({n})"
        else:
            mode = "NORMAL"
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
        self._normalize_tag_order()
        save_data(
            self._all_tasks,
            self._all_folders,
            self._data_file,
            password=self._password,
            undo_stack=self._undo_stack,
            redo_stack=self._redo_stack,
            projects=self._all_projects,
            areas=self._all_areas,
            tag_order=self._tag_order,
            collapsed_areas=self._collapsed_areas,
        )
        data_path = self._data_file or default_data_file_path()
        b = self._config.backup
        self._last_backup_monotonic = maybe_backup_after_save(
            data_path,
            enabled=b.enabled,
            backup_directory=b.directory,
            daily_keep=b.daily_keep,
            daily_slots_per_day=b.daily_slots_per_day,
            weekly_keep=b.weekly_keep,
            monthly_keep=b.monthly_keep,
            throttle_minutes=b.throttle_minutes,
            last_backup_monotonic=self._last_backup_monotonic,
            now_monotonic=time.monotonic(),
            gzip_backups=b.gzip,
        )

    def _task_to_yank_text(self, task: Task) -> str:
        """Return the clipboard representation of a single task."""
        if task.notes:
            return f"{task.title}\n{task.notes}"
        return task.title

    def _yank_task(self) -> None:
        """Copy the selected task(s) title and notes to the clipboard.

        In NORMAL mode: copies the single selected task.
        In VISUAL mode: copies all selected tasks separated by blank lines,
        then exits VISUAL mode.
        """
        if self._visual_mode:
            tasks = self._visual_selected_tasks
            if not tasks:
                self._exit_visual_mode()
                return
            text = "\n\n".join(self._task_to_yank_text(t) for t in tasks)
            self._exit_visual_mode()
        else:
            task = self._get_selected_task()
            if task is None:
                return
            text = self._task_to_yank_text(task)
        try:
            pyperclip.copy(text)
            self._update_status("(yanked to clipboard)")
        except pyperclip.PyperclipException:
            self._update_status("(clipboard not available)")

    # ------------------------------------------------------------------ #
    # Key handling                                                         #
    # ------------------------------------------------------------------ #

    def on_key(self, event: events.Key) -> None:
        # Track activity for the inactivity timeout.
        self._last_activity = time.monotonic()
        # Don't intercept keys when a modal overlay is active — let the modal handle them.
        if len(self.screen_stack) > 1:
            return
        # Ctrl-Z: suspend to background (SIGTSTP)
        if event.key == "ctrl+z":
            event.prevent_default()
            os.kill(os.getpid(), signal.SIGTSTP)
            return
        # Delete confirmations take priority
        if self._delete_confirm_folder_id:
            self._handle_delete_confirm_key(event)
            return
        if self._delete_confirm_project_id:
            self._handle_delete_confirm_project_key(event)
            return
        if self._delete_confirm_area_id:
            self._handle_delete_confirm_area_key(event)
            return
        if self._mode == "INSERT":
            # Escape and Ctrl+C handled by bindings (cancel_insert_mode, cancel_task_input)
            pass
        elif self._visual_mode:
            self._handle_visual_key(event)
        elif self.query_one("#sidebar", ListView).has_focus:
            self._handle_sidebar_key(event)
        else:
            self._handle_normal_key(event)

    def _handle_sidebar_key(self, event: events.Key) -> None:
        sidebar = self.query_one("#sidebar", ListView)

        # Move-mode: sidebar is acting as a folder picker
        if self._move_mode:
            n = len(self._sidebar_view_ids)
            if event.key == "j":
                event.prevent_default()
                self._pending_key = ""
                sidebar.action_cursor_down()
            elif event.key == "k":
                event.prevent_default()
                self._pending_key = ""
                sidebar.action_cursor_up()
            elif event.key == "H":
                event.prevent_default()
                self._pending_key = ""
                if n > 0:
                    sidebar.index = 0
            elif event.key == "M":
                event.prevent_default()
                self._pending_key = ""
                if n > 0:
                    sidebar.index = n // 2
            elif event.key in ("L", "G"):
                event.prevent_default()
                self._pending_key = ""
                if n > 0:
                    sidebar.index = n - 1
            elif self._pending_key == "g" and event.key == "g":
                event.prevent_default()
                self._pending_key = ""
                if n > 0:
                    sidebar.index = 0
            elif event.key == "g":
                self._pending_key = "g"
            elif event.key in ("l", "enter"):
                event.prevent_default()
                self._pending_key = ""
                self._confirm_move_task()
            elif event.key == "escape":
                event.prevent_default()
                self._pending_key = ""
                self._cancel_move_mode()
            return

        pending = self._pending_key
        self._pending_key = ""

        if pending == "g" and event.key == "g":
            event.prevent_default()
            if self._sidebar_view_ids:
                sidebar.index = 0
            return
        elif event.key == "g":
            self._pending_key = "g"
            return

        if event.key == "G":
            event.prevent_default()
            n = len(self._sidebar_view_ids)
            if n > 0:
                sidebar.index = n - 1
            return
        if event.key == "H":
            event.prevent_default()
            if self._sidebar_view_ids:
                sidebar.index = 0
            return
        if event.key == "M":
            event.prevent_default()
            n = len(self._sidebar_view_ids)
            if n > 0:
                sidebar.index = n // 2
            return
        if event.key == "L":
            event.prevent_default()
            n = len(self._sidebar_view_ids)
            if n > 0:
                sidebar.index = n - 1
            return
        if event.key == "j":
            event.prevent_default()
            sidebar.action_cursor_down()
        elif event.key == "k":
            event.prevent_default()
            sidebar.action_cursor_up()
        elif event.key == "J":
            event.prevent_default()
            idx = sidebar.index
            view_ids = self._sidebar_view_ids
            current_sid = (
                view_ids[idx] if idx is not None and idx < len(view_ids) else ""
            )
            if current_sid.startswith("project:"):
                self._move_selected_project_down()
            elif current_sid.startswith("tag:"):
                self._move_selected_tag_down()
            elif current_sid.startswith("area:"):
                self._move_selected_area_down()
            else:
                self._move_selected_folder_down()
        elif event.key == "K":
            event.prevent_default()
            idx = sidebar.index
            view_ids = self._sidebar_view_ids
            current_sid = (
                view_ids[idx] if idx is not None and idx < len(view_ids) else ""
            )
            if current_sid.startswith("project:"):
                self._move_selected_project_up()
            elif current_sid.startswith("tag:"):
                self._move_selected_tag_up()
            elif current_sid.startswith("area:"):
                self._move_selected_area_up()
            else:
                self._move_selected_folder_up()
        elif event.key in ("l", "enter"):
            event.prevent_default()
            # If the highlighted item is an area header, toggle collapse on Enter.
            idx = sidebar.index
            view_ids = self._sidebar_view_ids
            current_sid = (
                view_ids[idx] if idx is not None and idx < len(view_ids) else ""
            )
            if current_sid.startswith("area:"):
                area_id = current_sid[5:]
                if area_id in self._collapsed_areas:
                    self._collapsed_areas.discard(area_id)
                else:
                    self._collapsed_areas.add(area_id)
                self._save()
                self._rebuild_sidebar(cursor_view_id=current_sid)
            else:
                self.query_one("#task-list", ListView).focus()
        elif event.key == "o":
            event.prevent_default()
            self._start_create_folder("after")
        elif event.key == "O":
            event.prevent_default()
            self._start_create_folder("before")
        elif event.key == "N":
            event.prevent_default()
            self._start_new_project()
        elif event.key == "A":
            event.prevent_default()
            self._start_new_area()
        elif event.key == "m":
            event.prevent_default()
            self._start_assign_to_area()
        elif event.key == "r":
            event.prevent_default()
            idx = sidebar.index
            view_ids = self._sidebar_view_ids
            current_sid = (
                view_ids[idx] if idx is not None and idx < len(view_ids) else ""
            )
            if current_sid.startswith("project:"):
                self._start_rename_project()
            elif current_sid.startswith("area:"):
                self._start_rename_area()
            else:
                self._start_rename_folder()
        elif event.key == "d":
            event.prevent_default()
            idx = sidebar.index
            view_ids = self._sidebar_view_ids
            current_sid = (
                view_ids[idx] if idx is not None and idx < len(view_ids) else ""
            )
            if current_sid.startswith("project:"):
                self._delete_selected_project()
            elif current_sid.startswith("area:"):
                self._delete_selected_area()
            else:
                self._delete_selected_folder()
        elif event.key == "i":
            event.prevent_default()
            self._jump_to_view_id("inbox")
        elif event.key.isdigit():
            event.prevent_default()
            self._jump_to_view(int(event.key))
        elif event.key == "slash":
            event.prevent_default()
            self._open_search()
        elif event.key == "W":
            event.prevent_default()
            self._open_weekly_review()
        elif event.key == "u":
            event.prevent_default()
            self._undo()
        elif event.key == "ctrl+r":
            event.prevent_default()
            self._redo()
        elif event.key == "ctrl+d":
            event.prevent_default()
            step = max(1, sidebar.size.height // 2)
            n = len(self._sidebar_view_ids)
            if n > 0:
                sidebar.index = min(n - 1, (sidebar.index or 0) + step)
        elif event.key == "ctrl+u":
            event.prevent_default()
            step = max(1, sidebar.size.height // 2)
            if sidebar.index:
                sidebar.index = max(0, sidebar.index - step)
        elif event.key == "question_mark":
            event.prevent_default()
            self.push_screen(HelpScreen())
        elif event.key == "colon":
            event.prevent_default()
            self._start_command()
        elif event.key == "ctrl+c":
            event.prevent_default()
            # no-op in sidebar NORMAL mode; here for completeness
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

        # count is always 1 in the task list — count prefix lives in VimInput only.
        count = 1

        if event.key == "escape":
            event.prevent_default()
            return

        if event.key == "enter":
            event.prevent_default()
            self._open_task_detail()
            return
        elif event.key == "j":
            event.prevent_default()
            for _ in range(count):
                list_view.action_cursor_down()
                self._skip_separator(direction=1)
        elif event.key == "k":
            event.prevent_default()
            for _ in range(count):
                list_view.action_cursor_up()
                self._skip_separator(direction=-1)
        elif event.key == "G":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                # Ngg / NG: jump to row N (1-indexed); bare G = last row
                target = (
                    min(count - 1, n - 1)
                    if self._count_buf == "" and count > 1
                    else n - 1
                )
                if count > 1:
                    target = min(count - 1, n - 1)
                list_view.index = target
                self._skip_separator(direction=-1)
        elif event.key == "H":
            event.prevent_default()
            if self._list_entries:
                list_view.index = 0
                self._skip_separator(direction=1)
        elif event.key == "M":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                list_view.index = n // 2
                self._skip_separator(direction=1)
        elif event.key == "L":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                list_view.index = n - 1
                self._skip_separator(direction=-1)
        elif event.key == "ctrl+d":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                step = max(1, list_view.size.height // 2)
                new_idx = min(n - 1, (list_view.index or 0) + step)
                list_view.index = new_idx
                self._skip_separator(direction=1)
        elif event.key == "ctrl+u":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                step = max(1, list_view.size.height // 2)
                new_idx = max(0, (list_view.index or 0) - step)
                list_view.index = new_idx
                self._skip_separator(direction=-1)
        elif event.key == "n":
            event.prevent_default()
            self._navigate_search_match(1)
        elif event.key == "N":
            event.prevent_default()
            self._navigate_search_match(-1)
        elif event.key == "J":
            event.prevent_default()
            for _ in range(count):
                self._move_selected_down()
        elif event.key == "K":
            event.prevent_default()
            for _ in range(count):
                self._move_selected_up()
        elif event.key == "h":
            event.prevent_default()
            self.query_one("#sidebar", ListView).focus()
        elif event.key == "i":
            event.prevent_default()
            self._jump_to_view_id("inbox")
        elif event.key == "o":
            event.prevent_default()
            if self._current_view != "logbook":
                self._start_add_task("after")
        elif event.key == "O":
            event.prevent_default()
            if self._current_view != "logbook":
                self._start_add_task("before")
        elif event.key == "v":
            event.prevent_default()
            self._enter_visual_mode()
        elif event.key == "r":
            event.prevent_default()
            task = self._get_selected_task()
            if task is not None and not is_divider_task(task):
                self._start_rename_task_from_list(task)
        elif event.key == "s":
            event.prevent_default()
            task = self._get_selected_task()
            if task is not None and not is_divider_task(task):
                self._start_schedule()
        elif event.key == "m":
            event.prevent_default()
            task = self._get_selected_task()
            if task is not None and not is_divider_task(task):
                self._start_move_task()
        elif event.key == "u":
            event.prevent_default()
            self._undo()
        elif event.key == "ctrl+r":
            event.prevent_default()
            self._redo()
        elif event.key == "w" and (
            self._current_view == "today"
            or self._current_view == "inbox"
            or (
                self._current_view not in BUILTIN_FOLDER_IDS
                and self._current_view != REFERENCE_FOLDER_ID
            )
        ):
            event.prevent_default()
            task = self._get_selected_task()
            if task is None or not is_divider_task(task):
                self._move_selected_to_waiting_on()
        elif event.key == "t":
            event.prevent_default()
            task = self._get_selected_task()
            if task is None or not is_divider_task(task):
                self._handle_t_key()
        elif event.key == "x" or event.key == "space":
            event.prevent_default()
            task = self._get_selected_task()
            if task is None or not is_divider_task(task):
                self._complete_selected()
        elif event.key == "d":
            event.prevent_default()
            if self._current_view == "logbook":
                self._purge_logbook_entry()
            else:
                self._delete_selected()
        elif event.key == "y":
            event.prevent_default()
            task = self._get_selected_task()
            if task is not None:
                self._task_register = task
            self._yank_task()
        elif event.key == "p":
            event.prevent_default()
            self._paste_task_duplicate("after")
        elif event.key == "P":
            event.prevent_default()
            self._paste_task_duplicate("before")
        elif event.key.isdigit():
            event.prevent_default()
            self._jump_to_view(int(event.key))
        elif event.key == "slash":
            event.prevent_default()
            self._open_search()
        elif event.key == "W":
            event.prevent_default()
            self._open_weekly_review()
        elif event.key == "question_mark":
            event.prevent_default()
            self.push_screen(HelpScreen())
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
        if new_view in (
            "__new_folder__",
            "__tags_header__",
            "__projects_header__",
            self._current_view,
        ) or new_view.startswith("area:"):
            return
        self._current_view = new_view
        self._refresh_list()
        self._update_status()

    def _jump_to_view(self, idx: int) -> None:
        view_ids = self._sidebar_view_ids
        if 0 <= idx < len(view_ids):
            self.query_one("#sidebar", ListView).index = idx
            # on_list_view_highlighted handles the rest

    def _jump_to_view_id(self, view_id: str) -> None:
        view_ids = self._sidebar_view_ids
        try:
            idx = view_ids.index(view_id)
        except ValueError:
            return
        self.query_one("#sidebar", ListView).index = idx

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
            self._update_status(
                "(cannot add tasks to Upcoming — use Today or a folder)"
            )
            return
        task = self._get_selected_task()
        # Anchor on tasks that actually live in the current view.  Today is a
        # smart view so only today-folder tasks are reorderable; in all other
        # views every listed task belongs to that folder.
        if task is not None and task.folder_id == self._current_view:
            self._pending_anchor_id = task.id
        else:
            self._pending_anchor_id = ""
        self._pending_insert_position = insert_position
        self._show_placeholder = True
        self._mode = "INSERT"
        self._input_stage = "title"
        vim = self.query_one("#vim-input", VimInput)
        if self._current_view == "waiting_on":
            vim.set_placeholder("Waiting On task title...")
        elif self._current_view == "someday":
            vim.set_placeholder("Someday task title...")
        elif self._current_view == "inbox":
            vim.set_placeholder("Inbox task title...")
        elif self._current_view.startswith("project:"):
            vim.set_placeholder("Sub-task title...")
        elif self._current_view == REFERENCE_FOLDER_ID:
            vim.set_placeholder("Reference item title...")
        else:
            vim.set_placeholder("Task title...")
        vim.clear()
        vim.set_spell_check_on_space(self._spell_check_as_you_type_fn("titles"))
        vim.set_mode("insert")  # creation always starts in INSERT
        vim.add_class("active")
        vim.focus()
        self._update_status()
        self._refresh_list()  # show the placeholder row immediately

    def action_cancel_insert_mode(self) -> None:
        """Priority Esc handler: 2nd Esc=save during task creation; else cancel/close."""
        if len(self.screen_stack) > 1:
            # A modal is active.  If the focused widget is a VimInput in INSERT
            # sub-mode, let the VimInput handle Escape itself (it will switch to
            # COMMAND mode).  Otherwise forward to the screen's close action.
            focused = self.screen.focused
            if isinstance(focused, VimInput) and focused._vim_mode == "insert":
                focused.set_mode("command")
                return
            screen = self.screen
            if hasattr(screen, "action_save_and_close"):
                screen.action_save_and_close()  # type: ignore[union-attr]
            elif hasattr(screen, "action_cancel"):
                screen.action_cancel()  # type: ignore[union-attr]
            else:
                screen.dismiss()
            return
        # Task creation (o/O) and renames (r): 1st Esc → COMMAND mode; 2nd Esc → save & exit
        rename_stages = (
            "area_rename",
            "project_rename",
            "folder_rename",
            "task_rename",
        )
        if self._mode == "INSERT" and self._input_stage in (
            "title",
            "notes",
            *rename_stages,
        ):
            focused = self.screen.focused
            if isinstance(focused, VimInput) and (focused.id or "") == "vim-input":
                if focused._vim_mode == "insert":
                    focused.set_mode("command")
                    return
                if focused._vim_mode == "command":
                    focused.post_message(VimInput.Submitted(focused, focused.value))
                    return
        if self._mode == "INSERT":
            self._cancel_input()
        elif self._visual_mode:
            self._exit_visual_mode()

    def action_cancel_task_input(self) -> None:
        """Ctrl+C: cancel INSERT mode input (discard without saving)."""
        if self._mode == "INSERT":
            self._cancel_input()

    def _start_command(self) -> None:
        self._mode = "INSERT"
        self._input_stage = "command"
        inp = self.query_one("#task-input", Input)
        inp.placeholder = ":"
        inp.add_class("active")
        inp.focus()
        self._update_status(":")

    def _start_new_project(self) -> None:
        """Open the vim-input bar to capture a new project name."""
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_placeholder("New project name…")
        vim_input.set_spell_check_on_space(self._spell_check_as_you_type_fn("projects"))
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._input_stage = "project_name"
        self._mode = "INSERT"
        self._update_status()

    def _finish_new_project(self, title: str) -> None:
        """Create the new project from the captured title and navigate to it."""
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.remove_class("active")
        self._input_stage = ""
        self._mode = "NORMAL"
        if title.strip():
            self._push_undo()
            self._all_projects = add_project(self._all_projects, title.strip())
            new_proj = self._all_projects[-1]
            self._current_view = f"project:{new_proj.id}"
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _start_new_area(self) -> None:
        """Open the vim-input bar to capture a new area name."""
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_placeholder("New area name…")
        vim_input.set_spell_check_on_space(self._spell_check_as_you_type_fn("areas"))
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._input_stage = "area_name"
        self._mode = "INSERT"
        self._update_status()

    def _finish_new_area(self, name: str) -> None:
        """Create the new area from the captured name."""
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.remove_class("active")
        self._input_stage = ""
        self._mode = "NORMAL"
        if name.strip():
            self._all_areas = add_area(self._all_areas, name.strip())
            self._save()
            self._rebuild_sidebar()
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _start_assign_to_area(self) -> None:
        """Assign the currently-selected sidebar folder or project to an area."""
        if not self._all_areas:
            self._update_status("(no areas defined — press A to create one)")
            return
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        # Guard: only user folders and projects are assignable
        if (
            current_sid in BUILTIN_FOLDER_IDS
            or current_sid.startswith("__")
            or current_sid.startswith("tag:")
            or current_sid.startswith("area:")
        ):
            return

        if current_sid.startswith("project:"):
            project_id = current_sid[8:]

            def _on_area_pick(area_id: str | None) -> None:
                self._all_projects = assign_project_to_area(
                    self._all_projects, project_id, area_id
                )
                self._save()
                self._rebuild_sidebar()

            self.push_screen(AreaPickerScreen(self._all_areas), _on_area_pick)
        else:
            folder_id = current_sid

            def _on_area_pick_folder(area_id: str | None) -> None:
                self._all_folders = assign_folder_to_area(
                    self._all_folders, folder_id, area_id
                )
                self._save()
                self._rebuild_sidebar()

            self.push_screen(AreaPickerScreen(self._all_areas), _on_area_pick_folder)

    def on_vim_input_submitted(self, event: VimInput.Submitted) -> None:
        """Handle title/notes submission from the inline VimInput widget."""
        if event.vim_input.id != "vim-input":
            return  # guard against events leaking from modal screens
        value = event.value.strip()

        if self._input_stage == "title":
            if not value:
                self._cancel_input()
                return
            self._pending_title = self._normalize_user_text("titles", value)
            self._save_new_task("")

        elif self._input_stage == "notes":
            self._save_new_task(self._normalize_user_text("notes", value))

        elif self._input_stage == "project_name":
            self._finish_new_project(self._normalize_user_text("projects", value))

        elif self._input_stage == "area_name":
            self._finish_new_area(self._normalize_user_text("areas", value))

        elif self._input_stage == "folder_rename":
            if value and self._rename_folder_id:
                value = self._normalize_user_text("folders", value)
                self._all_folders = rename_folder(
                    self._all_folders, self._rename_folder_id, value
                )
                self._save()
                self._rebuild_sidebar()
                self._refresh_list()
            self._rename_folder_id = ""
            self._cancel_input()

        elif self._input_stage == "project_rename":
            if value and self._rename_project_id:
                value = self._normalize_user_text("projects", value.strip())
                self._all_projects = rename_project(
                    self._all_projects, self._rename_project_id, value
                )
                self._save()
                self._rebuild_sidebar()
                self._refresh_list()
            self._rename_project_id = ""
            self._cancel_input()

        elif self._input_stage == "area_rename":
            if value and self._rename_area_id:
                value = self._normalize_user_text("areas", value.strip())
                self._all_areas = rename_area(
                    self._all_areas, self._rename_area_id, value
                )
                self._save()
                self._rebuild_sidebar()
            self._rename_area_id = ""
            self._cancel_input()

        elif self._input_stage == "task_rename":
            if value and self._rename_task_id:
                value = self._normalize_user_text("titles", value.strip())
                self._push_undo()
                self._all_tasks = edit_task(
                    self._all_tasks, self._rename_task_id, title=value
                )
                self._save()
                self._refresh_list(select_task_id=self._rename_task_id)
            self._rename_task_id = ""
            self._cancel_input()

    def _save_new_task(self, notes: str) -> None:
        """Create the pending task with the given notes and clean up."""
        self._push_undo()
        new_id = str(uuid.uuid4())
        if self._current_view.startswith("project:"):
            project_id = self._current_view[8:]
            self._all_tasks = add_task_to_project(
                self._all_tasks, project_id, self._pending_title, notes=notes
            )
            # Override new_id to be the actual last-added task's id
            new_id = self._all_tasks[-1].id
        elif self._current_view == "waiting_on":
            if self._pending_anchor_id:
                if self._pending_insert_position == "before":
                    self._all_tasks = insert_waiting_on_task_before(
                        self._all_tasks,
                        self._pending_anchor_id,
                        self._pending_title,
                        notes=notes,
                        task_id=new_id,
                    )
                else:
                    self._all_tasks = insert_waiting_on_task_after(
                        self._all_tasks,
                        self._pending_anchor_id,
                        self._pending_title,
                        notes=notes,
                        task_id=new_id,
                    )
            else:
                self._all_tasks = add_waiting_on_task(
                    self._all_tasks, self._pending_title, notes=notes, task_id=new_id
                )
        elif (
            self._current_view in ("inbox", "someday", REFERENCE_FOLDER_ID)
            or self._current_view not in BUILTIN_FOLDER_IDS
        ):
            if self._pending_anchor_id:
                if self._pending_insert_position == "before":
                    self._all_tasks = insert_folder_task_before(
                        self._all_tasks,
                        self._current_view,
                        self._pending_anchor_id,
                        self._pending_title,
                        notes=notes,
                        task_id=new_id,
                    )
                else:
                    self._all_tasks = insert_folder_task_after(
                        self._all_tasks,
                        self._current_view,
                        self._pending_anchor_id,
                        self._pending_title,
                        notes=notes,
                        task_id=new_id,
                    )
            else:
                self._all_tasks = add_task_to_folder(
                    self._all_tasks,
                    self._current_view,
                    self._pending_title,
                    notes=notes,
                    task_id=new_id,
                )
        elif not self._pending_anchor_id:
            self._all_tasks = add_task(
                self._all_tasks, self._pending_title, notes=notes, task_id=new_id
            )
        elif self._pending_insert_position == "before":
            self._all_tasks = insert_task_before(
                self._all_tasks,
                self._pending_anchor_id,
                self._pending_title,
                notes=notes,
                task_id=new_id,
            )
        else:
            self._all_tasks = insert_task_after(
                self._all_tasks,
                self._pending_anchor_id,
                self._pending_title,
                notes=notes,
                task_id=new_id,
            )
        self._save()
        self._show_placeholder = False
        self._placeholder_list_idx = None
        self._rebuild_sidebar()
        self._refresh_list(select_task_id=new_id)
        self._cancel_input()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "task-input":
            return  # guard against events leaking from modal screens
        value = event.value.strip()

        if self._input_stage == "date":
            self._apply_date(value)

        elif self._input_stage == "command":
            self._cancel_input()
            if value in ("help", "h"):
                self.push_screen(HelpScreen())
            elif value:
                self._update_status(f"(unknown command: {value})")

        elif self._input_stage == "folder_name":
            self._sidebar_placeholder_insert = ""
            self._sidebar_placeholder_anchor_id = ""
            if value:
                value = self._normalize_user_text("folders", value)
                new_folder_id = str(uuid.uuid4())
                self._all_folders = insert_folder(
                    self._all_folders,
                    value,
                    anchor_id=self._folder_insert_anchor_id or None,
                    insert_position=self._folder_insert_position,
                    folder_id=new_folder_id,
                )
                self._save()
                self._current_view = new_folder_id
                self._rebuild_sidebar()
                self._refresh_list()
                self._cancel_input()
                self.query_one("#task-list", ListView).focus()
            else:
                self._rebuild_sidebar()
                self._cancel_input()

    def _cancel_input(self) -> None:
        vim = self.query_one("#vim-input", VimInput)
        vim.clear()
        vim.remove_class("active")
        inp = self.query_one("#task-input", Input)
        inp.clear()
        inp.remove_class("active")
        had_placeholder = self._show_placeholder
        had_sidebar_placeholder = bool(self._sidebar_placeholder_insert)
        self._mode = "NORMAL"
        self._input_stage = ""
        self._pending_title = ""
        self._pending_task_id = ""
        self._pending_task_ids = []
        self._pending_anchor_id = ""
        self._pending_insert_position = "after"
        self._show_placeholder = False
        self._placeholder_list_idx = None
        self._sidebar_placeholder_insert = ""
        self._sidebar_placeholder_anchor_id = ""
        self._rename_task_id = ""
        self._count_buf = ""
        self._update_status()
        if had_placeholder:
            self._refresh_list()  # removes placeholder; _apply_selection refocuses
        else:
            if had_sidebar_placeholder:
                self._rebuild_sidebar()
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
        if value.strip() == "?":

            def _on_calendar_pick(date_str: date | None) -> None:
                if date_str is not None:
                    self._apply_date(date_str.isoformat())

            self._cancel_input()
            self.push_screen(CalendarScreen(), _on_calendar_pick)
            return

        task_ids = (
            self._pending_task_ids
            if self._pending_task_ids
            else [self._pending_task_id]
        )
        if value.strip().lower() == "someday":
            self._push_undo()
            for tid in reversed(task_ids):
                self._all_tasks = unschedule_task(self._all_tasks, tid)
                self._all_tasks = move_task_to_folder(self._all_tasks, tid, "someday")
            self._rebuild_sidebar()
            self._save()
            self._refresh_list()
            self._cancel_input()
            return

        try:
            parsed = parse_date_input(value)
        except InvalidDateError:
            self._update_status("(invalid date)")
            self._cancel_input()
            return

        self._push_undo()
        for tid in task_ids:
            if parsed is None:
                self._all_tasks = unschedule_task(self._all_tasks, tid)
            else:
                self._all_tasks = schedule_task(self._all_tasks, tid, parsed)

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
        task_id = task.id
        entries = _build_action_picker_entries(
            self._all_folders,
            [p for p in self._all_projects if not p.is_complete],
            all_tags(self._all_tasks),
        )

        def _on_pick(result: "tuple[str, str] | None") -> None:
            if result is None:
                return
            self._apply_move_action([task_id], result)

        self.push_screen(_ActionPickerScreen(entries), _on_pick)

    def _confirm_move_task(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            self._cancel_move_mode()
            return
        target_folder_id = view_ids[idx]
        if target_folder_id == "upcoming":
            self._update_status(
                "(cannot move to Upcoming — schedule a date with 's' instead)"
            )
            self._cancel_move_mode()
            return
        self._push_undo()
        task_ids = (
            self._pending_task_ids
            if self._pending_task_ids
            else [self._pending_task_id]
        )
        for tid in reversed(task_ids):
            self._all_tasks = move_task_to_folder(
                self._all_tasks, tid, target_folder_id
            )
        first_task_id = task_ids[0] if task_ids else None
        self._save()
        self._move_mode = False
        self._pending_task_id = ""
        self._pending_task_ids = []
        self._current_view = target_folder_id
        self._rebuild_sidebar()
        self._refresh_list(select_task_id=first_task_id)
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _cancel_move_mode(self) -> None:
        self._move_mode = False
        self._pending_task_id = ""
        self._pending_task_ids = []
        self._update_status()
        self.query_one("#task-list", ListView).focus()

    def _start_rename_task_from_list(self, task: Task) -> None:
        """Open an inline rename input pre-filled with the task's current title."""
        self._rename_task_id = task.id
        self._mode = "INSERT"
        self._input_stage = "task_rename"
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_value_cursor_end(task.title)
        vim_input.set_placeholder("New title…")
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._update_status(
            "Rename: Enter to save, Esc Esc to save (Esc → command mode)"
        )

    def _paste_task_duplicate(self, position: str) -> None:
        """Paste a duplicate of the yanked task above or below the selection."""
        if self._task_register is None:
            self._update_status("(no task yanked — press y first)")
            return
        src = self._task_register
        anchor = self._get_selected_task()
        self._push_undo()

        import uuid as _uuid
        from dataclasses import replace as _replace
        from datetime import datetime as _dt

        # The duplicate lands in the anchor's folder (current view), not src's folder.
        target_folder = (
            anchor.folder_id
            if anchor is not None
            else (src.folder_id if src.folder_id != "logbook" else "inbox")
        )

        if anchor is not None:
            insert_pos = anchor.position + (1 if position == "after" else 0)
            # Shift tasks in the target folder at or beyond insert_pos.
            shifted: list[Task] = []
            for t in self._all_tasks:
                if t.folder_id == target_folder and t.position >= insert_pos:
                    shifted.append(_replace(t, position=t.position + 1))
                else:
                    shifted.append(t)
        else:
            shifted = list(self._all_tasks)
            insert_pos = (
                max(
                    (
                        t.position
                        for t in self._all_tasks
                        if t.folder_id == target_folder
                    ),
                    default=0,
                )
                + 1
            )

        new_id = str(_uuid.uuid4())
        dup = _replace(
            src,
            id=new_id,
            created_at=_dt.now(),
            is_deleted=False,
            completed_at=None,
            folder_id=target_folder,
            position=insert_pos,
        )
        self._all_tasks = shifted + [dup]
        self._save()
        self._refresh_list(select_task_id=new_id)
        self._update_status("(task duplicated)")

    def _open_task_detail(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        task_id = task.id
        old_repeat = task.repeat_rule
        old_recur = task.recur_rule
        old_date = task.scheduled_date
        old_deadline = task.deadline

        def _on_detail_close(
            result: (
                tuple[str, str, str, str, str, str, str, list[ChecklistItem]] | None
            ),
        ) -> None:
            if result is None:
                return
            (
                new_title,
                new_notes,
                date_text,
                deadline_text,
                repeat_text,
                recur_text,
                tags_raw,
                new_checklist,
            ) = result

            new_title = self._normalize_user_text("titles", new_title)
            new_notes = self._normalize_user_text("notes", new_notes)
            new_checklist = [
                ChecklistItem(
                    id=it.id,
                    label=self._normalize_user_text("checklist", it.label),
                    checked=it.checked,
                )
                for it in new_checklist
            ]

            # Parse date field.
            move_to_someday = date_text.strip().lower() == "someday"
            new_date = old_date
            if not move_to_someday:
                try:
                    new_date = parse_date_input(date_text)
                except InvalidDateError:
                    self._update_status(
                        "(invalid date — changes saved, date unchanged)"
                    )
                    new_date = old_date

            # Parse repeat field.
            new_repeat: RepeatRule | None = old_repeat
            try:
                parsed = parse_repeat_input(repeat_text)
                if parsed is None:
                    new_repeat = None
                elif (
                    old_repeat is not None
                    and old_repeat.interval == parsed.interval
                    and old_repeat.unit == parsed.unit
                    and old_repeat.days_of_week == parsed.days_of_week
                    and old_repeat.nth_weekday == parsed.nth_weekday
                ):
                    new_repeat = old_repeat  # preserve next_due unchanged
                else:
                    new_repeat = make_repeat_rule_from_parsed(parsed)
            except InvalidRepeatError:
                self._update_status(
                    "(invalid repeat — changes saved, repeat unchanged)"
                )
                new_repeat = old_repeat

            # Parse recur field.
            new_recur: RecurRule | None = old_recur
            try:
                parsed_recur = parse_repeat_input(recur_text)  # same format
                if parsed_recur is None:
                    new_recur = None
                else:
                    new_recur = RecurRule(
                        interval=parsed_recur.interval,
                        unit=parsed_recur.unit,
                        days_of_week=parsed_recur.days_of_week,
                        nth_weekday=parsed_recur.nth_weekday,
                    )
            except InvalidRepeatError:
                self._update_status(
                    "(invalid recurring — changes saved, recurring unchanged)"
                )
                new_recur = old_recur

            # Mutual exclusivity: if both are set, repeat wins and recur is cleared.
            if new_repeat is not None and new_recur is not None:
                new_recur = None
                self._update_status(
                    "(both repeat and recurring set — repeat takes precedence)"
                )

            # Parse deadline field.
            new_deadline = old_deadline
            try:
                new_deadline = parse_date_input(deadline_text)
            except InvalidDateError:
                self._update_status(
                    "(invalid deadline — changes saved, deadline unchanged)"
                )
                new_deadline = old_deadline

            new_tags = (
                [
                    self._normalize_user_text("tags", t.strip())
                    for t in tags_raw.split(",")
                    if t.strip()
                ]
                if tags_raw
                else []
            )
            old_tags = task.tags

            title_changed = new_title != task.title or new_notes != task.notes
            date_changed = move_to_someday or (new_date != old_date)
            deadline_changed = new_deadline != old_deadline
            repeat_changed = new_repeat != old_repeat
            recur_changed = new_recur != old_recur
            tags_changed = new_tags != old_tags
            checklist_changed = new_checklist != task.checklist
            if not (
                title_changed
                or date_changed
                or deadline_changed
                or repeat_changed
                or recur_changed
                or tags_changed
                or checklist_changed
            ):
                return

            self._push_undo()
            if title_changed:
                self._all_tasks = edit_task(
                    self._all_tasks, task_id, new_title, new_notes
                )
            if move_to_someday:
                self._all_tasks = unschedule_task(self._all_tasks, task_id)
                self._all_tasks = move_task_to_folder(
                    self._all_tasks, task_id, "someday"
                )
            elif date_changed:
                if new_date is None:
                    self._all_tasks = unschedule_task(self._all_tasks, task_id)
                else:
                    self._all_tasks = schedule_task(self._all_tasks, task_id, new_date)
            if deadline_changed:
                if new_deadline is None:
                    self._all_tasks = clear_deadline(self._all_tasks, task_id)
                else:
                    self._all_tasks = set_deadline(
                        self._all_tasks, task_id, new_deadline
                    )
            if repeat_changed:
                self._all_tasks = set_repeat_rule(self._all_tasks, task_id, new_repeat)
            if recur_changed:
                self._all_tasks = set_recur_rule(self._all_tasks, task_id, new_recur)
            if tags_changed:
                self._all_tasks = set_tags(self._all_tasks, task_id, new_tags)
            if checklist_changed:
                from dataclasses import replace as dc_replace

                self._all_tasks = [
                    dc_replace(t, checklist=new_checklist) if t.id == task_id else t
                    for t in self._all_tasks
                ]
            self._rebuild_sidebar()
            self._save()
            self._refresh_list(select_task_id=task_id)

        self.push_screen(TaskDetailScreen(task), _on_detail_close)

    def _open_weekly_review(self) -> None:
        self.push_screen(WeeklyReviewScreen(self._all_tasks))

    def _open_search(self) -> None:
        def _on_search_close(
            result: tuple[str | None, str] | None,
        ) -> None:
            if result is None:
                self.query_one("#task-list", ListView).focus()
                return
            task_id, query = result
            # Store match list for n/N navigation (active tasks only)
            if query:
                matched = search_tasks(self._all_tasks, query)
                self._last_search_query = query
                self._search_match_ids = [
                    t.id for t, _ in matched if t.folder_id != "logbook"
                ]
                if task_id and task_id in self._search_match_ids:
                    self._search_match_idx = self._search_match_ids.index(task_id)
                else:
                    self._search_match_idx = 0
            if task_id is None:
                self.query_one("#task-list", ListView).focus()
                return
            task = next((t for t in self._all_tasks if t.id == task_id), None)
            if task is None:
                self.query_one("#task-list", ListView).focus()
                return
            # Navigate to the task's folder
            self._current_view = task.folder_id
            self._rebuild_sidebar()
            self._refresh_list(select_task_id=task_id)

        self.push_screen(SearchScreen(self._all_tasks), _on_search_close)

    def _navigate_search_match(self, direction: int) -> None:
        """Cycle through stored search matches (n = forward, N = backward)."""
        if not self._search_match_ids:
            return
        self._search_match_idx = (self._search_match_idx + direction) % len(
            self._search_match_ids
        )
        task_id = self._search_match_ids[self._search_match_idx]
        task = next((t for t in self._all_tasks if t.id == task_id), None)
        if task is None:
            return
        self._current_view = task.folder_id
        self._rebuild_sidebar()
        self._refresh_list(select_task_id=task_id)

    # ------------------------------------------------------------------ #
    # VISUAL mode                                                          #
    # ------------------------------------------------------------------ #

    @property
    def _visual_selected_tasks(self) -> list[Task]:
        """Tasks in the current VISUAL selection range (separators and dividers excluded)."""
        list_view = self.query_one("#task-list", ListView)
        cursor = list_view.index
        if self._visual_anchor_idx is None or cursor is None:
            return []
        lo = min(self._visual_anchor_idx, cursor)
        hi = max(self._visual_anchor_idx, cursor)
        return [
            t
            for t in self._list_entries[lo : hi + 1]
            if t is not None and not is_divider_task(t)
        ]

    def _enter_visual_mode(self) -> None:
        if self._get_selected_task() is None:
            return
        list_view = self.query_one("#task-list", ListView)
        self._visual_mode = True
        self._visual_anchor_idx = list_view.index
        self._refresh_visual_highlights()
        self._update_status()

    def _exit_visual_mode(self) -> None:
        self._visual_mode = False
        self._visual_anchor_idx = None
        self._clear_visual_highlights()
        self._update_status()

    def _refresh_visual_highlights(self) -> None:
        list_view = self.query_one("#task-list", ListView)
        cursor = list_view.index
        items = list(list_view.query(ListItem))
        lo = min(self._visual_anchor_idx or 0, cursor or 0)
        hi = max(self._visual_anchor_idx or 0, cursor or 0)
        for i, item in enumerate(items):
            in_range = (
                lo <= i <= hi
                and i < len(self._list_entries)
                and self._list_entries[i] is not None
            )
            if in_range:
                item.add_class("visual-selected")
            else:
                item.remove_class("visual-selected")

    def _clear_visual_highlights(self) -> None:
        for item in self.query_one("#task-list", ListView).query(ListItem):
            item.remove_class("visual-selected")

    def _handle_visual_key(self, event: events.Key) -> None:
        list_view = self.query_one("#task-list", ListView)

        if event.key == "escape":
            event.prevent_default()
            self._exit_visual_mode()

        elif event.key == "j":
            event.prevent_default()
            list_view.action_cursor_down()
            self._skip_separator(direction=1)
            self._refresh_visual_highlights()
            self._update_status()

        elif event.key == "k":
            event.prevent_default()
            list_view.action_cursor_up()
            self._skip_separator(direction=-1)
            self._refresh_visual_highlights()
            self._update_status()

        elif event.key == "H":
            event.prevent_default()
            if self._list_entries:
                list_view.index = 0
                self._skip_separator(direction=1)
                self._refresh_visual_highlights()
                self._update_status()

        elif event.key == "M":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                list_view.index = n // 2
                self._skip_separator(direction=1)
                self._refresh_visual_highlights()
                self._update_status()

        elif event.key == "L":
            event.prevent_default()
            n = len(self._list_entries)
            if n > 0:
                list_view.index = n - 1
                self._skip_separator(direction=-1)
                self._refresh_visual_highlights()
                self._update_status()

        elif event.key in ("x", "space"):
            event.prevent_default()
            self._bulk_complete()

        elif event.key == "d":
            event.prevent_default()
            self._bulk_delete()

        elif event.key == "s":
            event.prevent_default()
            self._bulk_start_schedule()

        elif event.key == "m":
            event.prevent_default()
            self._bulk_start_move()

        elif event.key == "w":
            event.prevent_default()
            self._bulk_move_to_waiting_on()

        elif event.key == "t":
            event.prevent_default()
            self._bulk_handle_t_key()

        elif event.key == "J":
            event.prevent_default()
            self._bulk_move_block_down()

        elif event.key == "K":
            event.prevent_default()
            self._bulk_move_block_up()

        elif event.key == "y":
            event.prevent_default()
            self._yank_task()

        elif event.key == "u":
            event.prevent_default()
            self._exit_visual_mode()
            self._undo()

        elif event.key == "ctrl+r":
            event.prevent_default()
            self._exit_visual_mode()
            self._redo()

    def _bulk_complete(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        self._push_undo()
        project_ids = {t.project_id for t in tasks if t.project_id}
        for task in tasks:
            self._all_tasks = complete_task(self._all_tasks, task.id)
        for pid in project_ids:
            self._all_projects = check_auto_complete_project(
                self._all_tasks, self._all_projects, pid
            )
        self._exit_visual_mode()
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _bulk_delete(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        self._push_undo()
        if self._current_view == "logbook":
            for task in tasks:
                self._all_tasks = purge_logbook_task(self._all_tasks, task.id)
        else:
            for task in tasks:
                self._all_tasks = delete_task(self._all_tasks, task.id)
        self._exit_visual_mode()
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _bulk_start_schedule(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        self._pending_task_ids = [t.id for t in tasks]
        self._exit_visual_mode()
        self._mode = "INSERT"
        self._input_stage = "date"
        inp = self.query_one("#task-input", Input)
        inp.value = ""
        inp.placeholder = f"Date for {len(self._pending_task_ids)} tasks: tomorrow/+3d/... (empty=clear)"
        inp.add_class("active")
        inp.focus()
        self._update_status()

    def _bulk_start_move(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        task_ids = [t.id for t in tasks]
        self._exit_visual_mode()
        entries = _build_action_picker_entries(
            self._all_folders,
            [p for p in self._all_projects if not p.is_complete],
            all_tags(self._all_tasks),
        )

        def _on_pick(result: "tuple[str, str] | None") -> None:
            if result is None:
                return
            self._apply_move_action(task_ids, result)

        self.push_screen(_ActionPickerScreen(entries), _on_pick)

    def _apply_move_action(
        self, task_ids: list[str], result: "tuple[str, str]"
    ) -> None:
        """Apply a picker selection to a list of task IDs."""
        action_type, target_id = result
        self._push_undo()
        if action_type == "folder":
            if target_id == "upcoming":
                self._update_status(
                    "(cannot move to Upcoming — schedule a date with 's' instead)"
                )
                return
            for tid in reversed(task_ids):
                self._all_tasks = move_task_to_folder(self._all_tasks, tid, target_id)
            first_task_id = task_ids[0] if task_ids else None
            self._current_view = target_id
            self._save()
            self._rebuild_sidebar()
            self._refresh_list(select_task_id=first_task_id)
            self._update_status()
        elif action_type == "project":
            from dataclasses import replace as _dc_replace

            for tid in task_ids:
                self._all_tasks = assign_task_to_project(
                    self._all_tasks, tid, target_id
                )
                # Detach from its current folder — the task now lives in the project view.
                self._all_tasks = [
                    _dc_replace(t, folder_id="") if t.id == tid else t
                    for t in self._all_tasks
                ]
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status("(assigned to project)")
        elif action_type == "tag":
            for tid in task_ids:
                self._all_tasks = add_tag_to_task(self._all_tasks, tid, target_id)
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status(f"(tag '{target_id}' added)")

    def _bulk_move_to_waiting_on(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        self._push_undo()
        for task in reversed(tasks):
            self._all_tasks = move_to_waiting_on(self._all_tasks, task.id)
        self._exit_visual_mode()
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _bulk_move_to_today(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        self._push_undo()
        for task in reversed(tasks):
            self._all_tasks = move_to_today(self._all_tasks, task.id)
        self._exit_visual_mode()
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _bulk_handle_t_key(self) -> None:
        """Context-aware t in VISUAL mode: move to Today or schedule in-place."""
        tasks = self._visual_selected_tasks
        if not tasks:
            self._exit_visual_mode()
            return
        if self._current_view in ("waiting_on", "inbox"):
            self._bulk_move_to_today()
        elif self._current_view not in BUILTIN_FOLDER_IDS:
            self._push_undo()
            for task in tasks:
                self._all_tasks = schedule_task(self._all_tasks, task.id, date.today())
            self._exit_visual_mode()
            self._save()
            self._refresh_list()

    def _bulk_move_block_down(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks or any(not self._can_reorder(t) for t in tasks):
            return
        _anchor_entry = (
            self._list_entries[self._visual_anchor_idx]
            if self._visual_anchor_idx is not None
            and self._visual_anchor_idx < len(self._list_entries)
            else None
        )
        anchor_id = _anchor_entry.id if _anchor_entry is not None else None
        selected_ids = {t.id for t in tasks}
        self._push_undo()
        self._all_tasks = move_block_down(self._all_tasks, selected_ids)
        self._save()
        self._refresh_list()
        self.call_after_refresh(
            lambda: self._restore_visual_after_block_move(selected_ids, anchor_id)
        )

    def _bulk_move_block_up(self) -> None:
        tasks = self._visual_selected_tasks
        if not tasks or any(not self._can_reorder(t) for t in tasks):
            return
        _anchor_entry = (
            self._list_entries[self._visual_anchor_idx]
            if self._visual_anchor_idx is not None
            and self._visual_anchor_idx < len(self._list_entries)
            else None
        )
        anchor_id = _anchor_entry.id if _anchor_entry is not None else None
        selected_ids = {t.id for t in tasks}
        self._push_undo()
        self._all_tasks = move_block_up(self._all_tasks, selected_ids)
        self._save()
        self._refresh_list()
        self.call_after_refresh(
            lambda: self._restore_visual_after_block_move(selected_ids, anchor_id)
        )

    def _restore_visual_after_block_move(
        self, selected_ids: set[str], anchor_id: str | None
    ) -> None:
        """Re-establish VISUAL selection on moved tasks after a DOM rebuild."""
        selected_indices = [
            i
            for i, entry in enumerate(self._list_entries)
            if entry is not None and entry.id in selected_ids
        ]
        if not selected_indices:
            return
        new_anchor = (
            next(
                (
                    i
                    for i, e in enumerate(self._list_entries)
                    if e is not None and e.id == anchor_id
                ),
                selected_indices[0],
            )
            if anchor_id
            else selected_indices[0]
        )
        list_view = self.query_one("#task-list", ListView)
        self._visual_mode = True
        self._visual_anchor_idx = new_anchor
        list_view.index = max(selected_indices)
        self._refresh_visual_highlights()
        self._update_status()

    def _move_selected_to_waiting_on(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_to_waiting_on(self._all_tasks, task.id)
        self._save()
        self._current_view = "waiting_on"
        self._rebuild_sidebar()
        self._refresh_list(select_task_id=task.id)

    def _move_selected_to_today(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = move_to_today(self._all_tasks, task.id)
        self._save()
        self._current_view = "today"
        self._rebuild_sidebar()
        self._refresh_list(select_task_id=task.id)

    def _handle_t_key(self) -> None:
        """Context-aware t key:
        - waiting_on / today views: move to Today (existing behaviour).
        - inbox view: move task to Today folder.
        - user folder views: set scheduled_date = today (schedule in-place).
        """
        task = self._get_selected_task()
        if task is None:
            return
        if self._current_view in ("waiting_on", "inbox"):
            self._move_selected_to_today()
        elif self._current_view not in BUILTIN_FOLDER_IDS:
            self._push_undo()
            self._all_tasks = schedule_task(self._all_tasks, task.id, date.today())
            self._save()
            self._refresh_list(select_task_id=task.id)

    # ------------------------------------------------------------------ #
    # Folder creation / rename / delete                                   #
    # ------------------------------------------------------------------ #

    # Builtin folders that appear in the sidebar above the user-folder section.
    _BEFORE_USER_FOLDERS: frozenset[str] = frozenset(
        {"inbox", "today", "upcoming", "waiting_on"}
    )

    def _start_create_folder(self, insert_position: str = "end") -> None:
        # Determine which user folder to anchor relative to.
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        anchor_id = ""
        if idx is not None and idx < len(view_ids):
            candidate = view_ids[idx]
            if candidate not in BUILTIN_FOLDER_IDS and candidate != "__new_folder__":
                anchor_id = candidate
            elif candidate in self._BEFORE_USER_FOLDERS and insert_position == "after":
                # Pressing `o` on a builtin that precedes user folders: insert at the
                # very start of the user-folder section (before the first user folder).
                user_folders = sorted(self._all_folders, key=lambda f: f.position)
                if user_folders:
                    anchor_id = user_folders[0].id
                    insert_position = "before"
                # else: no user folders yet — fall through to "end" (first folder)
        self._folder_insert_position = insert_position
        self._folder_insert_anchor_id = anchor_id
        self._sidebar_placeholder_insert = insert_position
        self._sidebar_placeholder_anchor_id = anchor_id
        self._rebuild_sidebar()  # shows the placeholder slot
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
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_value_cursor_end(current_name)
        vim_input.set_placeholder("Folder name…")
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._update_status()

    def _delete_selected_area(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("area:"):
            return
        area_id = current_sid[5:]
        area = next((a for a in self._all_areas if a.id == area_id), None)
        if area is None:
            return
        folders_in_area = [f for f in self._all_folders if f.area_id == area_id]
        projects_in_area = [p for p in self._all_projects if p.area_id == area_id]
        if folders_in_area or projects_in_area:
            n_f = len(folders_in_area)
            n_p = len(projects_in_area)
            parts = []
            if n_f:
                parts.append(f"{n_f} folder(s)")
            if n_p:
                parts.append(f"{n_p} project(s)")
            self._delete_confirm_area_id = area_id
            self._update_status(
                f"'{area.name}' has {', '.join(parts)}. [d] delete area  [Esc] cancel"
            )
        else:
            self._push_undo()
            self._all_areas = delete_area(self._all_areas, area_id)
            if self._current_view.startswith("area:") and area_id in self._current_view:
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
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
            self._push_undo()
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
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

    def _move_selected_folder_up(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        folder_id = view_ids[idx]
        if folder_id in BUILTIN_FOLDER_IDS:
            return
        self._all_folders = move_folder_up(self._all_folders, folder_id)
        self._save()
        self._rebuild_sidebar()

    def _move_selected_folder_down(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        folder_id = view_ids[idx]
        if folder_id in BUILTIN_FOLDER_IDS:
            return
        self._all_folders = move_folder_down(self._all_folders, folder_id)
        self._save()
        self._rebuild_sidebar()

    def _start_rename_project(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("project:"):
            return
        project_id = current_sid[8:]
        project = next((p for p in self._all_projects if p.id == project_id), None)
        if project is None:
            return
        self._rename_project_id = project_id
        self._mode = "INSERT"
        self._input_stage = "project_rename"
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_value_cursor_end(project.title)
        vim_input.set_placeholder("Project name…")
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._update_status()

    def _delete_selected_project(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("project:"):
            return
        project_id = current_sid[8:]
        tasks_in_project = project_tasks(self._all_tasks, project_id)
        if not tasks_in_project:
            # Empty project: delete immediately
            self._push_undo()
            self._all_projects = delete_project(self._all_projects, project_id)
            if self._current_view == f"project:{project_id}":
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._rebuild_sidebar()
            self._refresh_list()
        else:
            # Has tasks: prompt user
            project = next((p for p in self._all_projects if p.id == project_id), None)
            name = project.title if project else project_id
            n = len(tasks_in_project)
            self._delete_confirm_project_id = project_id
            self._update_status(
                f"'{name}' has {n} task(s). [d]elete all  [k]eep tasks  [Esc] cancel"
            )

    def _move_selected_project_up(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("project:"):
            return
        project_id = current_sid[8:]
        self._all_projects = move_project_up(self._all_projects, project_id)
        self._save()
        self._rebuild_sidebar()

    def _move_selected_project_down(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("project:"):
            return
        project_id = current_sid[8:]
        self._all_projects = move_project_down(self._all_projects, project_id)
        self._save()
        self._rebuild_sidebar()

    def _start_rename_area(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("area:"):
            return
        area_id = current_sid[5:]
        area = next((a for a in self._all_areas if a.id == area_id), None)
        if area is None:
            return
        self._rename_area_id = area_id
        self._mode = "INSERT"
        self._input_stage = "area_rename"
        vim_input = self.query_one("#vim-input", VimInput)
        vim_input.clear()
        vim_input.set_value_cursor_end(area.name)
        vim_input.set_placeholder("Area name…")
        vim_input.add_class("active")
        vim_input.set_mode("insert")
        vim_input.focus()
        self._update_status()

    def _normalize_tag_order(self) -> None:
        """Keep _tag_order in sync with tags actually present in tasks."""
        existing_tags = {tag for task in self._all_tasks for tag in task.tags}
        # Drop removed tags, keep order of remaining ones
        self._tag_order = [t for t in self._tag_order if t in existing_tags]

    def _move_selected_tag_up(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("tag:"):
            return
        tag_name = current_sid[4:]
        self._normalize_tag_order()
        # Ensure tag is in _tag_order before moving
        existing_tags = {tag for task in self._all_tasks for tag in task.tags}
        ordered = [t for t in self._tag_order if t in existing_tags]
        ordered += sorted(existing_tags - set(ordered))
        self._tag_order = move_tag_up(ordered, tag_name)
        self._save()
        self._rebuild_sidebar()

    def _move_selected_tag_down(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("tag:"):
            return
        tag_name = current_sid[4:]
        self._normalize_tag_order()
        existing_tags = {tag for task in self._all_tasks for tag in task.tags}
        ordered = [t for t in self._tag_order if t in existing_tags]
        ordered += sorted(existing_tags - set(ordered))
        self._tag_order = move_tag_down(ordered, tag_name)
        self._save()
        self._rebuild_sidebar()

    def _move_selected_area_up(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("area:"):
            return
        area_id = current_sid[5:]
        self._all_areas = move_area_up(self._all_areas, area_id)
        self._save()
        self._rebuild_sidebar(cursor_view_id=current_sid)

    def _move_selected_area_down(self) -> None:
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index
        view_ids = self._sidebar_view_ids
        if idx is None or idx >= len(view_ids):
            return
        current_sid = view_ids[idx]
        if not current_sid.startswith("area:"):
            return
        area_id = current_sid[5:]
        self._all_areas = move_area_down(self._all_areas, area_id)
        self._save()
        self._rebuild_sidebar(cursor_view_id=current_sid)

    def _handle_delete_confirm_key(self, event: events.Key) -> None:
        folder_id = self._delete_confirm_folder_id
        if event.key == "d":
            event.prevent_default()
            sidebar = self.query_one("#sidebar", ListView)
            idx = sidebar.index or 0
            self._push_undo()
            for task in folder_tasks(self._all_tasks, folder_id):
                self._all_tasks = delete_task(self._all_tasks, task.id)
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._delete_confirm_folder_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "m":
            event.prevent_default()
            sidebar = self.query_one("#sidebar", ListView)
            idx = sidebar.index or 0
            self._push_undo()
            self._all_tasks = move_folder_tasks_to_today(self._all_tasks, folder_id)
            self._all_folders = delete_folder(self._all_folders, folder_id)
            if self._current_view == folder_id:
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._delete_confirm_folder_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "escape":
            event.prevent_default()
            self._delete_confirm_folder_id = ""
            self._update_status()

    def _handle_delete_confirm_project_key(self, event: events.Key) -> None:
        project_id = self._delete_confirm_project_id
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index or 0
        if event.key == "d":
            event.prevent_default()
            self._push_undo()
            for task in project_tasks(self._all_tasks, project_id):
                self._all_tasks = delete_task(self._all_tasks, task.id)
            self._all_projects = delete_project(self._all_projects, project_id)
            if self._current_view == f"project:{project_id}":
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._delete_confirm_project_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "k":
            event.prevent_default()
            self._push_undo()
            self._all_tasks = unlink_project_tasks(self._all_tasks, project_id)
            self._all_projects = delete_project(self._all_projects, project_id)
            if self._current_view == f"project:{project_id}":
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._delete_confirm_project_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "escape":
            event.prevent_default()
            self._delete_confirm_project_id = ""
            self._update_status()

    def _handle_delete_confirm_area_key(self, event: events.Key) -> None:
        area_id = self._delete_confirm_area_id
        sidebar = self.query_one("#sidebar", ListView)
        idx = sidebar.index or 0
        if event.key == "d":
            event.prevent_default()
            self._push_undo()
            self._all_folders = [
                replace(f, area_id=None) if f.area_id == area_id else f
                for f in self._all_folders
            ]
            self._all_projects = [
                replace(p, area_id=None) if p.area_id == area_id else p
                for p in self._all_projects
            ]
            self._all_areas = delete_area(self._all_areas, area_id)
            if self._current_view.startswith("area:") and area_id in self._current_view:
                new_view_ids = self._sidebar_view_ids
                new_idx = min(idx, len(new_view_ids) - 1)
                self._current_view = new_view_ids[new_idx] if new_view_ids else "today"
            self._save()
            self._delete_confirm_area_id = ""
            self._rebuild_sidebar()
            self._refresh_list()
            self._update_status()
        elif event.key == "escape":
            event.prevent_default()
            self._delete_confirm_area_id = ""
            self._update_status()

    # ------------------------------------------------------------------ #
    # Task completion                                                      #
    # ------------------------------------------------------------------ #

    def _complete_selected(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        project_id = task.project_id
        self._all_tasks = complete_task(self._all_tasks, task.id)
        if project_id:
            self._all_projects = check_auto_complete_project(
                self._all_tasks, self._all_projects, project_id
            )
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _delete_selected(self) -> None:
        task = self._get_selected_task()
        if task is None:
            return
        self._push_undo()
        self._all_tasks = delete_task(self._all_tasks, task.id)
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _purge_logbook_entry(self) -> None:
        """Permanently remove the selected logbook entry (no undo)."""
        task = self._get_selected_task()
        if task is None:
            return
        self._all_tasks = purge_logbook_task(self._all_tasks, task.id)
        self._rebuild_sidebar()
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

    def _apply_history(
        self,
        pop_from: list[tuple[list[Task], list[Folder], list[Project], list[Area]]],
        push_to: list[tuple[list[Task], list[Folder], list[Project], list[Area]]],
        empty_msg: str,
    ) -> None:
        if not pop_from:
            self._update_status(empty_msg)
            return
        push_to.append(
            (
                copy.deepcopy(self._all_tasks),
                copy.deepcopy(self._all_folders),
                copy.deepcopy(self._all_projects),
                copy.deepcopy(self._all_areas),
            )
        )
        entry = pop_from.pop()
        self._all_tasks = entry[0]
        self._all_folders = entry[1]
        self._all_projects = entry[2]
        self._all_areas = entry[3] if len(entry) > 3 else self._all_areas
        self._save()
        self._rebuild_sidebar()
        self._refresh_list()

    def _undo(self) -> None:
        self._apply_history(self._undo_stack, self._redo_stack, "(nothing to undo)")

    def _redo(self) -> None:
        self._apply_history(self._redo_stack, self._undo_stack, "(nothing to redo)")
