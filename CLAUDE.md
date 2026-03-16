# CLAUDE.md — AI Assistant Guide for Gtd_tui

## Project Overview

**Gtd_tui** is a terminal user interface (TUI) application implementing the GTD (Getting Things Done) productivity methodology. It is written in Python and modeled after the Things iPhone app, adapted for a TUI environment.

- **Language:** Python
- **Paradigm:** TUI (Terminal User Interface)
- **Inspiration:** Things app (iPhone) — core GTD feature set adapted for the terminal
- **Methodology:** GTD (Getting Things Done) task/project management
- **Repository:** toddclaw/Gtd_tui

---

## Architectural Decisions (Settled — Do Not Re-litigate)

| Decision | Choice | Rationale |
|---|---|---|
| **App type** | TUI (interactive terminal app) | Session-based "open, use, close" workflow; Things-style navigation requires a rendered interface |
| **Not** | CLI file utility (todo.txt style) | One-shot commands and file-per-task patterns optimize for scripting, not for the intended UX |
| **TUI framework** | Textual | Best modern Python TUI library; CSS-like styling; built-in keyboard navigation |
| **Storage** | Single JSON file (`~/.local/share/gtd_tui/data.json`) | Simple, inspectable, easy to back up; no schema migrations early on |

---

## Repository Status

This project was recently initialized. As of the initial commit, only a `README.md` exists. There is no source code or configuration yet. When implementing features, follow the conventions below from the start.

---

## Development Setup

### Prerequisites

- Python 3.11+
- `pip` or `uv` for dependency management

### Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd Gtd_tui

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# Install dependencies (once requirements.txt / pyproject.toml exists)
pip install -e ".[dev]"

# Run the application
python -m gtd_tui

# Run tests
pytest

# Format code
black .

# Lint
ruff check .

# Type check
mypy .
```

---

## Expected Project Structure

When source code is added, follow this conventional Python project layout:

```
Gtd_tui/
├── CLAUDE.md               # This file
├── README.md               # User-facing documentation
├── pyproject.toml          # Package metadata and dependencies
├── .gitignore              # Python gitignore (__pycache__, .venv, etc.)
├── gtd_tui/                # Main package
│   ├── __init__.py
│   ├── __main__.py         # Entry point: python -m gtd_tui
│   ├── app.py              # Application state and event loop
│   ├── ui.py               # TUI rendering logic
│   ├── gtd/                # GTD domain logic
│   │   ├── __init__.py
│   │   ├── task.py         # Task data structures
│   │   ├── project.py      # Project groupings
│   │   └── context.py      # GTD contexts (@home, @work, etc.)
│   └── storage/            # Persistence layer
│       ├── __init__.py
│       └── file.py         # File-based storage (JSON/SQLite)
└── tests/                  # Tests
    ├── __init__.py
    ├── test_gtd.py
    └── test_storage.py
