# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- **VimInput `f`/`F`/`t`/`T` find-char motions**: `f<ch>` moves to the next occurrence of a character on the current line; `F<ch>` moves backward; `t<ch>` stops one position before; `T<ch>` stops one position after. Works in both single-line and multi-line mode (scoped to the current line).
- **VimInput `;` / `,` repeat-find**: `;` repeats the last `f`/`F`/`t`/`T` in the same direction; `,` repeats in the opposite direction.
- **VimInput `gg` / `G`**: `gg` jumps to the beginning of the text (first line, first char); `G` jumps to the last character. Works in both single-line and multi-line mode.
- **VimInput `^`**: Moves cursor to the first non-blank (non-space) character of the current line. Multi-line aware.
- **Config `[ui] default_view`**: New setting in `~/.config/gtd_tui/config.toml`; controls which view the app opens on launch (`"today"`, `"inbox"`, `"upcoming"`, `"waiting_on"`, `"someday"`, or a user-folder id). Default: `"today"`.
- **ESC key latency fix**: `ESCDELAY` set to 25 ms (before any Textual import) — eliminates the 400–600 ms Esc lag experienced under tmux. Override with `ESCDELAY=<ms>` in your shell.

---

## [1.5.0] — 2026-03-18

### Added
- **Checklist sub-steps** within a task (BACKLOG-29): `ChecklistItem` dataclass with `id`, `label`, `checked`; `Task.checklist` field (backwards-compatible); operations: add, toggle, delete, reorder; task detail view section with `o`/`O` to add, `x`/Space to toggle, `d` to delete, `J`/`K` to reorder; struck-through rendering for completed items; `[N/M]` completion ratio in task list rows
- **Reference folder**: new built-in folder in the sidebar for storing non-actionable reference material; `r` from any view moves selected task(s) to Reference
- **Readable relative dates**: task list rows now show `today`, `tomorrow`, `yesterday`, weekday names (`Thursday`), or `Mar 16` instead of raw ISO dates
- **Upcoming view section headers**: tasks are now grouped by `Tomorrow`, weekday name, `This Month`, and month name (e.g. `April`) so future tasks are easy to scan
- **`w` key extended**: move-to-Waiting-On (`w`) now works from Inbox and all user-created folders, not just Today
- **Calendar picker** for date fields: press `?` on the Date or Deadline field to open a calendar modal; navigate with `h`/`j`/`k`/`l`, confirm with Enter, cancel with Esc
- **Config file auto-created** on first launch at `~/.config/gtd_tui/config.toml` with commented defaults
- **Configurable inactivity timeout**: `[timeout]` section in config with `timeout_minutes` (default 30) and `timeout_enabled` (default true); countdown shown in status bar during the last 5 minutes; `--no-timeout` CLI flag

### Added (VimInput — dot-repeat)
- **Dot-repeat (`.`)** in COMMAND mode replays the last editing operation: `x`, `r<ch>`, `~`, `D`, `dw`/`dW`/`dd`/`d$`/`d0`/`db`/`dB`, and INSERT sessions (`i`/`a`/`A`/`s`/`cw`/`c$`/`o`/`O` + text + Esc)
- Pre-insert actions are captured for `a` (append after char), `A` (append at EOL), `s` (delete char then insert), `cw`/`c$` so that `.` faithfully reproduces the full operation including cursor positioning and deletion

### Fixed
- `?` was being silently swallowed in INSERT mode on non-date fields — now types the character normally; COMMAND-mode bubble is preserved so `?` still opens the calendar on date fields
- `r<ch>` now uses `event.character` instead of the key name length check, so replacing with `.`, `=`, `?`, and other symbols works correctly
- `d0` in multiline mode no longer deletes the newline from the preceding line — it now correctly deletes from the current line's start to the cursor only
- `s=Esc.` now replays the full substitute (delete char + insert text), not just the text insertion
- `AFooEsc.` now moves to end-of-line before inserting, matching vim's `A` semantics

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
