# Feature Backlog

Features to implement, in rough priority order. Pick from the top when starting new work.

Story points use Fibonacci scale calibrated against delivered work: BACKLOG-1 ≈ 13 (full app scaffold), BACKLOG-2 ≈ 8 (significant feature on existing infrastructure).

---

### ~~BACKLOG-1 — Today folder with task creation~~ ✅ DONE

**Story points:** 13

**Description:**
- A built-in folder called **Today** is the default view on launch
- Tasks have two fields: a short **title** (one line) and an optional **notes** section (multi-line)
- New tasks are added positionally (`o` = after cursor, `O` = before cursor)
- Task order in Today persists between sessions (user-defined order is preserved)
- When a task is marked complete it is moved to the **Logbook** folder

**Acceptance criteria:**
- [x] Opening the app shows the Today folder
- [x] `o` / `O` add a new task after/before the selected task with a placeholder row shown immediately
- [x] Enter advances from title to notes; Esc cancels at any stage
- [x] Completed tasks disappear from Today and appear in Logbook with a completion timestamp
- [x] Task order survives app restart

**Also delivered (not in original spec):**
- `J` / `K` reorder tasks within Today
- `u` undoes the last mutating action
- `:help` shows a keybinding reference modal
- `G` jumps to the bottom; selection always stays highlighted after any operation

**Data model sketch:**
```python
@dataclass
class Task:
    id: str              # uuid
    title: str
    notes: str           # may be empty
    folder_id: str
    position: int        # explicit ordering within folder
    completed_at: datetime | None
    scheduled_date: date | None
```

---

### ~~BACKLOG-2 — Scheduled task dates (snooze to a date)~~ ✅ DONE

**Story points:** 8

**Description:**
- A task can have an optional **date** attached to it
- When a date is set, the task is removed from Today and held until that date arrives
- On the scheduled date the task reappears at the top of Today automatically
- Date can be set or cleared from the task edit view

**Acceptance criteria:**
- [x] Task edit view has a date field (keyboard-entry, e.g. `2026-03-20` or relative `+3d`)
- [x] Tasks with a future date do not appear in Today
- [x] On the scheduled date, tasks reappear in Today (checked at app launch)
- [x] Clearing a date returns the task to Today immediately

---

### ~~BACKLOG-3 — Waiting On folder~~ ✅ DONE

**Story points:** 8

**Acceptance criteria:**
- [x] Waiting On appears in the sidebar
- [x] Tasks can be created in or moved to Waiting On
- [x] `w` moves Today task to Waiting On; `t` moves Waiting On task back to Today
- [x] Surfaced tasks show `[W]` prefix in the Today view (undated WO tasks surface in Today)

---

### ~~BACKLOG-4 — User-created folders~~ ✅ DONE

**Story points:** 8

**Acceptance criteria:**
- [x] `N` while sidebar is focused creates a new folder
- [x] Folder name entry uses INSERT mode
- [x] New folder appears in sidebar immediately and persists across restarts
- [x] Tasks can be moved between folders (`m` to move, then select destination)
- [x] Deleting a non-empty folder prompts: `[d]`elete all or `[m]`ove to Today

---

### ~~BACKLOG-5 — Repeating tasks (time-based, independent of completion)~~ ✅ DONE

**Story points:** 8 — Requires a task detail/edit view (none exists yet), a new RepeatRule data model with storage migration, and launch-time task-spawning logic. The edit view alone is a significant new UI component.

**Description:**
- A task can be marked as **repeating** with an interval: every N days / weeks / months / years
- On each due date, a **new task** with the same title, notes, and folder is created automatically
- This happens regardless of whether the previous instance was completed — the schedule is fixed to the calendar, not to completion
- The original task is not modified; a fresh copy appears in Today on the repeat date

**Acceptance criteria:**
- [x] Task edit view has a repeat field: interval + unit (e.g. `7 days`, `1 month`)
- [x] On app launch, any repeat tasks whose next due date has arrived generate a new task in Today
- [x] The new task is a copy (title, notes, folder) with no repeat rule of its own; the source task keeps its rule for future spawns
- [x] Repeat schedule is stored on the source task and survives restarts
- [x] Completing or deleting a repeating task does not cancel future instances

**Data model addition:**
```python
@dataclass
class RepeatRule:
    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    next_due: date
```

---

### ~~BACKLOG-6 — Recurring tasks (completion-relative scheduling)~~ ✅ DONE

**Story points:** 5 — Incremental on BACKLOG-5: edit view and repeat infrastructure already exist, this adds a completion hook that spawns the next instance with a floating due date.