```

---

## Technology Choices (Recommended)

### TUI Framework

Prefer **[Textual](https://github.com/Textualize/textual)** — a modern Python TUI framework with a CSS-like styling system and reactive state management. Alternatively, **[urwid](https://github.com/urwid/urwid)** or raw **[curses](https://docs.python.org/3/library/curses.html)** are lighter options.

```toml
# pyproject.toml
[project]
dependencies = [
    "textual>=0.70",
]
```

### Storage

Start with JSON for simplicity, upgrade to SQLite if querying complexity grows:

```toml
# JSON (stdlib) — no extra dependency needed
# SQLite — use stdlib sqlite3 or:
dependencies = [
    "textual>=0.70",
]
```

### Things App Feature Alignment

Core features to implement (aligned with Things iPhone app):

| Feature | Description |
|---|---|
| **Inbox** | Quick capture, processed later |
| **Today** | Tasks scheduled or flagged for today |
| **Upcoming** | Scheduled tasks in the near future |
| **Anytime** | Active tasks with no specific schedule |
| **Someday** | Low-priority, parked tasks |
| **Projects** | Multi-step outcomes with sub-tasks |
| **Areas** | High-level responsibility areas (not time-bound) |
| **Logbook** | Completed tasks archive |
| **Tags** | Flexible labels across tasks/projects |
| **Deadlines** | Hard due dates on tasks/projects |
| **Checklists** | Sub-steps within a single task |

---

## GTD Domain Concepts

| Concept | Description |
|---|---|
| **Inbox** | Uncategorized capture of all incoming tasks/ideas |
| **Project** | Any outcome requiring more than one action step |
| **Next Action** | The immediate physical/digital action to move a project forward |
| **Context** | Location/tool tags for actions (e.g., `@computer`, `@phone`, `@errands`) |
| **Waiting For** | Items delegated to others, pending their response |
| **Someday/Maybe** | Low-priority items not actively being pursued |
| **Reference** | Non-actionable information stored for future use |
| **Weekly Review** | Regular review of all lists to keep the system current |

---

## Development Process

### Code Craftsmanship

This project follows code craftsmanship practices. Every piece of code should be written with care for the people (and AI assistants) who will read and maintain it next.

**Core principles:**

- **TDD** — tests are written before or alongside implementation, never after
- **SOLID** — apply SOLID principles throughout:
  - *Single Responsibility:* each class/function does one thing well
  - *Open/Closed:* extend behaviour without modifying existing code
  - *Liskov Substitution:* subtypes behave correctly wherever the base type is expected
  - *Interface Segregation:* small, focused interfaces over large general ones
  - *Dependency Inversion:* depend on abstractions, not concrete implementations
- **Readability** — code is read far more often than it is written; optimise for the reader
- **Testability** — if something is hard to test, that is a design smell; restructure until it is easy
- **Modularity** — keep modules small, focused, and loosely coupled; changes in one module should not ripple unexpectedly through others

**In practice this means:**
- Pure functions for all domain logic (no hidden state, no side effects)
- Side effects (storage, TUI) isolated at the edges of the system
- Short functions with clear names over long functions with comments explaining what they do
- No premature abstraction, but no copy-paste either — extract when a pattern appears twice

---

### Test-Driven Development (TDD)

This project uses TDD. Write tests before or alongside implementation — never after.

**Workflow:**
1. Write a failing test that describes the desired behaviour
2. Write the minimum code to make it pass
3. Refactor, keeping tests green

**What to test:**
- All GTD domain logic: task creation, completion, scheduling, filtering, sorting, state transitions
- Storage layer: read/write round-trips, corrupt/missing file handling
- Keybinding dispatch: modal state transitions (normal → insert → normal, etc.)
- Do **not** test Textual internals or pure rendering — test the logic that drives rendering

**Test location:** `tests/` mirroring the package structure (`tests/gtd/test_task.py`, `tests/storage/test_file.py`, etc.)

```bash
pytest                        # run all tests
pytest tests/gtd/             # run a subset
pytest --tb=short -q          # concise output
```

Tests must pass before every commit. A failing test suite blocks merging.

---

## UI Design Principles

### General

- **Clarity over cleverness.** Every screen should be immediately legible — what list am I in, what is selected, what actions are available.
- **Keyboard-first.** Every action reachable without a mouse. Mouse support is a bonus.
- **Minimal chrome.** Borders, status bars, and decorations should aid navigation, not fill space.
- **Fast.** Interactions should feel instant. No perceptible lag on a task list of hundreds of items.
- **Consistent.** Same key does the same thing everywhere possible. Surprises are bugs.

### Vi Keybindings

The UI **must** support vi-style navigation and editing throughout. This is a first-class requirement, not an optional mode.

**Modal editing:**

| Mode | Indicator | Purpose |
|---|---|---|
| `NORMAL` | Default | Navigation and commands |
| `INSERT` | Visible indicator in status bar | Text entry (task titles, notes) |

**Navigation (NORMAL mode):**

| Key | Action |
|---|---|
| `j` / `k` | Move selection down / up |
| `g g` | Jump to top of list |
| `G` | Jump to bottom of list |
| `Ctrl-d` / `Ctrl-u` | Half-page down / up |
| `h` / `l` | Navigate left/right (e.g. between sidebar and task list) |

**Actions (NORMAL mode):**

| Key | Action |
|---|---|
| `o` | Add new task below current (opens INSERT mode) |
| `O` | Add new task above current (opens INSERT mode) |
| `i` or `Enter` | Edit selected task (opens INSERT mode) |
| `x` or `Space` | Toggle task complete |
| `d d` | Delete selected task (with confirmation) |
| `u` | Undo last action |
| `/` | Search/filter tasks |
| `n` / `N` | Next / previous search match |
| `q` | Quit / close current view |

**INSERT mode:**

| Key | Action |
|---|---|
| `Esc` | Return to NORMAL mode |
| `Ctrl-c` | Cancel edit without saving |
| Standard text editing keys apply |

**Sidebar navigation:**

| Key | Action |
|---|---|
| `1`–`9` | Jump to nth sidebar item (Inbox, Today, etc.) |
| `Tab` / `Shift-Tab` | Cycle focus between sidebar and task list |

These bindings must be implemented in a dedicated keybinding module so they can be tested independently of the TUI framework.

---

## Security

This is a local personal productivity tool, but it should not be a security nightmare. Follow these rules:

### Data

- **Never** transmit task data over the network unless the user explicitly configures sync. No telemetry, no analytics, no silent outbound connections.
- Store data only in the user's own data directory (`~/.local/share/gtd_tui/`). Never write outside it without prompting.
- Do not log task content (titles, notes) to any log file — task data is private.

### File Handling

- Validate and sanitise any file path derived from user input before using it in filesystem operations (no path traversal: `../../etc/passwd`).
- When writing the JSON data file, write to a temp file and atomically rename — prevents data corruption on crash.
- Set file permissions to `600` (owner read/write only) on the data file.

### Input

- Task titles and notes are plain text. Do not interpret them as shell commands, HTML, or markup at any point.
- If the app ever spawns subprocesses (e.g., to open a URL), use a list-form `subprocess` call (never `shell=True`) and validate the input first.

### Dependencies

- Minimise third-party dependencies. Every dependency is an attack surface.
- Pin dependency versions in `pyproject.toml` and commit `requirements.lock` / use `uv lock`.
- Review changelogs before upgrading dependencies.

---

## Code Conventions

### General Python Style

- Format with **black** (line length 88)
- Lint with **ruff**
- Type-annotate all function signatures; use `mypy` for static checking
- Use `snake_case` for functions, variables, modules
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants
- Prefer `dataclasses` or `pydantic` models for domain objects

### Error Handling

- Use specific exception types; avoid bare `except:`
- Raise exceptions at boundaries, handle them at the appropriate layer
- Never silently swallow exceptions without a comment explaining why

### TUI Architecture Pattern

Follow a **Model-View-Controller** or **Elm-like** pattern:

```python
# State (model)
@dataclass
class AppState:
    tasks: list[Task]
    selected_index: int
    current_view: View

