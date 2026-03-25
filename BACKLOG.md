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

### BACKLOG-29 — Checklist sub-steps within a task ✅ DONE

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
- [x] `ChecklistItem` dataclass: `id`, `label: str`, `checked: bool`
- [x] `Task.checklist: list[ChecklistItem]` field (default `[]`); old files load without error
- [x] Task detail view shows checklist section below notes
- [x] `o` / `O` in the checklist section add a new item; `x` / Space toggles the focused item
- [x] Completed items are visually struck-through or marked
- [x] Task list row shows `[N/M]` completion ratio when checklist is non-empty
- [x] Storage round-trip works; tests cover add/toggle/reorder/delete of checklist items

---

### ~~BACKLOG-30 — Tags / Contexts~~ ✅ DONE

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
- [x] `Task.tags: list[str]` (default `[]`); old JSON files without the field load without error
- [x] Task detail view has a Tags field (comma-separated, `@` prefix optional)
- [x] Tags display inline with the task title in the task list, visually distinct
- [x] Sidebar has a collapsible "Tags" section listing all unique tags with task counts
- [x] Selecting a tag in the sidebar shows a cross-folder filtered view of matching tasks
- [x] Tag filter view supports `x` / Space to complete and `m` to move tasks
- [x] Storage round-trip and tag filtering covered by unit tests
- [x] `J`/`K` while a tag is selected in the sidebar reorders tags; order persisted to disk

---

### ~~BACKLOG-31 — Projects~~ ✅ DONE

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
- [x] `Project` dataclass: `id`, `title`, `notes`, `folder_id`, `position`, `deadline`,
  `completed_at`
- [x] `Task.project_id: str | None` (default `None`); old files load without error
- [x] Projects appear in the sidebar under a "Projects" heading, sorted by position
- [x] `N` while sidebar is focused on the Projects section creates a new project
- [x] Selecting a project shows its sub-tasks in the main task list
- [x] Sub-tasks support `o`/`O`, `x`/Space, `J`/`K`, `m`, `s` within the project view
- [x] Project sidebar entry shows `Title (done/total)` progress
- [x] Completing all sub-tasks auto-completes the project and moves it to Logbook
- [x] Projects and sub-tasks survive save/load round-trips
- [x] Deadline field on projects renders with the same red/yellow urgency as task deadlines
- [x] Tests cover project CRUD, sub-task management, and auto-completion logic
- [x] Project sidebar entries show `◆` prefix to distinguish them from folders visually
- [x] `r` on a project sidebar entry renames the project (pre-fills current title)
- [x] `d` on a project sidebar entry deletes the project and unlinks its tasks (`project_id → None`)
- [x] `J`/`K` on a project sidebar entry reorders projects by swapping positions (area-scoped: only reorders within the same area)
- [x] Projects inside an area render with `│ ◆ ` prefix to show area membership

---

### ~~BACKLOG-32 — Areas of responsibility~~ ✅ DONE

**Story points:** 8 — New `Area` dataclass, sidebar collapsible sections, folder/project
assignment. Depends on BACKLOG-31 (Projects).

**Description:**
Things' **Areas** are high-level, non-time-bound responsibility domains (Work, Personal,
Health) that group folders and projects. Areas are never "complete" — they represent ongoing
life domains. This is the top of the GTD hierarchy: Area → Project → Task.

**Acceptance criteria:**
- [x] `Area` dataclass: `id`, `name`, `position`
- [x] Folders and projects have an optional `area_id: str | None` (default `None`)
- [x] Sidebar renders Areas as collapsible section headings; their folders and projects appear
  indented beneath when expanded
- [x] `A` while sidebar is focused creates a new Area
- [x] Folders and projects can be assigned to an Area via the `m` key (move destination picker
  includes Areas)
- [x] Areas survive save/load round-trips
- [x] Tests cover Area CRUD and folder/project assignment logic
- [x] `r` on an area header renames the area (pre-fills current name)
- [x] Folders inside an area render with `│ ` pipe prefix for clear visual boundary
- [x] `J`/`K` within an area reorders only items belonging to that area

---

### ~~BACKLOG-33 — Test coverage for identified gaps~~ ✅ DONE

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
- [x] `tests/test_main.py` extended with mocked-`getpass` tests for `--encrypt` and `--decrypt`
- [x] `test_app.py` has a test for `:help` opening `HelpScreen` via the colon command buffer
- [x] `test_operations.py` has a direct test for `someday_tasks()` return value (already existed)
- [x] `test_operations.py` has a direct test for `purge_logbook_task()` (already existed)
- [x] `test_app.py` has a test for `m` key in NORMAL mode moving a task to a different folder
- [x] `test_app.py` has an integration test verifying `spawn_repeating_tasks` fires on launch

---

## Group: Housekeeping

### ~~BACKLOG-34 — Change license to MIT~~ ✅ DONE

**Story points:** 1

**Description:**
Add an MIT `LICENSE` file and update `pyproject.toml` to declare `license = {text = "MIT"}`.

**Acceptance criteria:**
- [x] `LICENSE` file at repo root contains the standard MIT license text with current year and author
- [x] `pyproject.toml` declares `license = {text = "MIT"}`

---

## Group: Navigation improvements

### ~~BACKLOG-35 — gg / G navigation in the sidebar folder list~~ ✅ DONE

**Story points:** 2

**Description:**
`gg` (jump to top) and `G` (jump to bottom) already work in the task list but are not wired up
for the sidebar. When the sidebar is focused, these keys should jump to the first and last
sidebar entry respectively, consistent with the task-list behaviour described in CLAUDE.md.

**Acceptance criteria:**
- [x] `gg` while sidebar is focused moves the selection to the first sidebar item
- [x] `G` while sidebar is focused moves the selection to the last sidebar item
- [x] Both keys are no-ops when the sidebar is empty
- [x] Existing task-list `gg` / `G` behaviour is unaffected

---

### ~~BACKLOG-36 — Folder number shortcuts start at 0~~ ✅ DONE

**Story points:** 2

**Description:**
Currently sidebar items are reached with keys `1`–`9`. Renumber so that:
- `0` → Inbox (first built-in folder)
- `1` → Today
- `2` → Upcoming
- `3` → Waiting On
- `4` → Someday
- `5`–`9` → user-created folders in order

This aligns with zero-indexed muscle memory and leaves `1`–`9` covering up to 9 user folders
after the 5 built-in slots.

**Acceptance criteria:**
- [x] `0` focuses Inbox; `1` focuses Today; `2` focuses Upcoming; `3` focuses Waiting On; `4` focuses Someday
- [x] `5`–`9` focus the 1st–5th user-created folder (in sidebar order)
- [x] Keys beyond the available folder count are silently ignored
- [x] Help screen keybinding table updated to reflect new numbering
- [x] Tests updated / added for the new mapping

---

## Group: Task movement semantics

### ~~BACKLOG-37 — Context-aware `t` key (Inbox → move to Today; other folders → schedule today)~~ ✅ DONE

**Story points:** 3

**Description:**
The `t` key currently moves a task from Waiting On to Today (`move_to_today`). Extend its
behaviour to cover all folders, with two distinct semantics:

| Current folder | `t` behaviour |
|---|---|
| **Inbox** | Move task to the Today folder (same as the existing Waiting On → Today move) |
| **Waiting On** | *(unchanged)* Move task to Today |
| **User-defined folder** | Set `scheduled_date = today` so the task surfaces in the Today smart view without being physically moved |
| **Today / Upcoming / Someday / Logbook** | No-op (already in the right place or archived) |

**Acceptance criteria:**
- [x] `t` in Inbox moves the task to the Today folder and refreshes the sidebar count
- [x] `t` in Waiting On continues to move the task to Today (existing behaviour preserved)
- [x] `t` in a user-created folder sets `scheduled_date = date.today()` and the task appears in Today's smart view
- [x] `t` is a no-op when the current folder is Today, Upcoming, Someday, or Logbook
- [x] Undo reverses the action in all cases
- [x] Unit tests cover all four branches; integration test covers Inbox → Today

---

## Group: System integration

### ~~BACKLOG-38 — Allow Ctrl-Z to suspend (background) the app~~ ✅ DONE

**Story points:** 1

**Description:**
Ctrl-Z is the standard Unix terminal shortcut for suspending a foreground process (sending
`SIGTSTP`). Textual intercepts it by default. The app should let Ctrl-Z through so the user
can background the TUI and return with `fg`.

**Acceptance criteria:**
- [x] Pressing Ctrl-Z suspends the app and returns to the shell prompt (standard `fg`/`bg` flow works)
- [x] The app resumes correctly when brought back to the foreground
- [x] No other keybindings are affected

---