**Description:**
- A task can be marked as **recurring** with an offset: N days / weeks / months / years after completion
- When the task is marked complete, a **new task** with the same details is created, with its scheduled date set to `completion_date + offset`
- Unlike repeating (BACKLOG-5), the next instance's date floats relative to when the current one was done

**Acceptance criteria:**
- [x] Task edit view allows selecting recurring mode distinct from repeating mode
- [x] On task completion, a new task is automatically created with the computed scheduled date
- [x] The new task appears in Today on its scheduled date (same mechanism as BACKLOG-2)
- [x] Recurring setting is preserved on each generated task

**Data model addition:**
```python
@dataclass
class RecurRule:
    interval: int
    unit: Literal["days", "weeks", "months", "years"]
```

**Notes:**
- `RecurRule` is distinct from `RepeatRule` (no `next_due` — date is computed at completion time)
- If both Repeat and Recurring are set on a task, Repeat takes precedence and Recurring is cleared
- The "Recurring" field in the task edit view uses the same `N unit` format as Repeat

**Distinction from BACKLOG-5:**

| | Repeating | Recurring |
|---|---|---|
| Schedule anchor | Fixed calendar date | Completion date |
| Missed instance | New task still appears on schedule | Deferred until you actually complete it |
| Example | "Pay rent — 1st of every month" | "Floss — 1 day after last done" |

---

### ~~BACKLOG-7 — Someday folder~~ ✅ DONE

**Story points:** 3

**Acceptance criteria:**
- [x] Someday appears in the sidebar as a built-in folder (below user-created folders)
- [x] Tasks can be created directly in Someday or moved there from any other folder
- [x] Tasks in Someday never surface in Today or Upcoming automatically
- [x] Tasks can be moved from Someday to Today or any other folder manually

---

### ~~BACKLOG-8 — Global search across all folders~~ ✅ DONE

**Story points:** 8 — Real-time filter-as-you-type requires reactive updates on every keystroke, result grouping with separators across folders, match highlighting within labels, and navigate-to-folder on selection. All new UI patterns.

**Description:**
- A search mode that matches tasks by title or notes text across every folder simultaneously
- Results are ordered: active folders first (Today, Waiting On, Someday, user folders), Logbook results last
- Within each group, results are ordered by relevance (title match > notes match) then by recency

**Acceptance criteria:**
- [x] `/` from any view opens a search prompt
- [x] Results update incrementally as the user types (filter-as-you-type)
- [x] Results are grouped: active folders first, Logbook last — with a visible separator
- [x] Selecting a result navigates to that task in its folder and closes search
- [x] `Esc` cancels search and returns to the previous view
- [x] Search is case-insensitive; matches are highlighted in results

### ~~BACKLOG-9 — UX polish: navigation shortcuts, task counts, date display~~ ✅ DONE

**Story points:** 3

**Acceptance criteria:**
- [x] `gg` in NORMAL mode moves the cursor to the first task
- [x] Header label updates to reflect current task count whenever the list changes
- [x] Scheduled task rows show abbreviated weekday, e.g. `[Mar 16 Mon]`

---

### ~~BACKLOG-10 — Natural language date input~~ ✅ DONE

**Story points:** 3

**Acceptance criteria:**
- [x] `tomorrow` resolves to today + 1 day
- [x] `next week` resolves to today + 7 days
- [x] `in N days` / `in N weeks` resolve correctly
- [x] Weekday names (`monday`, `tuesday`, …) resolve to the next occurrence of that weekday
- [x] Invalid input still raises `InvalidDateError` as before
- [x] All new cases covered by unit tests in `tests/gtd/test_dates.py`

---

### ~~BACKLOG-11 — Task detail and edit view~~ ✅ DONE

**Story points:** 5 — New overlay/panel component; first time existing tasks can be edited after creation.

**Description:**
- Pressing `Enter` on a selected task opens a detail panel showing its full title and notes
- From the detail panel the user can edit the title and notes (INSERT mode)
- Esc closes the panel; changes are saved on close

**Acceptance criteria:**
- [x] `Enter` in NORMAL mode opens the detail view for the selected task
- [x] Detail view shows full title and full notes (multi-line)
- [x] Modal opens directly in edit mode; `Enter` advances between fields; `Esc` saves and closes
- [x] Edits persist to `data.json` on close
- [x] Edited title is reflected in the task list immediately

**Also delivered beyond original spec:**
- Repeat field (calendar-fixed schedule, e.g. `7 days`) — BACKLOG-5
- Recurring field (completion-relative, e.g. `1 week`) — BACKLOG-6

---

