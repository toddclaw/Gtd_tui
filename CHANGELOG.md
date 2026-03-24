# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.9.0] — 2026-03-24

### Added
- **BACKLOG-81 — External editor for task notes (`Ctrl+E`)**: While the notes field in the task detail view is focused, `Ctrl+E` suspends the TUI and opens the notes in `$EDITOR` (falls back to `nano`). On exit code 0 the notes field is updated; on non-zero, notes are preserved. Temp file is cleaned up automatically.
- **BACKLOG-100 — Advanced recurrence patterns**: Both `RepeatRule` (calendar-fixed) and `RecurRule` (completion-relative) now support day-of-week sets (`M-F`, `weekends`, `MWF`, `TR`, `every Mon`, `every other Tue`) and nth-weekday-of-month patterns (`4th Thu`, `1st Mon`, etc.). Convenience aliases `monthly`, `quarterly`, `annually`/`yearly` are also accepted. Task list shows short codes (`↻ M-F`, `↻ 4th Thu`) for named patterns. Old JSON files without the new fields load cleanly.

---

## [1.8.0] — 2026-03-21

### Added
- **Configurable rotating backups**: `[backup]` in `config.toml` — optional throttled copies after each save to `~/.local/share/gtd_tui/backups` (or `directory`), tiered rotation (`daily_keep`, `weekly_keep`, `monthly_keep`); encrypted databases copy as `.enc`.
- **Task creation (o/O) Esc behavior**: First Esc enters COMMAND mode; second Esc saves and exits. Enter saves and exits. Ctrl+C cancels (blank title also cancels).
- **Rename (r) Esc behavior matches o/O**: First Esc enters COMMAND mode; second Esc saves and exits. Applies to task, folder, project, and area renames.
- **Single-instance lockfile**: Prevents two gtd-tui processes from opening the same database; prints "Another gtd-tui is already running." and exits when lockfile exists.
- **Sidebar d on Area**: Delete Area with confirmation when it has folders/projects; [d] confirms, [Esc] cancels. Keeps folders/projects, only disassociates.
- **Undo stack includes areas**: `u` after Area delete restores the area and folder/project membership; undo persists through quit and restart.
- **Optional spell check and capitalization**: `[text]` in `config.toml` — per-field toggles for English spell correction (`pyspellchecker`) and THe-style / sentence-case fixes on submit.
- **Spell check as you type**: `spell_check_as_you_type = true` — correct the last word when pressing Space in INSERT mode (titles, notes, projects, areas, detail view).
- **Backup validation**: Backups are validated after creation (decompress + structure check); tiny or corrupt backups are rejected and removed instead of kept.
- **Backup gzip compression**: `[backup] gzip = true` (default) compresses backups to save space.
- **Backup daily_slots_per_day**: `[backup] daily_slots_per_day` — keep multiple backups per calendar day (default 1).
- **CLI `--backup-now`**: One-shot backup of the data file and exit; uses `[backup]` config for directory and rotation.
- **README Configuration section**: Tables for `[backup]` and `[text]` options.
- **GitHub `main` protection (docs)**: `CLAUDE.md` / `README.md` describe enabling rulesets / branch protection so changes go through pull requests.
- **GitHub Release changelog order**: `scripts/reorder_changelog_section.py` reorders each version's notes; release workflow uses it; documented in `CLAUDE.md`.
- **`.gitignore`**: Narrowed `backup.*` to explicit `backup.json`, `backup.csv`, etc., so `gtd_tui/**/backup*.py` is not ignored.
- **CLAUDE.md release process**: clarifies that merge ≠ shipped release (version bump + tag on `main` still required); `gh pr merge --auto` only after `pre_push_check` / full suite green.
- **README.md**: Development section summarizes the same release and `--auto` rules for maintainers.

---

## [1.7.1] — 2026-03-21