### ~~BACKLOG-39 — y / p clipboard integration in title and notes VimInput fields~~ ✅ DONE

**Story points:** 5

**Description:**
When editing a task's title or notes in the detail view, the user should be able to:
- **`y` (COMMAND mode):** yank the entire current line to the system clipboard (and to an
  internal unnamed register)
- **`p` (COMMAND mode):** paste the unnamed register (or system clipboard if register is empty)
  after the cursor on the current line; in multi-line mode inserts below the current line
- **`P` (COMMAND mode):** paste before the cursor / above the current line

This follows standard vim clipboard conventions, using `pyperclip` (already a dependency).

**Acceptance criteria:**
- [x] `y` in COMMAND mode in any VimInput copies the current line to the system clipboard and internal register
- [x] `p` in COMMAND mode pastes register content after cursor (single-line) or as a new line below (multi-line)
- [x] `P` pastes before cursor / above current line
- [x] Pasting works even when the system clipboard is unavailable (falls back to internal register)
- [x] Unit tests cover yank and paste in both single-line and multi-line modes

---

## Group: Power features

### BACKLOG-40 — Regex support in search

**Story points:** 3

**Description:**
The global search (`/`) currently does case-insensitive substring matching. Add opt-in regex
support: when the query starts with `/` (i.e. the user types `//pattern`), interpret it as a
Python regex. Plain queries (no leading `/`) continue to behave as substring search.

Alternatively (simpler UX): always attempt regex; fall back to literal substring if the pattern
is invalid. Either approach is acceptable — confirm with user before implementing.

**Acceptance criteria:**
- [ ] Regex queries match titles and notes correctly (e.g. `buy (milk|bread)`)
- [ ] Invalid regex patterns fall back gracefully to literal substring search (no crash)
- [ ] Match highlighting in the results list works for regex matches (highlight the matched span)
- [ ] `search_tasks()` unit tests cover regex matching and the invalid-pattern fallback
- [ ] Search status bar hints that regex is supported

---

### ~~BACKLOG-41 — Persist undo buffer across sessions~~ ✅ DONE

**Story points:** 8

**Description:**
The undo stack is currently held in memory and lost when the app exits. Persisting it lets
users undo actions from a previous session — useful when e.g. accidentally deleting tasks and
then restarting before noticing.

The undo stack entry is a `list[Task]` snapshot. Serialise it alongside the main task/folder
data in `data.json` (or a companion `undo.json`). Apply a cap (e.g. 20 entries) to keep the
file size manageable.

**Acceptance criteria:**
- [x] Undo stack survives app restart (at least the last 20 operations)
- [x] `u` after restart restores the previous state as expected
- [x] Undo history is capped at 20 entries to bound file size
- [x] Old `data.json` files without undo history load without error (empty undo stack)
- [x] Encrypted databases store undo history encrypted alongside task data
- [x] Unit tests cover save/load round-trip of the undo stack; integration test verifies cross-session undo

---

## Group: Vim completeness

### BACKLOG-42 — VimInput: `f`/`F`/`t`/`T` find-char motions ✅ DONE

**Story points:** 3

**Description:**
Vim's find-char motions let users jump to a specific character on the current line without counting words or pressing `h`/`l` repeatedly. `f<ch>` moves to the next occurrence of `ch`; `F<ch>` moves backward; `t<ch>` stops one position before the char; `T<ch>` stops one position after.

**Acceptance criteria:**
- [x] `f<ch>` in COMMAND mode moves cursor to next occurrence of `ch` on current line; no-op if not found
- [x] `F<ch>` moves cursor to previous occurrence of `ch` on current line; no-op if not found
- [x] `t<ch>` moves cursor to one position before the next `ch`; `T<ch>` one position after the previous `ch`
- [x] `;` repeats the last `f`/`F`/`t`/`T` in the same direction; `,` repeats in the opposite direction
- [x] All four motions are scoped to the current logical line in multi-line mode (do not cross newlines)
- [x] Tests cover all four commands, `;`, `,`, no-match cases, and multi-line boundary

---

### BACKLOG-43 — VimInput: `gg` / `G` jump-to-first/last

**Story points:** 2

**Description:**
Add `gg` (jump to start of text) and `G` (jump to end of text) to VimInput in all modes. These complement the existing `0`/`$` line-level jumps with document-level jumps.

**Acceptance criteria:**
- [x] `gg` in COMMAND mode moves cursor to the beginning of the text (offset 0)
- [x] `G` in COMMAND mode moves cursor to the last character of the text (last line in multi-line)
- [x] Both work in single-line and multi-line VimInput
- [x] Tests cover both in single-line and multi-line mode

---

### BACKLOG-44 — VimInput: `^` first-non-blank motion

**Story points:** 1

**Description:**
`^` moves the cursor to the first non-blank (non-space) character of the current line, matching vim's behaviour. This is distinct from `0` which goes to column 0 unconditionally.

**Acceptance criteria:**
- [x] `^` in COMMAND mode moves cursor to the first non-space character of the current line
- [x] Works in both single-line and multi-line mode (scoped to current line)
- [x] On a line with no leading spaces, behaves identically to `0`
- [x] Tests cover leading spaces, no leading spaces, and multi-line variants

---

## Group: GTD feature gaps

### BACKLOG-45 — "Anytime" folder (unscheduled active tasks) ✅ DONE

**Story points:** 3

**Description:**
The Things app distinguishes between **Anytime** (active, unscheduled tasks) and **Someday** (low-priority, parked). A native Anytime folder makes it clear which work is active but flexible in timing, separate from Someday.

**Acceptance criteria:**
- [x] Built-in "Anytime" folder created on app initialization; old `data.json` files without it load with an empty Anytime folder
- [x] Anytime appears in the sidebar between Today and Upcoming
- [x] `o`/`O` create tasks in Anytime when the Anytime view is active
- [x] `m` (move) works correctly to move tasks in/out of Anytime
- [x] Sidebar numbering adjusts: `2`=Anytime, `3`=Upcoming, `4`=Waiting On, `5`=Someday
- [x] Tests confirm Anytime appears in sidebar order and tasks display correctly

---

### BACKLOG-46 — Flag/Star tasks

**Story points:** 5

**Description:**
A star/flag marker lets users mark tasks as high-priority without creating a separate folder. Flags are a binary attribute; flagged tasks are visually distinct and optionally shown in a cross-folder "Flagged" view.

**Acceptance criteria:**
- [ ] `Task.is_flagged: bool = False` field; old JSON files load safely with `is_flagged = False`
- [ ] `!` in NORMAL mode toggles flag on selected task; `!` in VISUAL mode toggles on all selected
- [ ] Flagged tasks show a visual indicator in task list rows (e.g., `★` prefix)
- [ ] Task detail view shows flag state and allows toggling
- [ ] Storage round-trip tested; integration tests cover flag toggle in NORMAL and VISUAL modes

---

### BACKLOG-47 — Start date field

**Story points:** 5

**Description:**
A `start_date` field controls when a task becomes actionable. Tasks with a future start date are hidden from Today, Upcoming, and search until the date arrives. Complements the existing `scheduled_date` (when to do it) and `deadline` (when it must be done).

**Acceptance criteria:**
- [ ] `Task.start_date: date | None = None`; old JSON files load safely
- [ ] Task detail view has a Start Date field; accepts the same input formats as scheduled date
- [ ] Tasks with a future start date do not appear in Today, Upcoming, or search results
- [ ] Once start_date arrives (on app launch), the task surfaces in the appropriate smart view
- [ ] Help text explains start date semantics

---

### BACKLOG-48 — Regex support in search

**Story points:** 3

**Description:**
The global search (`/`) currently does case-insensitive substring matching. Add opt-in regex support: when the query starts with `/` (i.e. the user types `//pattern`), interpret it as a Python regex. Plain queries continue as substring search.

**Acceptance criteria:**
- [ ] Regex queries (prefixed with `/`) match titles and notes correctly (e.g. `buy (milk|bread)`)
- [ ] Invalid regex patterns fall back gracefully to literal substring search (no crash)
- [ ] Match highlighting in results works for regex matches
- [ ] `search_tasks()` unit tests cover regex matching and the invalid-pattern fallback
- [ ] Search prompt shows a hint that `//pattern` enables regex

---

### BACKLOG-49 — "Waiting for" person field on Waiting On tasks

**Story points:** 3

(This is BACKLOG-28 but renumbered here for completeness — see the original entry above under BACKLOG-28.)

---

### BACKLOG-50 — Tags / Contexts

**Story points:** 8

(This is BACKLOG-30 — see original entry above.)

---

### BACKLOG-51 — Projects

**Story points:** 13