### ~~BACKLOG-12 — Vim motions in text input fields~~ ✅ DONE

**Story points:** 8

**Acceptance criteria:**
- [x] Custom vi-aware input widget (`VimInput`) replaces standard Input in all editing contexts
- [x] `h` / `l` move cursor left / right in COMMAND mode
- [x] `w` / `b` / `W` / `B` jump forward / backward by word / WORD
- [x] `0` / `$` move to start / end of line
- [x] `x` deletes character under cursor
- [x] `cw` / `dw` / `dW` delete to end of word / WORD (cw enters INSERT mode)
- [x] `i` / `a` enter INSERT mode at / after cursor
- [x] `Esc` always returns to COMMAND mode (never exits the field)
- [x] Multiline mode: `Enter` inserts newline; `j` / `k` navigate lines; boundary j/k bubbles to parent

---

### ~~BACKLOG-13 — Redo~~ ✅ DONE

**Story points:** 2

**Acceptance criteria:**
- [x] `Ctrl+R` in NORMAL mode reapplies the most recently undone action
- [x] Redo stack is cleared on any new mutation (add, complete, move, schedule)
- [x] `u` followed by `Ctrl+R` returns the list to its pre-undo state
- [x] Status bar shows `(nothing to redo)` when the redo stack is empty

---

### ~~BACKLOG-14 — Upcoming view~~ ✅ DONE

**Story points:** 5 — Delivered as part of the Today/Upcoming/Someday smart-view refactor.

**Description:**
- **Upcoming** is a sidebar view that aggregates all tasks with a future `scheduled_date` across every folder
- Tasks are displayed sorted by date ascending, with day-of-week labels (see BACKLOG-9)
- A task can be promoted back to Today (date cleared) directly from Upcoming with a keybinding
- Moving a task from Today to Upcoming is shorthand for scheduling it (opens the date picker with `s`)

**Acceptance criteria:**
- [x] Upcoming appears in the sidebar
- [x] Upcoming lists all tasks with `scheduled_date > today`, sorted by date
- [x] Task count is shown in the Upcoming header
- [x] `s` in any view opens the date picker — setting a date moves the task to Upcoming automatically
- [ ] Unschedule a task from Upcoming returns it to its home folder's Today slot (`s` then empty)

---

### ~~BACKLOG-15 — Visual mode block selection and bulk operations~~ ✅ DONE

**Story points:** 8 — New modal state alongside NORMAL and INSERT; significant keybinding and rendering work.

**Description:**
- `v` in NORMAL mode enters VISUAL mode; selected tasks are highlighted distinctly
- `j` / `k` extend or shrink the selection
- Bulk operations apply to all selected tasks:
  - `s` — open date picker; date is applied to every selected task
  - `x` / Space — complete all selected tasks
  - `d` — delete all selected tasks
  - `m` — move selected tasks to the picked folder
  - `w` — move selected tasks to Waiting On
  - `t` — move selected tasks to Today
  - `J` / `K` — move entire block of selected tasks down or up
- Esc exits VISUAL mode without performing any action

**Acceptance criteria:**
- [x] `v` enters VISUAL mode; status bar shows `VISUAL`
- [x] `j` / `k` extend selection downward / upward (anchor stays fixed)
- [x] Selected rows are visually distinct from the cursor row
- [x] `s` in VISUAL mode opens date picker; date applied to all selected tasks on confirm
- [x] `x` / Space in VISUAL mode completes all selected tasks
- [x] `d` in VISUAL mode deletes all selected tasks
- [x] Esc cancels selection and returns to NORMAL mode
- [x] All bulk operations are undoable as a single undo step

---

### ~~BACKLOG-16 — TUI integration tests~~ ✅ DONE

**Story points:** 8 — Textual ships a headless test driver (`App.run_test()`) that simulates key events and inspects the DOM without a real terminal. This is the first time the app layer is tested directly; all prior tests cover only domain logic and storage.

**Description:**
- Add integration tests that drive `GtdApp` through its full stack — key events → app state → rendered DOM — using Textual's built-in headless test driver
- Tests should cover the core user journeys that cannot be verified by unit-testing domain logic alone: navigation, modal screens, mode transitions, and persistence side-effects
- Keep tests fast: use `tmp_path` for storage so no real data file is touched

