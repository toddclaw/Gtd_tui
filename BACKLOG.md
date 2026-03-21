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

### BACKLOG-45 — "Anytime" folder (unscheduled active tasks)

**Story points:** 3

**Description:**
The Things app distinguishes between **Anytime** (active, unscheduled tasks) and **Someday** (low-priority, parked). A native Anytime folder makes it clear which work is active but flexible in timing, separate from Someday.

**Acceptance criteria:**
- [ ] Built-in "Anytime" folder created on app initialization; old `data.json` files without it load with an empty Anytime folder
- [ ] Anytime appears in the sidebar between Today and Upcoming
- [ ] `o`/`O` create tasks in Anytime when the Anytime view is active
- [ ] `m` (move) works correctly to move tasks in/out of Anytime
- [ ] Sidebar numbering adjusts: `2`=Anytime, `3`=Upcoming, `4`=Waiting On, `5`=Someday
- [ ] Tests confirm Anytime appears in sidebar order and tasks display correctly

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

### BACKLOG-54 — Snooze / Defer task

**Story points:** 5

**Description:**
"Snooze" temporarily hides a task and re-surfaces it at a later time, without requiring a permanent reschedule.

**Acceptance criteria:**
- [ ] `Task.snoozed_until: datetime | None = None`; old JSON files load safely
- [ ] Snoozed tasks are excluded from Today, Upcoming, and search results
- [ ] `z` keybinding opens a snooze-duration picker (1 hour, 3 hours, tomorrow, 1 week, custom)
- [ ] On app launch, expired snooze timers are resolved and tasks re-appear in smart views
- [ ] Snoozed status indicated in task list rows (e.g., `[Snoozed until Thu]`)

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