(This is BACKLOG-31 — see original entry above.)

---

### BACKLOG-52 — Areas of responsibility

**Story points:** 8

(This is BACKLOG-32 — see original entry above.)

---

## Group: Power features (new)

### BACKLOG-53 — Export to plain text / CSV / markdown ✅ DONE

**Story points:** 5

**Description:**
Users may want to export their tasks for backup or external processing. Add simple export formats as CLI flags.

**Acceptance criteria:**
- [x] `--export=txt` exports tasks as newline-delimited plaintext (one task per line)
- [x] `--export=csv` exports as CSV with columns: folder, title, date, deadline, notes
- [x] `--export=md` exports as markdown with folder headings and task lists
- [x] `--export=json` exports as lossless JSON (added — recommended for backup/import)
- [x] `--output=<path>` writes to a file instead of stdout
- [x] `--import=<path>` imports tasks/folders from a JSON export file (non-destructive merge)
- [x] Unit tests verify export format correctness and import round-trip

---

### BACKLOG-54 — Snooze / Defer task ✅ DONE

**Story points:** 5

**Description:**
"Snooze" temporarily hides a task and re-surfaces it at a later time, without requiring a permanent reschedule.

**Acceptance criteria:**
- [x] `Task.snoozed_until: datetime | None = None`; old JSON files load safely
- [x] Snoozed tasks are excluded from Today, Upcoming, and search results
- [x] `z` keybinding opens a snooze-duration picker (1 hour, 3 hours, tomorrow, 1 week, custom)
- [x] On app launch, expired snooze timers are resolved and tasks re-appear in smart views
- [x] Snoozed status indicated in task list rows (e.g., `[Snoozed until Thu]`)

---

### BACKLOG-55 — Bulk multi-field edit in VISUAL mode

**Story points:** 5

**Description:**
Extend VISUAL mode bulk operations to batch-edit multiple fields (notes, deadline, estimate) on all selected tasks in a single dialog.

**Acceptance criteria:**
- [ ] `e` in VISUAL mode opens a bulk-edit modal
- [ ] Modal allows selecting which fields to edit (only checked fields are updated)
- [ ] Bulk edit is a single undo step
- [ ] Unit tests verify field masking; integration tests confirm multi-task updates

---

### BACKLOG-56 — Time estimate field

**Story points:** 5

**Description:**
A lightweight time estimate field (e.g., 5m, 30m, 2h) helps users plan and batch similar-effort work.

**Acceptance criteria:**
- [ ] `Task.estimated_duration: str | None = None`; old JSON files load safely
- [ ] Task detail view has an estimated duration field (free text)
- [ ] Common durations displayed in task list rows as a dim suffix (`(30m)`)
- [ ] `e` in VISUAL mode (outside bulk-edit) opens an estimate picker for all selected tasks

---

### BACKLOG-57 — UI acceptance test suite

**Story points:** 8

**Description:**
Implement a structured suite of UI acceptance tests using Textual's headless Pilot API that captures the most important user journeys end-to-end. Goal: catch regressions in keyboard flows, modal interactions, and view transitions automatically.

**Key test scenarios:**
- Task creation → detail view → edit title → Esc back to list
- Schedule a task from Today → verify it disappears
- Create a recurring task → complete → verify it re-appears with new date
- Search → navigate results → open task
- VISUAL mode: select range → bulk delete

**Acceptance criteria:**
- [ ] At least 10 new end-to-end Pilot tests covering the above scenarios
- [ ] Tests use headless `run_test()` and do not rely on screen rendering details
- [ ] All tests run in CI under 60 seconds
- [ ] Test failures produce clear messages identifying which step failed

---

### BACKLOG-58 — config_and_vim feature batch ✅ DONE

**Story points:** 8

**Description:**
Eight improvements implemented together: vim motions, config options, UX polish.

**Features delivered:**
- [x] Bug fix: `?` opens calendar picker from inline schedule input (`s` key flow)
- [x] VimInput `%` / `d%` / `c%` bracket-matching motions
- [x] Checklist item rename with `r` in checklist navigation mode
- [x] Configurable screen border (`border_style`, `border_block_size` in config)
- [x] Configurable color theme (`theme` in config: blue/red/yellow/green)
- [x] tmux ESCDELAY one-time tip at startup
- [x] Configurable sidebar counts (`[sidebar_counts]` config section)
- [x] `dd` populates the yank register (enables `p`/`P` after delete)

---

### BACKLOG-59 — Border text banner ✅ DONE

**Story points:** 3

**Description:**
When a coloured screen border is active (`border_style != "none"`), show a configurable text label centred in both the top and bottom horizontal border strips. The text background matches the primary border colour (yellow for `yellow_grey`, red for `red_grey`).

**Acceptance criteria:**
- [ ] `Config.border_text: str = ""` — empty string means no banner
- [ ] `save_default_config()` includes `border_text = ""` in the `[ui]` section
- [ ] When non-empty, the text appears centred in both top and bottom `ColorBorderStrip` widgets, padded with a single space on each side
- [ ] The text background colour is the first colour of the border pair (e.g. yellow for yellow_grey)
- [ ] The left/right sides continue the alternating block pattern
- [ ] `load_config()` reads `border_text` from `[ui]`
- [ ] Test: horizontal strip renders with centred text

---

### BACKLOG-60 — Auto-populate missing config defaults ✅ DONE

**Story points:** 2

**Description:**
When the app starts and reads an existing config file that is missing some keys (because new config options were added in a later version), automatically append those missing keys with their default values to the config file. Non-destructive: never modifies existing content.

**Acceptance criteria:**
- [ ] `_ensure_config_defaults(path, raw_dict)` is called after successfully loading a config file
- [ ] Any missing key in `[timeout]`, `[ui]`, or `[sidebar_counts]` is appended with its default value
- [ ] If an entire section is missing, the section header is appended before the keys
- [ ] The original file content is never modified (only appended to)
- [ ] After the call, re-reading the file produces a complete config
- [ ] Tests verify: missing section gets appended, missing key in existing section gets appended, file with all keys is unchanged

---

### BACKLOG-61 — Default cursor at top-left in text fields ✅ DONE

**Story points:** 2

**Description:**
When a task detail screen opens, the cursor in all VimInput fields should start at position 0 (top-left), not at the end of the text. Currently, long titles and multi-line notes place the cursor at the right or middle, making it hard to see the full content on open.

**Acceptance criteria:**
- [ ] `VimInput` gains a `start_at_beginning: bool = False` constructor parameter
- [ ] When `True`, `_cursor = 0`, `_view_row = 0`, `_view_offset = 0` at init
- [ ] `detail-title-input`, `detail-notes-input`, and all other read-mode VimInput fields in `TaskDetailScreen` use `start_at_beginning=True`
- [ ] Tests: VimInput with `start_at_beginning=True` starts with cursor at 0

---

### BACKLOG-62 — Divider tasks ✅ DONE

**Story points:** 3

**Description:**
If a task's title is exactly `-` or `=`, render it as a full-width horizontal divider line in the task list (filled with `-` or `=` characters). This lets users visually separate groups of tasks without creating a folder.

**Acceptance criteria:**
- [ ] `is_divider_task(task) -> bool` returns `True` when `task.title.strip() in ("-", "=")`
- [ ] Divider tasks render as a dim full-width line of dashes or equals signs in the task list
- [ ] Action keys that modify task state (x, d, s, m, w, t, J, K) are no-ops on divider tasks in normal mode
- [ ] Divider tasks are excluded from VISUAL mode selection (treated like separators)
- [ ] Creating a divider is done normally with `o` / typing `-` or `=`
- [ ] Tests: is_divider_task, rendering, action guards

---

### BACKLOG-63 — Duplicate task with y then p/P ✅ DONE

**Story points:** 3

**Description:**
In the task list, `y` yanks the selected task to both the clipboard (existing behaviour) and an internal task register. `p` pastes a duplicate of the yanked task immediately below the current position; `P` pastes above. The duplicate gets a new UUID and the current timestamp as `created_at`, but copies all other fields (title, notes, tags, folder_id, project_id, scheduled_date).

**Acceptance criteria:**
- [ ] `y` in NORMAL mode copies to clipboard (unchanged) AND saves to `GtdApp._task_register: Task | None`
- [ ] `p` inserts a duplicate below the currently selected task
- [ ] `P` inserts a duplicate above the currently selected task
- [ ] The new task has a fresh `id` and `created_at = datetime.now()`; all other fields are copied
- [ ] Duplicate is inserted at the correct position in the folder's task list
- [ ] Status bar shows `(task duplicated)` after paste
- [ ] Tests: duplicate creates new task, position is correct, original is unchanged

---