**Acceptance criteria:**
- [x] Test harness uses `await app.run_test()` (Textual's `pilot` API) — no subprocess or real terminal required
- [x] Launching the app shows Today view with correct header
- [x] Pressing `o` enters INSERT mode; typing a title and pressing Enter twice adds the task to the list
- [x] Pressing `x` on a task completes it and removes it from Today
- [x] Pressing `Enter` on a task opens the `TaskDetailScreen` modal; `Esc` closes it
- [x] Pressing `/` opens the `SearchScreen` modal; `Esc` closes it
- [x] Pressing `h` focuses the sidebar; `l` returns focus to the task list
- [x] Pressing `u` after completing a task restores it to Today (undo)
- [x] Tasks persist: saving and reloading `GtdApp` with the same `tmp_path` data file shows the same tasks
- [x] Tests live in `tests/app/test_app.py` and run with the rest of the suite via `pytest`

**Implementation notes:**
- Used `label.content` (not `.renderable`) to read Label text in Textual 8.1.1
- `_task` attribute renamed to `_gtd_task` in `TaskDetailScreen` — Textual's `Widget` base class uses `_task` internally for its asyncio task, causing a collision
- `asyncio_mode = "auto"` in `pyproject.toml` means all `async def test_*` functions run as asyncio tests without `@pytest.mark.asyncio`

---

### ~~BACKLOG-17 — Usability polish (6 small improvements)~~ ✅ DONE

**Story points:** 13 — Six independent improvements captured from the user's own Today list; each is small individually but together they meaningfully improve daily usability.

**Description:**

1. **`H`/`M`/`L` navigation** — jump to top / middle / bottom of the task list (vim screen-position mnemonics applied to the full list)
2. **`o`/`O` to create folders** — consistent with task-creation keybindings; sidebar now accepts `o` and `O` as aliases for `N` (new folder)
3. **Sidebar item counts** — every sidebar entry shows its live task count: `Today (4)`, `Upcoming (2)`, `Logbook (17)`, etc.
4. **Recurrence marker** — task rows with a `repeat_rule` or `recur_rule` show a `↻` suffix so recurring tasks are visually distinct
5. **`"someday"` date keyword** — typing `someday` in the date picker moves the task to the Someday folder instead of setting a date
6. **CLI `--summary` / `-s` flag** — `gtd-tui --summary` (or `-s`) prints the first 4 Today tasks to stdout and exits; useful for shell prompts and scripts

**Acceptance criteria:**
- [x] `H` moves cursor to first task, `M` to middle, `L` to last
- [x] `o` and `O` in sidebar create a new folder (same as `N`)
- [x] Sidebar shows `FolderName (N)` for every built-in and user folder
- [x] Task rows with repeat or recur rule show `↻` at the end of the title
- [x] `s` → `someday` moves task to Someday folder; no date is set
- [x] `gtd-tui -s` prints up to 4 Today tasks and exits with code 0

---

### ~~BACKLOG-18 — Usability polish II (8 improvements)~~ ✅ DONE

**Story points:** 8 — Eight user-requested usability improvements from the user's Today list.

**Description:**

1. **Skip notes on initial task creation** — after entering a title and pressing Enter, the task is saved immediately; notes can be added later via the detail view (`Enter` on a task)
2. **Larger notes section** — the notes VimInput in TaskDetailScreen is 7 rows tall (4 content lines visible)
3. **Folder count refresh** — sidebar counts update immediately after a task is added to any folder
4. **Year in date display** — dates in a different year than today show the year: `Mar 16 Mon 2027`; same-year dates remain `Mar 16 Mon`
5. **Notes in CLI summary** — `gtd-tui --summary` prints notes (indented) under each task that has them
6. **Speed up Esc** — `ESCAPE_TO_MINIMIZE = False` on GtdApp removes Textual's built-in Esc delay
7. **VimInput horizontal scroll** — text longer than the widget width scrolls to keep the cursor visible; no more invisible characters
8. **Undo for folder deletion** — deleting a folder (empty or via confirm) is undoable with `u`; undo/redo stack now stores `(tasks, folders)` tuples

**Features deferred to future backlogs:**
- Waiting-on reminder (auto-date after 7 days) → BACKLOG-19
- Weekly review screen → BACKLOG-19
- Deadline field with red past-due display → BACKLOG-20

**Acceptance criteria:**
- [x] `o` → type title → Enter saves task immediately (no notes prompt)
- [x] Notes section in detail view is at least 4 lines tall
- [x] Sidebar count updates after adding a task
- [x] Dates in a different year show the year suffix
- [x] `--summary` prints notes indented under tasks that have them
- [x] Esc in VimInput feels instant
- [x] Cursor stays visible when typing past the right edge of the input
- [x] `u` after deleting a folder restores it and its tasks

---

### ~~BACKLOG-19 — Weekly review~~ ✅ DONE

**Story points:** 13 — a new full-screen view (weekly review).

**Description:**
- **Weekly review** — a new view (accessible via `W`) showing all tasks completed in the last 7 days, with completion timestamps and scrollable with j/k
- Note: completed tasks all carry `folder_id='logbook'` regardless of origin, so the list is flat/chronological rather than grouped by original folder

**Acceptance criteria:**
- [x] `W` opens the Weekly Review view (works from both task list and sidebar)
- [x] Weekly Review lists completed tasks from the past 7 days, most recent first
- [x] Completion timestamps shown per task
- [x] j/k scroll the panel; Esc/Enter/q close it

---

### ~~BACKLOG-20 — Deadline field~~ ✅ DONE

**Story points:** 8 — New data model field, rendering in red if past due, and days-remaining display.

**Description:**
- A task can have a **deadline** date separate from its scheduled date
- In the task list, if a deadline is set: show the deadline date; if past due, render in red; if due soon (≤ 3 days), render in yellow
- In the detail view, a dedicated Deadline field (below the Date field)
- The days-remaining count is shown alongside the date: `Mar 21 Sat — 3d left` or `Mar 16 Mon — 2d overdue` in red

**Acceptance criteria:**
- [x] Task detail view has a Deadline field (between Date and Notes)
- [x] Deadline date stored in `Task.deadline: date | None`
- [x] Task rows show deadline info when set
- [x] Past-due deadlines render in red
- [x] Due-in-≤3-days (including today) render in yellow
- [x] No deadline: no change to existing display

---

### ~~BACKLOG-21 — Extended vim motions, multiline notes, created_at, positional folder insertion~~ ✅ DONE

**Story points:** 13

**Acceptance criteria:**
- [x] `W` / `B` WORD-forward / WORD-backward motions in VimInput
- [x] `dw` / `dW` delete to end of word / WORD in VimInput
- [x] VimInput supports `multiline=True` mode: Enter inserts newline, j/k navigate lines
- [x] Task notes field is multiline in the detail view
- [x] `Task.created_at` field set at creation, stored/loaded in JSON, displayed in detail/logbook views
- [x] `insert_folder()` operation supports before/after/end positional insertion with renumbering
- [x] Sidebar `o` / `O` insert a new folder after / before the selected folder
- [x] Undo/redo unified via `_apply_history` helper

---

### ~~BACKLOG-22 — UX polish III (detail view date field, j/k navigation, o/O in VimInput, universal placeholder)~~ ✅ DONE

**Story points:** 8

**Acceptance criteria:**
- [x] Task detail view has a **Date** field (between Title and Notes) for editing the scheduled date
- [x] All detail view fields open in COMMAND mode; `j` / `k` move between fields
- [x] `o` / `O` in COMMAND mode: single-line fields jump to end/start + enter INSERT mode; multiline notes open a new line below/above + enter INSERT mode
- [x] Multiline VimInput: `j` at last line and `k` at first line bubble to parent for field navigation
- [x] Placeholder row (empty inline entry) shown immediately on `o` / `O` in Waiting On, Someday, and all user folders — consistent with Today behavior
- [x] Waiting On tasks created without a date auto-receive `scheduled_date = today + 7d`
- [x] Waiting On tasks moved from another folder also receive `scheduled_date = today + 7d` (only if no existing date)
- [x] Scrollable help screen: `j` / `k` scroll the help panel; panel has fixed height so overflow is reachable

---

### ~~BACKLOG-23 — Encrypted database~~ ✅ DONE

**Story points:** 13 — New dependency (`cryptography`), key-derivation layer, auto-detection of file format, one-time CLI migration flag, interactive password prompt (no echo), atomic encrypted writes, and unit tests for all crypto paths. Security-critical code requires careful review.

**Description:**
- The data file is either plaintext JSON or an encrypted binary blob. The app detects which it is from a magic header — no flag is needed at runtime once encryption is set up.
- **First-time encryption:** `gtd-tui --encrypt` migrates an existing plaintext file to encrypted format. Prompts for password + confirmation, then all future runs work without any flag.
- **All subsequent runs:** if the file header indicates ciphertext, the app automatically prompts for the password (via `getpass`), decrypts to an in-memory buffer, and re-encrypts on every save. The flag is never needed again.
- **Runs on a plaintext file (no flag):** opens normally, no password prompt.
- **`--decrypt`:** one-time reverse migration — prompts for password, writes plaintext file, no further prompts needed after that.

**Encryption design:**
- Key derivation: **scrypt** (`cryptography` package), random 32-byte salt stored in file header; parameters `N=2^17, r=8, p=1`
- Cipher: **AES-256-GCM** — authenticated encryption guards against tampering and corruption
- File format (binary): `[4-byte magic][1-byte version][32-byte salt][12-byte nonce][ciphertext][16-byte GCM tag]`
- Atomic write: encrypt to a temp file, then `os.replace()` — same as existing plaintext writes
- File permissions remain `600`

**CLI changes:**
- `gtd-tui --encrypt` — one-time command: prompts for password + confirmation, encrypts plaintext file, exits with confirmation message
- `gtd-tui --decrypt` — one-time command: prompts for password, writes plaintext file, exits with confirmation message
- Normal `gtd-tui` (no flags): auto-detects encryption from file header and prompts for password if needed
- `gtd-tui --summary` / `-s` also auto-detects and prompts if needed

**Acceptance criteria:**
- [x] `gtd-tui --encrypt` on a plaintext file: prompts for password + confirmation, encrypts file in-place, prints confirmation
- [x] `gtd-tui` (no flag) on an encrypted file: auto-detects, prompts for password, opens normally
- [x] `gtd-tui` (no flag) on a plaintext file: opens normally, no password prompt
- [x] Wrong password: prints `"Incorrect password"` and exits with code 1
- [x] `gtd-tui --decrypt`: prompts for password, writes plaintext file, prints confirmation
- [x] Atomic write: a crash mid-save never corrupts the file
- [x] Unit tests: encrypt→decrypt round-trip, wrong-password rejection, magic-byte detection, corrupt-file rejection, plaintext passthrough
- [x] `cryptography` added to `pyproject.toml` dependencies

**Implementation notes:**
- All crypto logic lives in `gtd_tui/storage/crypto.py`; `file.py` calls into it after detecting the file format
- Never log or print the password or derived key
- `--encrypt` and `--decrypt` are migration utilities only — they do not start the TUI

---

### ~~BACKLOG-24 — Fix CI pipeline~~ ✅ DONE

**Story points:** 2 — Configuration-only changes; no source code.

**Description:**
The CI workflow at `.github/workflows/ci.yml` has three problems:
1. It triggers on `branches: [main]` but the repo's default branch is `master` — CI never runs on push
2. It runs only `pytest`; black, ruff, and mypy are documented as required pre-merge checks in CLAUDE.md but are not enforced
3. The test matrix covers Python 3.11 and 3.12 only; Python 3.13 is not tested

**Acceptance criteria:**
- [x] Branch trigger changed to `master` (or to `[master, main]` to be forward-compatible)
- [x] CI step added: `black --check .`
- [x] CI step added: `ruff check .`
- [x] CI step added: `mypy gtd_tui/`
- [x] Python 3.13 added to the test matrix
- [x] All steps run successfully (green) on current codebase before merging

---

### ~~BACKLOG-25 — Dependency lock file and pre-commit hooks~~ ✅ DONE

**Story points:** 3 — Tooling setup; no source code changes.

**Description:**
- All three production dependencies (`textual`, `platformdirs`, `cryptography`) use `>=` lower
  bounds only, making installs non-reproducible across machines and CI runs
- Formatting and type checks are documented in CLAUDE.md but not enforced at commit time, so
  non-conforming commits can reach the branch

**Acceptance criteria:**
- [x] `uv.lock` generated and committed (`uv lock`)
- [x] README Getting Started updated: `uv sync` as primary install path, `pip install -e ".[dev]"` kept as fallback
- [x] CLAUDE.md Getting Started updated similarly
- [x] `.pre-commit-config.yaml` added with black, ruff, and mypy hooks
- [x] `pre-commit run --all-files` passes on the current codebase
- [x] CLAUDE.md pre-commit checklist updated to include `pre-commit install` step

---

### ~~BACKLOG-26 — Missing vi keybindings from CLAUDE.md spec~~ ✅ DONE

**Story points:** 3 — Three small independent additions; no new state required.

**Description:**
CLAUDE.md lists these as first-class vi keybinding requirements; none are implemented:

1. **`Ctrl+d` / `Ctrl+u`** — half-page scroll down / up in the task list
2. **`n` / `N`** — jump to next / previous search match from NORMAL mode (without reopening the
   search screen); only meaningful after a search has been performed
3. **`Ctrl+c`** — cancel edit without saving and return to NORMAL mode (currently Esc is the
   only cancel path; `Ctrl+c` is documented but does nothing)

**Acceptance criteria:**
- [x] `Ctrl+d` scrolls down by half the visible task list height; `Ctrl+u` scrolls up
- [x] After a search, `n` moves the cursor to the next matching task (wrapping); `N` moves to
  the previous
- [x] `Ctrl+c` in INSERT mode cancels the current edit without saving, identical to `Esc`
- [x] All three keybindings documented in `:help`
- [x] Unit/integration tests for each new binding

---

### ~~BACKLOG-27 — Inbox folder~~ ✅ DONE

**Story points:** 3 — New built-in folder; sidebar infrastructure already exists (BACKLOG-3/4 done).

**Description:**
The GTD methodology places the **Inbox** as the primary capture point — a zero-friction bucket
where everything lands before being triaged into Today, Someday, a folder, or Waiting On.
Currently, new tasks go directly to Today, which conflates capture with commitment.

- Inbox appears at the top of the sidebar, above Today
- Tasks in Inbox are never automatically promoted to Today or Upcoming
- The user processes Inbox tasks using the existing `m`, `t`, `s`, and `d` keys

**Acceptance criteria:**
- [x] Inbox is a built-in folder (`folder_id = "inbox"`); `BUILTIN_FOLDER_IDS` updated
- [x] Inbox appears as the first sidebar item (above Today)
- [x] `o` / `O` create tasks in Inbox when the Inbox view is active
- [x] Tasks in Inbox never appear in Today, Upcoming, or any smart view automatically
- [x] Number key `1` jumps to Inbox; existing number shortcuts shift down by one
- [x] `"inbox"` added to `BUILTIN_FOLDER_IDS` in `folder.py`; no new data model fields needed

**Data model note:** `folder_id = "inbox"` suffices; no schema change required.

---

### BACKLOG-28 — "Waiting for" person field on Waiting On tasks

**Story points:** 3 — New optional field on `Task`; storage round-trip; display in Waiting On view.

**Description:**
Waiting On tasks represent work delegated to or blocked on another person or entity. Without a
"waiting for" label, the task list gives no reminder of who to follow up with.

- `Task.waiting_for: str` — optional free-text name (e.g. `"Alice"`, `"Legal team"`)
- Displayed alongside the task title in the Waiting On view: `Buy server quote  → Alice`
- Editable in the task detail view (new field below the date field, only visible when the task
  is in the Waiting On folder)

**Acceptance criteria:**
- [ ] `Task.waiting_for: str` field (default `""`); old JSON files without the field load without error
- [ ] Waiting On task rows show `→ <person>` suffix when `waiting_for` is set
- [ ] Task detail view has a Waiting For field when the task is in the Waiting On folder
- [ ] Field is editable via VimInput (INSERT mode), consistent with other detail fields
- [ ] Storage round-trip tested; display tested in integration tests

---

### BACKLOG-29 — Checklist sub-steps within a task

**Story points:** 5 — New `ChecklistItem` model, storage, detail-view rendering, and completion tracking.

**Description:**
Many tasks in Things have numbered sub-steps (checklist items) that can be individually ticked
off without creating full sub-tasks. This is lighter than Projects (BACKLOG-31) and useful for
things like "Pack for trip: passport ☐, charger ☐, headphones ☐".

- A task has an ordered list of `ChecklistItem` objects (label + checked state)
- Checklist items are displayed and editable in the task detail view
- Completing all checklist items does not auto-complete the parent task (unlike Projects)
- A partial completion indicator is shown in the task list: `Pack for trip [1/3]`

**Acceptance criteria:**
- [ ] `ChecklistItem` dataclass: `id`, `label: str`, `checked: bool`
- [ ] `Task.checklist: list[ChecklistItem]` field (default `[]`); old files load without error
- [ ] Task detail view shows checklist section below notes
- [ ] `o` / `O` in the checklist section add a new item; `x` / Space toggles the focused item
- [ ] Completed items are visually struck-through or marked
- [ ] Task list row shows `[N/M]` completion ratio when checklist is non-empty
- [ ] Storage round-trip works; tests cover add/toggle/reorder/delete of checklist items

---

### BACKLOG-30 — Tags / Contexts

**Story points:** 8 — New `Task.tags` field, storage migration, tag-filter view, inline display.

**Description:**
Tags implement GTD's **context** concept (`@home`, `@work`, `@errands`, `@computer`) and
Things' flexible label system. A task can have zero or more tags. Tags allow cross-folder
filtering: "show me everything I can do @computer right now".

- `Task.tags: list[str]` — free-text labels, conventionally prefixed with `@`
- Tags editable in task detail view (comma-separated input)
- Tags section in the sidebar lists all unique tags across all tasks; selecting one filters
- Inline tag display in the task list (dim/coloured suffix)

**Acceptance criteria:**
- [ ] `Task.tags: list[str]` (default `[]`); old JSON files without the field load without error
- [ ] Task detail view has a Tags field (comma-separated, `@` prefix optional)
- [ ] Tags display inline with the task title in the task list, visually distinct
- [ ] Sidebar has a collapsible "Tags" section listing all unique tags with task counts
- [ ] Selecting a tag in the sidebar shows a cross-folder filtered view of matching tasks
- [ ] Tag filter view supports `x` / Space to complete and `m` to move tasks
- [ ] Storage round-trip and tag filtering covered by unit tests

---

### BACKLOG-31 — Projects

**Story points:** 13 — New `Project` dataclass, sub-task linking, sidebar section, progress
display, and auto-completion logic. Significant new UI component.

**Description:**
GTD **Projects** are outcomes that require more than one action step. Things represents these
as first-class containers in the sidebar, separate from folders. A project holds an ordered
list of tasks; when all are complete, the project moves to Logbook automatically.

- `Project` dataclass with title, notes, optional deadline, folder/area assignment
- Sub-tasks link to a project via `Task.project_id`
- Projects appear in the sidebar under a "Projects" section
- Header shows live progress: `Deploy v2 (3/5)`

**Acceptance criteria:**
- [ ] `Project` dataclass: `id`, `title`, `notes`, `folder_id`, `position`, `deadline`,
  `completed_at`
- [ ] `Task.project_id: str | None` (default `None`); old files load without error
- [ ] Projects appear in the sidebar under a "Projects" heading, sorted by position
- [ ] `N` while sidebar is focused on the Projects section creates a new project
- [ ] Selecting a project shows its sub-tasks in the main task list
- [ ] Sub-tasks support `o`/`O`, `x`/Space, `J`/`K`, `m`, `s` within the project view
- [ ] Project sidebar entry shows `Title (done/total)` progress
- [ ] Completing all sub-tasks auto-completes the project and moves it to Logbook
- [ ] Projects and sub-tasks survive save/load round-trips
- [ ] Deadline field on projects renders with the same red/yellow urgency as task deadlines
- [ ] Tests cover project CRUD, sub-task management, and auto-completion logic

---

### BACKLOG-32 — Areas of responsibility

**Story points:** 8 — New `Area` dataclass, sidebar collapsible sections, folder/project
assignment. Depends on BACKLOG-31 (Projects).

**Description:**
Things' **Areas** are high-level, non-time-bound responsibility domains (Work, Personal,
Health) that group folders and projects. Areas are never "complete" — they represent ongoing
life domains. This is the top of the GTD hierarchy: Area → Project → Task.