### Added
- **Startup focus config** (`[ui] startup_focus_sidebar`): when `true` (default), focus starts on the sidebar; when `false`, focus starts on the task list (or the empty-hint when the list is empty) so `o` adds a task immediately.
- **Project view strikethrough**: completed project sub-tasks now appear crossed out in the project view instead of being hidden.
- **H/M/L/G/gg in action picker**: move/assign/tag picker supports `H` (top), `M` (middle), `L` (bottom), `G` (bottom), `gg` (top) for fast navigation.
- **H/M/L in sidebar**: `H`, `M`, `L` jump to top/middle/bottom of the sidebar (and in move-mode folder picker).
- **Pre-push quality gate**: `scripts/pre_push_check.py` runs full `pytest`, `black --check`, `ruff check`, and `mypy gtd_tui/`; documented mandatory pre-push checklist in `CLAUDE.md`; optional `pre-commit` **pre-push** hook (`pre-commit install --hook-type pre-push`); `README.md` contributor notes updated to stress that commit hooks do not run tests.
- **Contributor / agent workflow**: `CLAUDE.md` documents branch sanity before work, release step 0, and **closing a body of work** (reflection + user-selected follow-ups); `AGENTS.md` and `.cursor/rules/closure.mdc` mirror the closure step for AI tools.

### Fixed
- **Empty task list focus**: when `startup_focus_sidebar=false` and the task list is empty, focus now correctly goes to the empty-hint so `o` adds a task instead of creating a folder.
- **Default config missing startup_focus_sidebar**: fresh config files (created when none exists) and old configs upgraded via `_ensure_config_defaults` now include `startup_focus_sidebar = true` in the `[ui]` section.
- **Integration tests vs. sidebar default focus**: Pilot tests that drive the task list now use `tests.cfg.CFG_TASK_LIST_FOCUS` so they match production `startup_focus_sidebar=true` without breaking (visual mode, vi keybindings, tags/projects/areas acceptance, inbox TUI tests).

---

## [1.7.0] — 2026-03-20

### Added
- **Border text banner** (BACKLOG-59): `[ui] border_text` config key; when non-empty, the text is rendered centred (with primary-color background) in the top and bottom `ColorBorderStrip` widgets; left/right sides continue the alternating block pattern unchanged.
- **Auto-populate missing config defaults** (BACKLOG-60): on startup, `_ensure_config_defaults()` non-destructively appends any missing TOML keys with their default values; users upgrading from older versions automatically get new config sections without losing existing settings.
- **Default cursor at top-left in text fields** (BACKLOG-61): `VimInput` gains `start_at_beginning=True` mode; `detail-title-input` and `detail-notes-input` open with the cursor at position 0 so long content is visible from the beginning.
- **Regex search** (unlisted): `search_tasks()` auto-detects regex patterns; falls back to case-insensitive substring matching if the pattern is invalid; `//pattern` prefix forces case-sensitive regex.
- **Divider tasks** (BACKLOG-62): tasks whose title is exactly `-` or `=` render as a full-width dim horizontal rule; action keys (`x`, `s`, `m`, `w`, `t`) are no-ops on dividers; dividers are excluded from VISUAL selection.
- **Duplicate task with y / p / P** (BACKLOG-63): `y` in NORMAL mode now also stores the task in `_task_register`; `p` pastes a duplicate below and `P` above the current position; duplicates get a fresh UUID and `created_at`.
- **Quick task rename with r** (BACKLOG-64): `r` in NORMAL mode opens the inline `#task-input` pre-filled with the task's current title; Enter saves, Esc cancels; no-op on divider tasks.
- **HML navigation in VISUAL mode** (BACKLOG-65): `H`, `M`, `L` in VISUAL block mode jump the cursor to the top/middle/bottom of the list and extend the selection, matching NORMAL mode behaviour.
- **Help screen from sidebar** (BACKLOG-66): `?` while the sidebar has focus now opens `HelpScreen`, consistent with the task-list behaviour.
- **Unified action picker for m** (BACKLOG-67/68): `m` opens `_ActionPickerScreen` instead of switching sidebar focus; the picker shows Folders, Projects, and Tags sections; selecting a folder moves the task, a project assigns it (`project_id`), a tag adds it (via `add_tag_to_task`); works in NORMAL and VISUAL mode.
- **VimInput count prefix** (BACKLOG-69): digits `1`–`9` (and `0` when buffer non-empty) accumulate in `_count_buffer`; count applies to `h`, `l`, `w`, `b`, `e`, `W`, `B`, `E`, `x`; `Ni` captures count before `i` and replicates the inserted text N times on ESC.