### BACKLOG-64 — Quick task rename with r from task list ✅ DONE

**Story points:** 2

**Description:**
From the task list (NORMAL mode), pressing `r` opens an inline rename input pre-filled with the selected task's current title. On submit, saves the new title. This avoids needing to open the full task detail screen for a simple title change.

**Acceptance criteria:**
- [ ] `r` in NORMAL mode (task list focused) enters INSERT mode with `#task-input` pre-filled with the task title
- [ ] On submit, calls `edit_task()` with the new title and refreshes the list
- [ ] Pressing Escape cancels without changes
- [ ] Cannot be used on divider tasks
- [ ] Status bar shows "Rename: type new title, Enter to save, Esc to cancel"
- [ ] Tests: submit saves new title, Esc cancels, divider guard

---

### BACKLOG-65 — HML navigation in VISUAL block mode ✅ DONE

**Story points:** 2

**Description:**
`H`, `M`, `L` already work in NORMAL mode to jump to the top/middle/bottom of the list. Add the same keys to VISUAL block mode so users can extend a selection to a distant row in one keystroke.

**Acceptance criteria:**
- [ ] In VISUAL mode, `H` moves the cursor to the top of the list and extends the selection
- [ ] In VISUAL mode, `M` moves the cursor to the middle of the list and extends the selection
- [ ] In VISUAL mode, `L` moves the cursor to the bottom of the list and extends the selection
- [ ] Visual highlights and status bar update after each move
- [ ] Tests: H/M/L in visual mode change cursor index and update highlights

---

### BACKLOG-66 — Help screen accessible from sidebar focus ✅ DONE

**Story points:** 1

**Description:**
`?` opens the help screen only when the task list has focus. When the sidebar has focus, `?` does nothing. Add `?` handling to `_handle_sidebar_key` so help is accessible regardless of focus.

**Acceptance criteria:**
- [ ] Pressing `?` while the sidebar has focus opens HelpScreen
- [ ] The existing `?` behaviour in the task list is unchanged
- [ ] Tests: `?` from sidebar opens HelpScreen

---

### BACKLOG-67 — Move task to project with m; visual block move to project ✅ DONE

**Story points:** 5

**Description:**
Extend the `m` key to open a unified action picker (modal overlay) that lists Folders, Projects, and Tags in separate sections. Selecting a folder moves the task (existing behaviour). Selecting a project assigns the task to that project (sets `task.project_id`). Selecting a tag adds the tag to the task. Works in both NORMAL and VISUAL block mode.

**Acceptance criteria:**
- [ ] `m` opens `_ActionPickerScreen` modal instead of switching focus to the sidebar
- [ ] The picker shows three sections: Folders, Projects, Tags
- [ ] Selecting a folder: moves task(s) to that folder (existing logic)
- [ ] Selecting a project: assigns task(s) to that project via `assign_task_to_project()`; task stays in current folder
- [ ] Selecting a tag: adds the tag to task(s) via a new `add_tag_to_task()` helper; does not replace existing tags
- [ ] VISUAL mode `m` opens the same picker for all selected tasks
- [ ] Esc cancels with no changes
- [ ] Tests: folder move, project assign, tag add, visual block, cancel

---

### BACKLOG-68 — Add tag to task with m (merged into BACKLOG-67) ✅ DONE

**Story points:** 0

**Description:**
See BACKLOG-67 — tag addition via `m` is implemented as part of the unified action picker.

**Acceptance criteria:**
- [ ] See BACKLOG-67

---

### BACKLOG-69 — Vim count prefix for commands ✅ DONE

**Story points:** 8

**Description:**
Support a numeric count prefix for vim motions in both the task list and VimInput. Examples: `5j` moves down 5 rows, `2dd` deletes 2 tasks, `20i-Esc` inserts 20 dashes, `5w` moves 5 words forward.

**Acceptance criteria:**
- [ ] VimInput: digits 1–9 (and `0` when buffer non-empty) accumulate in `_count_buffer`; cleared when a non-digit key is pressed
- [ ] VimInput count applies to: `h`, `l`, `j`, `k`, `w`, `b`, `e`, `W`, `B`, `E`, `x`, `X`, `0` (only as motion, when buffer empty), motion commands
- [ ] VimInput `Ni` (N then i): count captured before `i`; on ESC the inserted text is replicated N times total
- [ ] Task list: `_count_buf` in GtdApp accumulates digits in NORMAL mode; applied to `j`, `k`, `G` (jump to row N), `d` (delete N tasks)
- [ ] Count is shown in the status bar while being accumulated
- [ ] ESC clears the count buffer
- [ ] Tests cover: 5j motion, 2dd delete, count + motion in VimInput, NiXXXEsc repeat

---

### BACKLOG-70 — Bug: multiline notes not indented in CLI summary ✅ DONE

**Story points:** 1

**Description:**
The `--summary` CLI flag prints task notes, but notes with embedded newlines are printed without indentation on the continuation lines, making them misaligned with the leading `  - title` line.

**Acceptance criteria:**
- [ ] Each line of a multiline note is indented with four spaces (`    `)
- [ ] Single-line notes are unchanged
- [ ] Tests: `_print_summary` with a task whose notes contain `\n` produces correctly indented output

---

### BACKLOG-71 — Review :help text and README for completeness ✅ DONE

**Story points:** 3

**Description:**
After the feature batch 59–71 is implemented, do a full pass over `HelpScreen._HELP_TEXT` and `README.md` to ensure every implemented keybinding and feature is documented.

**Acceptance criteria:**
- [ ] All new keybindings from this batch are listed in `HelpScreen._HELP_TEXT`
- [ ] `README.md` reflects the current feature set
- [ ] No stale keybindings remain in the help text
- [ ] The config file reference in README shows all current config options

---

### BACKLOG-72 — Configurable backups, spell check, capitalization; release tooling ✅ DONE

**Story points:** 8

**Description:**
Rotating backups after save (`[backup]` in config), optional English spell check and capitalization fixes on submit (`[text]`), GitHub release notes reorder script, and maintainer docs for protecting `main` with PR-only rules.

**Acceptance criteria:**
- [x] `[backup]` with throttle, directory, daily/weekly/monthly retention; copies `.json` or encrypted blob
- [x] `[text]` per-field toggles for spell and capitalization; `spell_check_as_you_type` reserved in config
- [x] `scripts/reorder_changelog_section.py` + release workflow; `CLAUDE.md` documents both
- [x] `README` / `CLAUDE.md` describe GitHub rulesets for `main`
- [x] Tests for backup rotation, text processing, changelog script, config load

---

## Group: GTD methodology gaps

### BACKLOG-73 — Guided GTD weekly review workflow

**Story points:** 8

**Description:**
BACKLOG-19 added a weekly review screen that shows tasks completed in the last 7 days. A full GTD weekly review is a structured, multi-step process: clear the inbox, review all active projects, check the someday list, sweep each area, and record the review date. This feature adds a guided walkthrough mode distinct from the existing logbook-style completion list.

- `W` (or a dedicated key from the sidebar) launches the guided review
- Steps walk through: Inbox → Today → Projects (one at a time) → Someday → Waiting On
- Each step prompts: "Is this still relevant? (y/n/s)" to complete, keep, or move to someday
- Review date is recorded in `data.json`; a "Last reviewed: N days ago" badge appears in the sidebar

**Acceptance criteria:**
- [ ] Guided review mode is a distinct screen from the existing completed-tasks view
- [ ] Steps cycle through Inbox, Today, each Project, Someday, Waiting On in order
- [ ] At each step, `y` keeps the item, `n` deletes it, `s` moves it to Someday, `d` sets a deadline, `Esc` pauses the review
- [ ] Review completion timestamp stored in `data.json`; sidebar shows "Last reviewed: N days ago"
- [ ] Help text updated to document the review flow
- [ ] Integration tests cover the step-cycle and the `y`/`n`/`s` actions

---

### BACKLOG-74 — Horizons of Focus: Goals and Vision levels

**Story points:** 8

**Description:**
GTD defines six "horizons of focus" above Next Actions: Projects → Areas → Goals (1–2 yr) → Vision (3–5 yr) → Purpose/Principles. Areas (BACKLOG-32) implement the third horizon. This feature adds the fourth and fifth horizons as first-class objects that can be attached to Areas and Projects.

- `Goal` dataclass: title, notes, optional target year, `area_id` (optional)
- `Vision` dataclass: title, notes (long-form)
- Sidebar section "Horizons" lists Goals and Visions, collapsible
- Tasks and Projects can be linked to a Goal via `goal_id`