# Pure rendering from state (view)
def render(app: AppState) -> ...:
    ...

# Event handling → state mutation (controller)
def handle_key(app: AppState, key: str) -> AppState:
    ...
```

Keep rendering and state mutation strictly separated.

### Testing

- This project uses **TDD** — write tests before or alongside implementation (see Development Process above)
- Unit test domain logic (task creation, filtering, sorting, state transitions)
- Unit test keybinding dispatch and modal state machine
- Integration test the storage layer (read/write round-trips)
- Run `pytest` before every commit; a failing suite blocks merging

---

## Git Workflow

### Branching

- Development happens on feature branches: `claude/<description>-<id>`
- Do not push directly to `master`/`main`

### Commit Messages

Use clear, imperative commit messages:

```
Add inbox task capture with keyboard shortcut
Fix project deletion leaving orphaned tasks
Refactor storage layer to use JSON serialization
```

### Pre-commit Checklist

- [ ] `black .` — code is formatted
- [ ] `ruff check .` — no lint warnings
- [ ] `mypy .` — no type errors
- [ ] `pytest` — all tests pass

---

## Key Files Reference

| File | Purpose |
|---|---|
| `README.md` | User-facing project description |
| `CLAUDE.md` | This file — AI assistant conventions |
| `pyproject.toml` | Package metadata and dependencies |
| `gtd_tui/__main__.py` | Entry point — keep thin |
| `gtd_tui/app.py` | Application state, event loop |
| `gtd_tui/ui.py` | All TUI rendering logic |

---

## Feature Backlog

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

### BACKLOG-15 — Visual mode block selection and bulk operations

**Story points:** 8 — New modal state alongside NORMAL and INSERT; significant keybinding and rendering work.

**Description:**
- `v` in NORMAL mode enters VISUAL mode; selected tasks are highlighted distinctly
- `j` / `k` extend or shrink the selection
- Bulk operations apply to all selected tasks:
  - `s` — open date picker; date is applied to every selected task
  - `x` / Space — complete all selected tasks
  - `d d` — delete all selected tasks (with confirmation)
  - 'm' - move selected tasks to the picked folder
  - 'w' - move selected tasks to waiting-on folder
  - 't' - move selected tasks to today folder
  - 'J' / 'K' - move entire block of selected tasks down or up
- Esc exits VISUAL mode without performing any action

**Acceptance criteria:**
- [ ] `v` enters VISUAL mode; status bar shows `VISUAL`
- [ ] `j` / `k` extend selection downward / upward (anchor stays fixed)
- [ ] Selected rows are visually distinct from the cursor row
- [ ] `s` in VISUAL mode opens date picker; date applied to all selected tasks on confirm
- [ ] `x` / Space in VISUAL mode completes all selected tasks
- [ ] `d d` in VISUAL mode deletes all selected tasks after confirmation
- [ ] Esc cancels selection and returns to NORMAL mode
- [ ] All bulk operations are undoable as a single undo step

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

### BACKLOG-19 — Weekly review

**Story points:** 13 — a new full-screen view (weekly review).

**Description:**
2. **Weekly review** — a new view (accessible via a keybinding, e.g. `W`) showing all tasks completed in the last 7 days, grouped by folder, with completion timestamps

**Acceptance criteria:**
- [ ] `W` (or similar) opens the Weekly Review view
- [ ] Weekly Review lists completed tasks from the past 7 days, grouped by folder
- [ ] Folder name is shown as a section header in the review

---

### BACKLOG-20 — Deadline field

**Story points:** 8 — New data model field, rendering in red if past due, and days-remaining display.

**Description:**
- A task can have a **deadline** date separate from its scheduled date
- In the task list, if a deadline is set: show the deadline date; if past due, render in red; if due soon (≤ 3 days), render in yellow
- In the detail view, a dedicated Deadline field (below the date field)
- The days-remaining count is shown alongside the date: `[Dec 1 Mon — 3d left]` or `[Dec 1 Mon — 2d overdue]` in red

**Acceptance criteria:**
- [ ] Task detail view has a Deadline field
- [ ] Deadline date stored in `Task.deadline: date | None`
- [ ] Task rows show deadline info when set
- [ ] Past-due deadlines render in red
- [ ] Due-in-≤3-days deadlines render in yellow
- [ ] No deadline: no change to existing display

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

## Notes for AI Assistants

- BACKLOG-1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 21, 22 are **complete**. BACKLOG-19 is partially complete (WO auto-scheduling done; weekly review view not yet built). The full project structure exists (`pyproject.toml`, `gtd_tui/`, `tests/`). When implementing new features, extend the existing codebase rather than scaffolding from scratch.
- **TDD is required.** Write tests before or alongside every feature. Do not implement logic without a corresponding test.
- Always run `pytest` (or suggest it) after adding/modifying Python source files.
- Prefer **minimal, focused changes** — avoid adding speculative abstractions before the design stabilizes.
- The UI should be modeled after the **Things iPhone app** — reference its information architecture (Inbox, Today, Upcoming, Anytime, Someday, Projects, Areas, Logbook) when making design decisions.
- **Vi keybindings are a first-class requirement.** All navigation and editing actions must be reachable via vi-style keys. Implement modal state (NORMAL/INSERT) from the start — do not retrofit it later.
- Storage format decisions (JSON vs SQLite) should be confirmed with the user before implementation, as they affect migration complexity later.
- Default data directory should follow XDG conventions (`~/.local/share/gtd_tui/` on Linux) using the `platformdirs` package.
- Follow the security rules in the Security section — especially: no network calls, atomic file writes, `600` permissions on the data file, no `shell=True`.
