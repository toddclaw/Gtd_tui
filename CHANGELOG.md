# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Areas of responsibility (BACKLOG-32): new `Area` dataclass (`id`, `name`, `position`); `Folder.area_id` and `Project.area_id` optional fields (default `None`, backward-compatible with existing data); sidebar renders Areas as collapsible `▾`/`▸` section headings (bold primary colour) with their folders and projects indented beneath when expanded; `A` while sidebar is focused creates a new Area; `m` while a user folder or project is selected in the sidebar opens an `AreaPickerScreen` modal to assign it to an Area (or unassign via "No area"); `Enter` on an Area header collapses/expands it; areas survive save/load round-trips; 22 new unit tests in `tests/gtd/test_areas.py`
- Projects (BACKLOG-31): new `Project` dataclass (`id`, `title`, `notes`, `folder_id`, `position`, `deadline`, `completed_at`); `Task.project_id: str | None` (default `None`, backward-compatible); Projects section in sidebar with `Title (done/total)` progress display; deadline urgency rendered red/yellow matching task deadlines; `N` while sidebar is focused on the Projects section creates a new project; selecting a project shows its sub-tasks in the main task list; `o`/`O`, `x`/Space, `J`/`K`, `m`, `s` work within project view; completing all sub-tasks auto-completes the project; projects and sub-tasks survive save/load round-trips; 18 new unit tests in `tests/gtd/test_projects.py`
- Tags / Contexts (BACKLOG-30): `Task.tags: list[str]` field; comma-separated Tags input in task detail view; inline cyan tag display in task list; Tags section in sidebar listing all unique tags with counts; selecting a tag shows a cross-folder filtered view supporting `x`/Space to complete and `m` to move; storage round-trip backward-compatible with old JSON files; 10 new unit tests in `tests/gtd/test_tags.py`

---

## [1.3.0] — 2026-03-17

### Added
- MIT `LICENSE` file; `pyproject.toml` now declares `license = {text = "MIT"}` (BACKLOG-34)
- `gg` / `G` jump to first / last item in the sidebar when sidebar is focused (BACKLOG-35)
- `0` now jumps to Inbox; numbering is now 0-indexed (`0`=Inbox, `1`=Today, `2`=Upcoming, `3`=Waiting On, `4`=Someday, `5`–`9`=user folders) (BACKLOG-36)
- Context-aware `t` key: in Inbox or Waiting On it moves the task to Today; in a user-created folder it sets `scheduled_date = today` so the task surfaces in the Today smart view without changing folder (BACKLOG-37)
- Ctrl-Z suspends the app to the background (`fg` to resume) (BACKLOG-38)
- Undo/redo stacks now persist across sessions (capped at 20 entries); `u` after restart can undo the last action from a previous session; undo history is stored in `data.json` alongside tasks and folders, including in encrypted files (BACKLOG-41)
- `y` in VimInput COMMAND mode yanks the current line to an internal register and the system clipboard; `p` / `P` paste register content after/before the cursor (single-line) or as a new line below/above (multi-line); falls back to internal register when clipboard is unavailable (BACKLOG-39)

### Fixed
- All 14 mypy errors resolved: `_on_key` made async in VimInput; `_UnitLiteral` type alias for repeat unit fields; `parsed_repeat` variable to separate date vs repeat parsing; `focused.id or ""` for `_normalize_field`; `_anchor_entry` extraction for VISUAL block-move

---

## [1.2.3] — 2026-03-17

### Fixed
- Multiline notes field: cursor no longer goes off-screen when scrolling through lines longer than the widget width.  The scroll logic now counts visual rows (accounting for line wrapping) rather than logical lines, so pressing `j` always keeps the cursor visible.
- Global search (`/`): first result is now reliably highlighted after typing a query.  Root cause was Textual's async DOM — `ListView.validate_index` silently discarded the index while items were still mounting.  Fixed by making `_run_search` async and awaiting `clear()` + `extend()` before setting the selection.
- Date field now accepts `today` as valid input (previously raised InvalidDateError)

### Changed
- `y` in VISUAL mode yanks all selected tasks to the clipboard (title + notes per task, separated by blank lines), then exits VISUAL mode

### Added
- `y` keybinding in NORMAL mode yanks the selected task's title (and notes if present) to the system clipboard; shows `(yanked to clipboard)` or `(clipboard not available)` in the status bar
- Document clipboard prerequisites (`xclip`/`xsel`/`wl-clipboard`) and tmux `DISPLAY` fix in README and CLAUDE.md
- Encrypted database (`--encrypt` / `--decrypt` migration flags); AES-256-GCM via `cryptography` package; auto-detected from file magic header on every launch
- Moved feature backlog out of `CLAUDE.md` into `BACKLOG.md`

---

## [1.1.0]

### Added
- BACKLOG-22: UX polish III — detail view Date field, j/k field navigation, o/O in VimInput, universal placeholder row, Waiting On auto-date (+7d), scrollable help screen
- BACKLOG-21: Extended vim motions (W/B/dw/dW), multiline notes in detail view, Task.created_at field, positional folder insertion (o/O in sidebar)
- BACKLOG-20: Deadline field on tasks — red if overdue, yellow if ≤3 days; shown in task list and detail view
- BACKLOG-19: Weekly review screen (`W`) showing tasks completed in the past 7 days
- BACKLOG-18: Usability polish II — skip notes on task creation, larger notes field, sidebar count refresh, year in date display, notes in `--summary`, instant Esc, VimInput horizontal scroll, undo for folder deletion
- BACKLOG-17: Usability polish — H/M/L navigation, o/O for folders, sidebar item counts, recurrence marker (↻), `someday` date keyword, `--summary` / `-s` CLI flag
- BACKLOG-16: TUI integration tests using Textual's headless `run_test()` / Pilot API
- BACKLOG-15: Visual mode (v) with block selection and bulk operations (complete, delete, schedule, move, reorder)
- BACKLOG-14: Upcoming view aggregating all future-dated tasks sorted by date
- BACKLOG-13: Redo (Ctrl+R); redo stack cleared on new mutations
- BACKLOG-12: VimInput widget with full vi motions (h/l/w/b/W/B/0/$/x/cw/dw/dW/i/a) in all text fields
- BACKLOG-11: Task detail and edit view (Enter on a task); edits persist immediately
- BACKLOG-10: Natural language date input (tomorrow, next week, in N days, weekday names)
- BACKLOG-9: gg / G navigation, header task counts, abbreviated weekday in date display
- BACKLOG-8: Global search (/) with filter-as-you-type, folder grouping, match highlighting
- BACKLOG-7: Someday folder
- BACKLOG-6: Recurring tasks (completion-relative scheduling via RecurRule)
- BACKLOG-5: Repeating tasks (calendar-fixed schedule via RepeatRule)
- BACKLOG-4: User-created folders with create/rename/delete and cross-folder task moves
- BACKLOG-3: Waiting On folder; `w` / `t` to move tasks; [W] prefix in Today view
- BACKLOG-2: Scheduled task dates; tasks hide until their date; `+Nd` / `YYYY-MM-DD` input
- BACKLOG-1: Initial app scaffold — Today view, task creation (o/O), Logbook, undo, vi navigation