**Acceptance criteria:**
- [ ] `Goal` and `Vision` dataclasses with storage round-trip; old JSON files load without error
- [ ] Sidebar "Horizons" section lists Goals (with linked area) and Visions
- [ ] `N` while Horizons section is focused creates a new Goal or Vision (user selects type)
- [ ] Task detail view has an optional "Goal" linkage field
- [ ] Project sidebar entry shows linked Goal name as a dim suffix when set
- [ ] Tests cover Goal/Vision CRUD, area linkage, and task-to-goal assignment

---

### BACKLOG-75 — Mind sweep guided capture mode

**Story points:** 5

**Description:**
GTD's "mind sweep" is a facilitated capture exercise: a series of prompts ("What's on your mind about work? finances? relationships? health?") that surfaces items the user hasn't yet captured. Completing a mind sweep ensures the inbox is genuinely empty.

- A dedicated mode (accessible via `:sweep` command or a keybinding) displays prompts one at a time
- User types a response and presses Enter to capture it to Inbox, or Esc to skip
- A configurable prompt list lives in `config.toml` under `[sweep]`
- Progress shown: "Prompt 4 of 12"

**Acceptance criteria:**
- [ ] Mind sweep mode launches and cycles through prompts sequentially
- [ ] Each response is captured as a new Inbox task
- [ ] Skipped prompts are recorded; after all prompts, a summary screen shows how many items were captured
- [ ] `[sweep]` section in `config.toml` allows customizing the prompt list
- [ ] `save_default_config()` includes a sensible default prompt list
- [ ] Tests cover prompt cycling, Inbox insertion, and skip behaviour

---

### BACKLOG-76 — Stale task surfacing / aging alerts

**Story points:** 3

**Description:**
GTD systems rot when tasks are captured and then ignored. This feature flags tasks that have sat in Inbox or Anytime for more than a configurable number of days without being touched (scheduled, moved, completed, or edited).

- `Task.last_touched_at: datetime` — updated on any mutation; existing tasks default to `created_at`
- A "Stale" indicator (e.g., dim yellow `[stale]` suffix) appears on qualifying task rows
- Configurable threshold: `[review] stale_threshold_days = 14` in `config.toml`
- A `:stale` command (or sidebar filter) shows only stale tasks across all active folders

**Acceptance criteria:**
- [ ] `Task.last_touched_at` updated on edit, schedule, move, flag, tag change; old files default to `created_at`
- [ ] Tasks older than `stale_threshold_days` in Inbox or Anytime show a visual indicator
- [ ] `:stale` command (or dedicated view) filters to stale tasks only
- [ ] Completing or rescheduling a task clears the stale state immediately
- [ ] `[review] stale_threshold_days` in config with default 14; `save_default_config()` updated
- [ ] Tests cover stale detection logic and the `:stale` filter

---

### BACKLOG-77 — Tickler file (date-triggered task surfacing)

**Story points:** 5

**Description:**
The classic GTD tickler file (43 folders: 31 daily + 12 monthly) surfaces reference items or reminders on a specific calendar date. This is distinct from Upcoming (which shows tasks with a scheduled date to *do* something) — Tickler items appear as a reminder to *review or act on* a reference item.

- A built-in "Tickler" folder where tasks have a required `tickle_date`
- On `tickle_date`, the task surfaces in Today with a `[Tickler]` prefix; after that date it stays in Today until actioned
- Tasks in Tickler are hidden from all views until their tickle date arrives

**Acceptance criteria:**
- [ ] Built-in Tickler folder (`folder_id = "tickler"`) in the sidebar
- [ ] Tasks in Tickler require a date; `o`/`O` to create immediately prompts for date
- [ ] On launch, tasks whose `tickle_date <= today` move to Today with a `[Tickler]` prefix
- [ ] Tasks with a future tickle date are invisible in all smart views and search
- [ ] Sidebar count shows only un-surfaced future tickle items
- [ ] Tests cover date-triggered surfacing and the hidden-until-date behaviour

---

## Group: TUI / interface gaps

### BACKLOG-78 — Side-by-side split view (task list + detail pane) ✅ DONE

**Story points:** 8

**Description:**
Currently the task detail screen is a modal overlay that replaces the task list. A split view shows the task list on the left and the detail pane on the right simultaneously, like a mail client (Mutt, Aerc). This reduces the friction of reviewing and editing tasks sequentially.