### Fixed
- **Multiline notes indentation in CLI summary** (BACKLOG-70): `--summary` now splits notes on `\n` and indents every continuation line with four spaces.

### Added
- **VimInput `dd` populates register**: `dd` in both single-line and multi-line mode now copies the deleted text to the internal yank register (and system clipboard), so `p`/`P` paste the deleted content immediately after deletion — consistent with real vim behaviour.
- **VimInput `%` bracket-matching motion**: `%` in COMMAND mode jumps the cursor to the matching bracket (`(`, `)`, `[`, `]`, `{`, `}`), respecting nesting. No-op when the cursor is not on a bracket.
- **VimInput `d%` / `c%`**: `d%` deletes from cursor to matching bracket (inclusive) and populates the register; `c%` does the same then enters INSERT mode.
- **Checklist item rename**: pressing `r` while in checklist navigation mode pre-fills the "Add checklist item" input with the current item's label, allowing the user to edit and confirm with Enter (or cancel with Esc). Undo supported.
- **Configurable color theme**: new `[ui] theme` config option (`"blue"` / `"red"` / `"yellow"` / `"green"`); applies to all `$primary`, `$primary-darken-1`, and `$accent` design tokens (header, status bar, borders, VimInput focus ring). Default: `"blue"`.
- **Configurable screen border**: new `[ui] border_style` option (`"none"` / `"yellow_grey"` / `"red_grey"`) and `border_block_size` (cells per color block, default 3). When non-`"none"`, renders 1-cell alternating-color strips around the app frame.
- **tmux ESCDELAY tip**: if the app is launched inside a tmux session and `ESCDELAY` has not been customised, a one-time status message recommends adding `set-environment -g ESCDELAY 25` to `~/.tmux.conf`.
- **Configurable sidebar counts**: new `[sidebar_counts]` config section with per-section boolean flags (`inbox`, `today`, `upcoming`, `waiting_on`, `someday`, `reference`, `logbook`, `user_folders`, `projects`, `tags`). Set any to `false` to suppress the count parenthetical for that section type. Default: all `true`.
- **`?` opens calendar from inline schedule input**: typing `?` in the `s` (schedule) inline date input now opens the CalendarScreen picker; selecting a date fills it in automatically, consistent with the task-detail date fields.
- Project sidebar management: `r` renames a selected project (pre-fills current title), `d` deletes it and unlinks its tasks (sets `project_id=None` so tasks remain visible), `J`/`K` reorder projects by swapping positions — matching the behaviour already available for user folders; project sidebar entries now show a `◆` prefix so projects are instantly distinguishable from folders at a glance; new operations `move_project_up`, `move_project_down`, `unlink_project_tasks`; 6 new unit tests and 3 new acceptance tests
- Area rename: `r` while an area header is selected in the sidebar renames the area (pre-fills current name); new `area_rename` input stage; 1 new acceptance test
- Tag reordering: `J`/`K` while a tag is selected in the sidebar reorders the tag list; tag order is persisted to disk (`tag_order` key in JSON); `load_tag_order` / `save_data(…, tag_order=…)` storage helpers; new `move_tag_up` / `move_tag_down` operations; 1 new acceptance test
- Area visual boundary: folders and projects belonging to an Area now render with a `│ ` pipe prefix in the sidebar, making area boundaries immediately visible even when an area contains only folders; area-scoped project reorder now uses `◆` with pipe: `│ ◆ `; 2 new acceptance tests
- Area-scoped J/K reordering for folders and projects within an Area: `move_folder_up/down` and `move_project_up/down` now swap only within siblings that share the same `area_id`, so reordering items in one area never disturbs items in another
- Areas of responsibility (BACKLOG-32): new `Area` dataclass (`id`, `name`, `position`); `Folder.area_id` and `Project.area_id` optional fields (default `None`, backward-compatible with existing data); sidebar renders Areas as collapsible `▾`/`▸` section headings (bold primary colour) with their folders and projects indented beneath when expanded; `A` while sidebar is focused creates a new Area; `m` while a user folder or project is selected in the sidebar opens an `AreaPickerScreen` modal to assign it to an Area (or unassign via "No area"); `Enter` on an Area header collapses/expands it; areas survive save/load round-trips; 22 new unit tests in `tests/gtd/test_areas.py`
- Projects (BACKLOG-31): new `Project` dataclass (`id`, `title`, `notes`, `folder_id`, `position`, `deadline`, `completed_at`); `Task.project_id: str | None` (default `None`, backward-compatible); Projects section in sidebar with `Title (done/total)` progress display; deadline urgency rendered red/yellow matching task deadlines; `N` while sidebar is focused on the Projects section creates a new project; selecting a project shows its sub-tasks in the main task list; `o`/`O`, `x`/Space, `J`/`K`, `m`, `s` work within project view; completing all sub-tasks auto-completes the project; projects and sub-tasks survive save/load round-trips; 18 new unit tests in `tests/gtd/test_projects.py`
- Tags / Contexts (BACKLOG-30): `Task.tags: list[str]` field; comma-separated Tags input in task detail view; inline cyan tag display in task list; Tags section in sidebar listing all unique tags with counts; selecting a tag shows a cross-folder filtered view supporting `x`/Space to complete and `m` to move; storage round-trip backward-compatible with old JSON files; 10 new unit tests in `tests/gtd/test_tags.py`