**Acceptance criteria:**
- [ ] `Area` dataclass: `id`, `name`, `position`
- [ ] Folders and projects have an optional `area_id: str | None` (default `None`)
- [ ] Sidebar renders Areas as collapsible section headings; their folders and projects appear
  indented beneath when expanded
- [ ] `A` while sidebar is focused creates a new Area
- [ ] Folders and projects can be assigned to an Area via the `m` key (move destination picker
  includes Areas)
- [ ] Areas survive save/load round-trips
- [ ] Tests cover Area CRUD and folder/project assignment logic

---

### BACKLOG-33 — Test coverage for identified gaps

**Story points:** 3 — Tests only; no source changes.

**Description:**
The audit identified several untested paths that carry real risk:

1. **CLI crypto functions** — `_cmd_encrypt`, `_cmd_decrypt`, and `_detect_password` in
   `__main__.py` are untested; they use `getpass` and `sys.exit`, requiring mocks
2. **Colon command parsing** — `:help` / `:h` dispatch via `_start_command()` has no test
3. **`someday_tasks()`** — the domain function is only covered indirectly; no direct unit test
4. **`purge_logbook_task()`** — covered at the app level but not at the domain level
5. **Single-task move mode** — the `m` key flow in NORMAL mode (not VISUAL mode) has no
   dedicated integration test
6. **`spawn_repeating_tasks()` called on launch** — the on-mount integration (correct date
   passed, tasks actually spawned) is untested

**Acceptance criteria:**
- [ ] `tests/test_main.py` extended with mocked-`getpass` tests for `--encrypt` and `--decrypt`
- [ ] `test_app.py` has a test for `:help` opening `HelpScreen` via the colon command buffer
- [ ] `test_operations.py` has a direct test for `someday_tasks()` return value
- [ ] `test_operations.py` has a direct test for `purge_logbook_task()`
- [ ] `test_app.py` has a test for `m` key in NORMAL mode moving a task to a different folder
- [ ] `test_app.py` has an integration test verifying `spawn_repeating_tasks` fires on launch