- Toggled with a keybinding (e.g., `\` or a config option `split_view = true`)
- Left pane: task list (same as today); right pane: detail of the currently selected task, auto-updating as the cursor moves
- Editing in the right pane uses INSERT mode; `h`/`l` switches focus between panes

**Acceptance criteria:**
- [x] `\` toggles between split view and the current full-screen layout
- [x] Right pane shows title, date, deadline, notes, checklist of the selected task
- [x] Moving `j`/`k` in the left pane updates the right pane immediately
- [x] `l` transfers focus to the right pane for editing; `h` returns to the task list
- [x] Edits in the right pane save on `Esc` or on `h` (leaving the pane)
- [x] Split ratio is configurable: `split_ratio = 0.6` (left width fraction) in `config.toml`
- [x] Tests cover pane switching, auto-update, and edit-save flow

---

### BACKLOG-79 — Fuzzy finder (fzf-style search across all tasks)

**Story points:** 5

**Description:**
The existing `/` search does case-insensitive substring matching. A fuzzy finder (like `fzf` or Telescope in Neovim) ranks results by how closely they match the query characters in order, even non-contiguously. Type `bmlk` to match "Buy milk" by matching b-m-l-k.

- Accessible via a distinct keybinding (e.g., `Ctrl+P` or `<leader>f`) separate from `/`
- Results ranked by fuzzy score; top result highlighted
- Filtering is real-time as the user types
- Selecting a result navigates to the task

**Acceptance criteria:**
- [ ] `Ctrl+P` opens the fuzzy finder overlay
- [ ] Results update in real-time ranked by fuzzy match score (title match weighted higher than notes)
- [ ] Selecting a result closes the overlay and navigates to the task in its folder
- [ ] `Esc` closes without navigation
- [ ] `fuzzy_search_tasks()` domain function is unit-tested with known inputs and expected rankings
- [ ] Integration test: `Ctrl+P` opens overlay; typing narrows results; Enter navigates

---

### BACKLOG-80 — Command palette / ex-mode colon commands

**Story points:** 5

**Description:**
Power users expect a command line for actions that don't warrant a dedicated keybinding. Pressing `:` opens an ex-style input (like Vim's command mode) where the user can type commands such as `:sort deadline`, `:move inbox`, `:tag @work`, `:stale`, `:sweep`.

- `:` enters command mode; status bar shows the command being typed
- A small set of built-in commands; extensible without new keybindings
- Tab completion for command names and argument values (folder names, tag names)
- `Esc` cancels; Enter executes

**Acceptance criteria:**
- [ ] `:` in NORMAL mode (task list or sidebar) enters command mode; status bar shows `:`-prefixed input
- [ ] Supported commands include: `:sort <field>`, `:move <folder>`, `:tag <tag>`, `:stale`, `:sweep`, `:help`
- [ ] Tab completes command names and known arguments (folder/tag names)
- [ ] Unknown command shows `"Unknown command: foo"` in status bar
- [ ] `Esc` cancels without action
- [ ] Unit tests for command dispatch; integration test for `:sort` and `:move`

---

### BACKLOG-81 — External editor for task notes ($EDITOR) ✅ DONE

**Story points:** 3

**Description:**
Long-form task notes are awkward to write in the inline VimInput widget. Pressing `E` (capital) in the task detail view opens the notes field in the user's `$EDITOR` (same pattern as `git commit`). On save-and-quit, the notes are updated in the task.

- Suspends the Textual TUI, spawns `$EDITOR` with the notes in a temp file, resumes after the editor exits
- Falls back to `nano` if `$EDITOR` is not set
- Works only from the task detail view notes field

**Acceptance criteria:**
- [x] `Ctrl+E` in the detail view notes field suspends TUI and opens `$EDITOR <tempfile>`
- [x] On editor exit, temp file contents replace the notes field value
- [x] If `$EDITOR` is unset, uses `nano`
- [x] If the editor exits with a non-zero code, notes are unchanged
- [x] TUI resumes cleanly after editor closes
- [x] Tests mock the subprocess call and verify notes are updated on success and unchanged on failure

---

### BACKLOG-82 — Markdown-rendered notes in detail view ✅ DONE

**Story points:** 5

**Description:**
Task notes are stored as plain text but many users naturally write Markdown (headings, bold, lists, links). Textual ships a `Markdown` widget that renders Markdown to styled text. This feature renders notes as Markdown in read mode and switches to the raw VimInput in edit mode.

- Read mode (COMMAND focus on notes): Markdown rendered
- Edit mode (INSERT focus): raw VimInput (existing behaviour)
- Toggle with a keybinding or automatic on focus change

**Acceptance criteria:**
- [x] Notes displayed using Textual's `Markdown` widget in read mode
- [x] Pressing `i`/`a`/`o` on the notes field switches to raw VimInput (INSERT mode)
- [x] `Esc` from INSERT mode returns to Markdown rendered view
- [x] Markdown rendering supports: headings, bold, italic, bullet lists, code blocks
- [x] Fallback: if notes contain no Markdown syntax, rendered output is visually identical to plain text
- [x] Tests: notes with Markdown syntax render without error; edit/save round-trip preserves raw text

---

### BACKLOG-83 — Multiple sort orders for task list

**Story points:** 3

**Description:**
Tasks within a folder are currently displayed in manual (positional) order. Users should be able to sort by other criteria without permanently reordering their manual positions.

- Sort orders: manual (default), by due date ascending, by deadline ascending, by creation date, by title (alphabetical)
- Sort is a view-level setting, not stored in the data model; manual order is always preserved underneath
- The current sort is shown in the status bar: `[sorted: deadline]`
- `:sort <field>` command (BACKLOG-80) or a dedicated key (`S` cycles through sort orders)

**Acceptance criteria:**
- [ ] `S` in NORMAL mode cycles through: manual → due date → deadline → created → title → manual
- [ ] Sort indicator shown in status bar when non-manual sort is active
- [ ] Switching back to manual restores original positional order
- [ ] Sort persists for the session but resets to manual on restart (or optionally saved to config)
- [ ] Tests: each sort order produces correct task ordering given a known task list

---

### BACKLOG-84 — Vim marks (m{letter} / '{letter} task bookmarks)

**Story points:** 3

**Description:**
Vim's mark system lets users bookmark positions and jump back. In gtd-tui, `m{a-z}` marks the currently selected task, and `'{letter}` jumps to the marked task (switching folders if needed).

- Marks are session-scoped (not persisted to disk)
- Jumping to a mark switches the sidebar to the task's folder and moves the cursor to that task
- `''` (two apostrophes) jumps back to the position before the last mark-jump

**Acceptance criteria:**
- [ ] `m{a-z}` in NORMAL mode stores a reference to the selected task under that letter
- [ ] `'{letter}` navigates to the marked task (switches folder view if the task is in a different folder)
- [ ] `''` returns to the previous cursor position (before the most recent `'` jump)
- [ ] Marking a deleted task: jumping to a deleted mark shows `"Mark '{letter}' is no longer valid"` in the status bar
- [ ] Tests cover mark set, jump, cross-folder jump, and stale mark handling

---

### BACKLOG-85 — Column / table view

**Story points:** 5

**Description:**
An optional table layout shows each task as a spreadsheet row with visible columns: title, due date, deadline, tags, and estimated duration. Useful for scanning and comparing task attributes across many tasks at once.

- Toggled with `\` (if not used by split view) or a config option `default_view = "table"`
- Column widths are fixed or proportional to the terminal width
- All existing keybindings work identically in table view

**Acceptance criteria:**
- [ ] `Ctrl+T` (or config key) toggles between list view and table view
- [ ] Table columns: Title, Date, Deadline, Tags, Est. — all truncated to fit terminal width
- [ ] Columns with all-empty values are hidden automatically
- [ ] `j`/`k` navigation, `x`, `d`, `m`, `s` all work identically to list view
- [ ] `default_view = "list" | "table"` option in `config.toml`
- [ ] Tests: table view renders correct column data; keybindings still function

---

## Group: General application gaps

### BACKLOG-86 — Task templates

**Story points:** 5

**Description:**
Frequently-repeated workflows (e.g. "Onboard new client", "Weekly release", "Travel packing") involve the same set of tasks every time. Task templates allow saving a task (or a project with subtasks/checklist items) as a reusable blueprint that can be instantiated with one command.

- Templates stored in `~/.local/share/gtd_tui/templates.json`
- `Ctrl+T` in the task list opens a template picker; selecting one creates the task(s) in the current folder
- Templates can be saved from an existing task: `T` in detail view saves the task as a template

**Acceptance criteria:**
- [ ] `T` in task detail view saves the current task (title, notes, checklist, tags) as a named template
- [ ] `Ctrl+T` in the task list (NORMAL mode) opens a template picker modal
- [ ] Selecting a template instantiates the task(s) in the current folder with fresh IDs and `created_at`
- [ ] Project templates create the project and all its sub-tasks in one step
- [ ] Templates persist across restarts; storage round-trip tested
- [ ] Tests: save template, list templates, instantiate template (task and project variants)

---

### BACKLOG-87 — Desktop notifications for due tasks

**Story points:** 5

**Description:**
When the app is closed, there is no way to be reminded of tasks due today or tasks with approaching deadlines. A lightweight background checker (invoked via a systemd user timer or launchd plist) sends a desktop notification listing due tasks.

- `gtd-tui --notify` checks for tasks due today and deadlines within 24 hours; sends a notification and exits
- On Linux: uses `notify-send`; on macOS: uses `osascript`; on Windows: no-op with a warning
- Notification body lists up to 5 task titles; if more, shows "…and N more"
- CLAUDE.md / README documents how to set up the systemd timer

**Acceptance criteria:**
- [ ] `gtd-tui --notify` prints nothing to stdout and exits 0 if no due tasks; exits 0 with notification if tasks are due
- [ ] `notify-send` called with title "gtd-tui" and body listing due-today tasks and near-deadline tasks
- [ ] Falls back gracefully if `notify-send` / `osascript` is not installed (prints a warning to stderr, exits 0)
- [ ] Works with encrypted databases (prompts for password via `getpass`)
- [ ] README includes a systemd user timer unit file example
- [ ] Tests mock `subprocess.run` and verify correct task list is passed to the notification command

---

### BACKLOG-88 — Quick-add CLI

**Story points:** 3

**Description:**
Adding a task requires opening the full TUI. A `gtd add` subcommand lets users capture tasks from the shell without launching the UI — useful from shell aliases, scripts, or Alfred/Raycast.

- `gtd-tui add "Buy milk" [--folder inbox] [--due tomorrow] [--tag @errands] [--project "Shopping"]`
- Writes directly to `data.json` (or encrypted blob) and exits
- Default folder is Inbox if `--folder` is not specified

**Acceptance criteria:**
- [ ] `gtd-tui add "title"` creates a task in Inbox and exits 0
- [ ] `--folder`, `--due`, `--tag`, `--project` flags are all optional and functional
- [ ] `--due` accepts the same natural-language formats as the TUI date field
- [ ] Works with encrypted databases (prompts for password)
- [ ] Prints `"Added: <title>"` to stdout on success
- [ ] Tests cover each flag combination; integration test verifies the task appears in the data file

---

### BACKLOG-89 — Keyboard shortcut customization

**Story points:** 5

**Description:**
All keybindings are currently hardcoded in `app.py`. Power users may want to remap keys (e.g., change `x` to Space-only, remap `w` to something else, add custom shortcuts). Allow overriding keybindings via `config.toml`.

- `[keys]` section in `config.toml` maps action names to key sequences
- A curated set of action names covers all major operations (complete, delete, schedule, move, etc.)
- Conflicting or invalid key specs print a warning at startup and fall back to the default

**Acceptance criteria:**
- [ ] `[keys]` section in `config.toml`; `save_default_config()` includes commented-out defaults for all action names
- [ ] At startup, custom key mappings override defaults; conflicts logged as warnings
- [ ] At minimum, the following actions are remappable: `complete`, `delete`, `schedule`, `move`, `waiting_on`, `today`, `undo`, `redo`, `search`, `help`
- [ ] `load_config()` validates key specs (rejects multi-char sequences where single-char is required)
- [ ] Tests: load config with custom key, verify action fires on custom key and not on old key

---

### BACKLOG-90 — Undo history viewer

**Story points:** 5

**Description:**
The undo stack (BACKLOG-41) persists up to 20 operations but is only accessible one step at a time with `u`. An undo history viewer shows the full list of undoable actions with descriptions, and allows jumping to any point in the stack.

- Accessible via `:history` command or `Ctrl+U`
- Each entry shows: action type, timestamp, affected tasks (title list)
- Selecting an entry in the viewer undoes all operations back to that point (equivalent to pressing `u` N times)

**Acceptance criteria:**
- [ ] `Ctrl+U` opens the undo history modal
- [ ] Modal lists up to 20 undo entries, most recent first, with action type and short description
- [ ] Selecting an entry undoes back to that state (all intermediate steps applied)
- [ ] `Esc` closes without any undo
- [ ] Tests: viewer lists correct entries; selecting entry N undoes correctly

---

## Group: Project management gaps

### BACKLOG-91 — Task dependencies (blocked-by relationships)

**Story points:** 8

**Description:**
In complex projects, some tasks cannot start until another is complete. A `blocked_by` field links tasks, and blocked tasks are visually dimmed and excluded from the Today smart view until their blockers are complete.

- `Task.blocked_by: list[str]` — list of task UUIDs this task is waiting on
- In the task list, blocked tasks show a `[blocked]` indicator and are dimmed
- Today view excludes blocked tasks; Upcoming view also excludes them
- When all blockers complete, the task automatically becomes unblocked

**Acceptance criteria:**
- [ ] `Task.blocked_by: list[str]` (default `[]`); old JSON files load without error
- [ ] Task detail view has a "Blocked by" field listing linked tasks (by title), editable
- [ ] `B` in NORMAL mode opens a task picker to add a blocker to the selected task
- [ ] Blocked tasks are visually dimmed in the task list with a `[blocked]` suffix
- [ ] Today and Upcoming smart views exclude blocked tasks
- [ ] Completing the last blocker task automatically removes its ID from all `blocked_by` lists
- [ ] Tests cover blocking, unblocking on completion, and Today/Upcoming exclusion

---

### BACKLOG-92 — Time tracking (start/stop timer per task)

**Story points:** 8

**Description:**
For users who need to track time spent on tasks (for billing, retrospectives, or focus), a lightweight start/stop timer can be attached to any task. The elapsed time is displayed in the task row and in the detail view, and can be exported.

- `Task.time_log: list[tuple[datetime, datetime | None]]` — list of (start, stop) pairs; `None` stop means currently running
- `T` in NORMAL mode starts/stops the timer on the selected task
- Status bar shows "Timer running: Buy milk [0:23]" when a timer is active
- `--export=csv` / `--export=json` includes accumulated time

**Acceptance criteria:**
- [ ] `Task.time_log` field; old JSON files load without error
- [ ] `T` starts the timer (sets a new open-ended entry); `T` again stops it (fills in the stop time)
- [ ] Only one task can have a running timer at a time; starting a new timer auto-stops any running one
- [ ] Task rows show total logged time as a dim suffix: `(1h 23m)`
- [ ] Detail view shows full time log (start, stop, duration per entry)
- [ ] Export formats include time data
- [ ] Tests: start/stop round-trip, auto-stop on new start, total duration calculation

---

### BACKLOG-93 — Sub-projects (nested projects)

**Story points:** 8

**Description:**
Complex outcomes ("Launch v2") often decompose into meaningful sub-outcomes ("Build auth", "Write docs", "Set up CI") that themselves contain tasks. Nested projects model this hierarchy.

- `Project.parent_id: str | None` — references another project
- Sub-projects appear indented under their parent in the sidebar
- A parent project's progress bar aggregates sub-project completion as well as direct tasks
- Maximum nesting depth: 2 (parent → sub-project → tasks); deeper nesting is rejected with an error

**Acceptance criteria:**
- [ ] `Project.parent_id: str | None` (default `None`); old JSON files load without error
- [ ] `N` while a project is selected in the sidebar offers "New sub-project" as an option
- [ ] Sub-projects appear indented under their parent in the sidebar with a `│ ◆` prefix
- [ ] Parent project progress includes all direct tasks plus all sub-project tasks
- [ ] Attempting to nest more than 2 levels shows an error: `"Max nesting depth (2) reached"`
- [ ] Deleting a parent project prompts: delete sub-projects too, or unlink them
- [ ] Tests cover creation, progress rollup, depth limit, and parent deletion options

---

## Group: Outside-the-box features

### BACKLOG-94 — AI task breakdown (Claude API integration)

**Story points:** 5

**Description:**
When a task title is vague ("Refactor auth", "Plan holiday"), it can be hard to know the next concrete action. Pressing `?` on a task sends the title (and optional notes) to the Claude API, which returns 4–6 concrete next-action suggestions. The user picks which to add as checklist items or sub-tasks.

- Opt-in: requires `[ai] api_key = "..."` in `config.toml`; no calls made without a key
- `?` in NORMAL mode (task list) sends the task to the API and opens a picker with the suggestions
- Each suggestion can be accepted (added as a checklist item), rejected, or edited before adding
- No task data is sent if `[ai] enabled = false` (default)

**Acceptance criteria:**
- [ ] `[ai] enabled = false` and `[ai] api_key = ""` in default config; feature is off by default
- [ ] `?` with a valid API key calls the Claude API with the task title and notes
- [ ] Response is parsed into a list of action suggestions; displayed in a picker modal
- [ ] Each suggestion has `[a]ccept`, `[e]dit`, `[s]kip` options; accepted items added as checklist items
- [ ] Network errors or invalid API key show a user-friendly error in the status bar; no crash
- [ ] Task data is never sent when `enabled = false`
- [ ] Tests mock the API call and verify suggestion parsing, checklist insertion, and error handling

---

### BACKLOG-95 — Focus / distraction-free mode

**Story points:** 2

**Description:**
A full-screen, decoration-free view showing only today's tasks. Hides the sidebar, status bar decorations, and border. Useful when actually doing work and wanting to see only the current task list with minimal chrome.

- `F` toggles focus mode on/off
- In focus mode: sidebar is hidden, border is hidden, header shows only "Today" or current folder name
- All keybindings continue to work normally; `F` restores the full layout

**Acceptance criteria:**
- [ ] `F` hides the sidebar and all decorative elements; `F` again restores them
- [ ] Task list expands to fill the full terminal width in focus mode
- [ ] Status bar remains visible (needed for INSERT mode indicator)
- [ ] `focus_mode_on_launch = false` config option in `[ui]`
- [ ] Tests: `F` toggles sidebar visibility; task list width changes

---

### BACKLOG-96 — Pomodoro timer

**Story points:** 5

**Description:**
A built-in 25-minute work timer with a 5-minute break timer. The timer is linked to the currently selected task and shown in the status bar. When the timer expires, a desktop notification fires (if available) and the status bar updates.

- `P` in NORMAL mode starts a Pomodoro on the selected task; `P` again pauses/resumes; Esc cancels
- Status bar shows `🍅 Buy milk [18:42]` while running
- After 25 min, a break timer (5 min) starts automatically
- Pomodoro count per task stored in `Task.pomodoro_count: int`

**Acceptance criteria:**
- [ ] `P` starts a 25-minute countdown linked to the selected task
- [ ] Status bar shows task name and remaining time, updated every second
- [ ] On expiry, a notification fires (if `notify-send` / `osascript` is available) and break mode starts
- [ ] `Task.pomodoro_count` incremented on each completed Pomodoro; shown as `🍅 ×3` in the task list
- [ ] `[pomodoro] work_minutes`, `break_minutes`, `long_break_minutes`, `sessions_before_long_break` configurable in `config.toml`
- [ ] Tests: timer state transitions (start → running → expired → break); count increment

---

### BACKLOG-97 — Task aging visualization

**Story points:** 3

**Description:**
Tasks that have been sitting in Inbox or Anytime for a long time are visually highlighted to signal they need attention. The color of the task title fades from normal to yellow to orange to red based on days since `created_at` or `last_touched_at`.

- Age thresholds configurable: `[review] age_yellow_days = 7`, `age_orange_days = 14`, `age_red_days = 30`
- Only applies in Inbox and Anytime folders (not Today, Waiting On, Someday, Projects)
- Aging indicator is purely visual; no data model changes required beyond BACKLOG-76's `last_touched_at`

**Acceptance criteria:**
- [ ] Task titles in Inbox/Anytime folders render in yellow when age ≥ `age_yellow_days`
- [ ] Orange when age ≥ `age_orange_days`; red when age ≥ `age_red_days`
- [ ] Age is based on `last_touched_at` if BACKLOG-76 is implemented, otherwise `created_at`
- [ ] Other folders are unaffected
- [ ] Thresholds are configurable in `config.toml`; `save_default_config()` includes them
- [ ] Tests: task age → expected color mapping for each threshold

---

### BACKLOG-98 — Git-based sync across machines

**Story points:** 8

**Description:**
Many users work across multiple machines (desktop + laptop) and want their tasks synced without a cloud service. Git provides a zero-infrastructure sync mechanism: auto-commit `data.json` to a private repo on each save, and pull on each launch.

- `[sync] git_repo = "git@github.com:user/private-tasks.git"` in `config.toml`
- On save: `git add data.json && git commit -m "gtd-tui auto-sync" && git push` (async, non-blocking)
- On launch: `git pull --rebase` before reading `data.json`
- Conflict on pull: merge conflicts in JSON are detected; user is prompted to resolve or use local/remote version

**Acceptance criteria:**
- [ ] `[sync]` section in `config.toml`; sync is disabled by default
- [ ] When enabled and git is available, a pull is attempted on launch before loading data
- [ ] After each save, a non-blocking background push is initiated
- [ ] If push fails (network unavailable), a dim status bar message appears: `"Sync pending"`; retry on next save
- [ ] Merge conflict on pull: user is prompted with `[L]ocal / [R]emote / [C]ancel`
- [ ] Tests mock `subprocess.run` for git commands; verify pull-before-load and push-after-save sequence

---

### BACKLOG-99 — Daily session log

**Story points:** 3

**Description:**
At the end of each session (on graceful exit), append a one-line summary to a plain text log file: date, tasks completed, tasks created, and the active folder at exit. Simple productivity journaling without a separate app.

- Log file: `~/.local/share/gtd_tui/session.log` (configurable)
- Format: `2026-03-21 09:34 | completed: 7 | created: 3 | active: Today`
- Opt-in: `[log] session_log = true` in `config.toml`

**Acceptance criteria:**
- [ ] `[log] session_log = false` in default config (opt-in)
- [ ] `[log] session_log_path` configurable; defaults to `~/.local/share/gtd_tui/session.log`
- [ ] On clean exit, one line is appended in the documented format
- [ ] Completed count = tasks completed during the session; created count = tasks created during the session
- [ ] Log file is created if it doesn't exist; never truncated
- [ ] Tests: mock exit, verify appended line format and counts

---

### BACKLOG-100 — Advanced recurrence patterns (M-F, weekends, MWF, TR, nth weekday, etc.) ✅ DONE

**Story points:** 13 — New schedule fields on RepeatRule and RecurRule, new advance algorithms, extended parser, serialisation, display changes.

**Description:**
The existing repeat/recur system only supports simple N-days/weeks/months/years intervals. This feature adds rich schedule patterns to both `RepeatRule` (calendar-fixed) and `RecurRule` (completion-relative):

- **Day-of-week sets:** M-F (weekdays), weekends, MWF, TR, any single day (every Monday), biweekly single day (every other Tuesday)
- **Nth weekday of month:** 4th Thursday, 1st Monday, 3rd Wednesday, etc.
- **Convenience aliases:** `monthly` (= 1 month), `quarterly` (= 3 months), `annually`/`yearly` (= 1 year)

**Data model additions:**
```python
@dataclass
class RepeatRule:
    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    next_due: date
    days_of_week: list[int] = []   # Mon=0..Sun=6; empty = use interval/unit
    nth_weekday: tuple[int, int] | None = None  # (nth, weekday) e.g. (4, 3) = 4th Thursday

@dataclass
class RecurRule:  # same new fields
    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    days_of_week: list[int] = []
    nth_weekday: tuple[int, int] | None = None
```

**Accepted input strings (Repeat and Recurring fields):**

| Input | Pattern |
|---|---|
| `M-F`, `weekdays` | Mon–Fri daily |
| `weekends` | Sat+Sun |
| `MWF` | Mon, Wed, Fri |
| `TR` | Tue, Thu |
| `every monday` (or any weekday name) | Weekly on that day |
| `every other tuesday` | Biweekly on that day |
| `4th thursday`, `fourth thursday` | 4th Thursday of each month |
| `monthly` | Every 1 month (alias) |
| `quarterly` | Every 3 months (alias) |
| `annually`, `yearly` | Every 1 year (alias) |
| `7 days`, `2 weeks`, `1 month` | Existing simple intervals (unchanged) |

**Task list display (short codes after ↻):**

| Pattern | Display |
|---|---|
| M-F | ↻ M-F |
| weekends | ↻ weekends |
| MWF | ↻ MWF |
| TR | ↻ TR |
| every Mon | ↻ every Mon |
| every other Tue | ↻ every other Tue |
| 4th Thu | ↻ 4th Thu |
| Simple intervals | ↻ (unchanged, no suffix) |

**Acceptance criteria:**
- [x] `RepeatRule.days_of_week` and `RepeatRule.nth_weekday` fields; old JSON without them loads cleanly (default to empty/None)
- [x] Same fields on `RecurRule`; same backward-compatibility
- [x] `parse_repeat_input` parses all new patterns; raises `InvalidRepeatError` for unrecognised input; returns `ParsedRepeat` (NamedTuple with `interval`, `unit`, `days_of_week`, `nth_weekday`)
- [x] `spawn_repeating_tasks` advances M-F / MWF / TR / weekend / nth-weekday repeat rules correctly
- [x] `complete_task` advances completion-relative recur rules with the same logic
- [x] Task list row shows `↻ M-F` etc. for named patterns; simple intervals keep bare `↻`
- [x] Detail screen Repeat/Recurring fields normalise to the canonical short form on submit
- [x] Storage round-trip for all new fields (`days_of_week`, `nth_weekday`) in both RepeatRule and RecurRule
- [x] Unit tests for: parser (all new patterns), advance functions (weekday cycle, nth-weekday roll-over to next month), `spawn_repeating_tasks` with a weekday rule, `complete_task` with a weekday recur rule
- [x] All existing repeat/recur tests still pass

---

### BACKLOG-101 — Import tasks from Markdown checkbox list ✅ DONE

**Story points:** 5

**Problem:** No way to bulk-import tasks from a `.md` file (e.g. from another tool, brain-dump, or AI-generated list).

**Implementation:**
- `portability.import_md(text, target_folder_id)` parses `- [ ] title` / `- [x] title` lines; indented lines → notes; completed get `completed_at = now()`
- CLI: `gtd-tui --import tasks.md [--import-folder FOLDER]` auto-detects `.md` extension
- TUI: `Ctrl+I` opens `ImportMdScreen` modal (file path + folder picker)
- Status message: `imported N tasks: M active, K completed → folder`

**Acceptance criteria:**
- [x] `import_md()` parses `[ ]` as active and `[x]` as completed tasks
- [x] Indented lines after a task become notes
- [x] Headings and non-checkbox lines are ignored
- [x] CLI `--import tasks.md` routes to `_cmd_import_md()`; `--import-folder` sets destination
- [x] TUI `Ctrl+I` opens `ImportMdScreen`; imported tasks merge into task list and persist
- [x] Unit tests in `tests/test_portability.py`; integration tests in `tests/app/test_import.py`

---

### BACKLOG-102 — Vim-style cut-paste for tasks (d/p/P) ✅ DONE

**Story points:** 5

**Problem:** `y`/`p` duplicates tasks; there is no way to *move* a task to another position or folder via keyboard cut-paste.

**Implementation:**
- `d` (normal) and visual `d` cut task(s) into `_cut_register` (separate from `_task_register` used by `y`)
- `p`/`P` paste cut tasks below/above cursor in the current view, updating `folder_id` and `position`
- Undo after `d` restores the task and clears `_cut_register`
- `y`/`p` (duplicate) is unchanged; `_cut_register` only set by `d`

**Acceptance criteria:**
- [x] `d` populates `_cut_register` with the deleted task
- [x] `p` after `d` moves the task below cursor position; `P` moves above
- [x] Cross-folder paste updates `folder_id` to the current view's folder
- [x] Visual `d` puts all selected tasks into `_cut_register`
- [x] Undo after `d` restores task and clears register
- [x] `y`/`p` still creates a duplicate; `_cut_register` stays empty
- [x] Integration tests in `tests/app/test_cutpaste.py`

---

### BACKLOG-103 — i18n: Full translation of all UI strings ✅ DONE

**Story points:** 8

**Problem:** All UI strings are hardcoded in English with no way to use another language.

**Implementation:**
- `gtd_tui/i18n/__init__.py` — `t(key, **kwargs)` and `set_language(lang)` helpers
- `gtd_tui/i18n/locales/en.json` — ~200 English strings (source of truth)
- Locale files for es, fr, de, zh, ja, ru
- `Config.language = "en"`; `save_default_config()` adds commented `# language = "en"` in `[ui]`
- All hardcoded strings in `app.py` replaced with `t("key")` calls
- `GtdApp.on_mount()` calls `set_language(self._config.language)`

**Acceptance criteria:**
- [x] `t("key")` returns English for unknown keys (fallback to key itself)
- [x] `set_language("es")` loads Spanish translations
- [x] Missing keys in a locale fall back to English
- [x] Unknown language code falls back to English
- [x] All 7 locale files have core sidebar keys (inbox, today, anytime, upcoming, someday, logbook)
- [x] Parameterised strings (`mode_visual`, `imported_tasks`, etc.) interpolate correctly
- [x] `tests/test_i18n.py` covers all above behaviours