---

## [1.6.0] — 2026-03-19

### Added
- **Export** (`--export FORMAT`): export tasks to stdout or `--output FILE` in four formats: `json` (lossless, recommended for backups), `txt` (one line per task), `csv` (columns: folder, title, scheduled_date, deadline, notes), `md` (markdown with folder headings). Deleted tasks are always omitted from all formats.
- **Import** (`--import FILE`): non-destructive merge from a JSON export file — only tasks and folders whose IDs do not already exist in the data file are added; built-in folder IDs are never imported.
- **VimInput `f`/`F`/`t`/`T` find-char motions**: `f<ch>` moves to the next occurrence of a character on the current line; `F<ch>` moves backward; `t<ch>` stops one position before; `T<ch>` stops one position after. Works in both single-line and multi-line mode (scoped to the current line).
- **VimInput `;` / `,` repeat-find**: `;` repeats the last `f`/`F`/`t`/`T` in the same direction; `,` repeats in the opposite direction.
- **VimInput `gg` / `G`**: `gg` jumps to the beginning of the text (first line, first char); `G` jumps to the last character. Works in both single-line and multi-line mode.
- **VimInput `^`**: Moves cursor to the first non-blank (non-space) character of the current line. Multi-line aware.
- **Config `[ui] default_view`**: New setting in `~/.config/gtd_tui/config.toml`; controls which view the app opens on launch (`"today"`, `"inbox"`, `"upcoming"`, `"waiting_on"`, `"someday"`, or a user-folder id). Default: `"today"`.
- **ESC key latency fix**: `ESCDELAY` set to 25 ms (before any Textual import) — eliminates the 400–600 ms Esc lag experienced under tmux. Override with `ESCDELAY=<ms>` in your shell.

### Fixed
- **CI black formatting**: pinned `target-version = ["py311"]` in `pyproject.toml` so black produces identical output on Python 3.11 (CI) and newer local environments.

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
