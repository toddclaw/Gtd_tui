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

### BACKLOG-3 — Waiting On folder

**Story points:** 8 — Sidebar is the dominant new piece (split pane, `h`/`l` focus switching between sidebar and task list). Date-surfacing logic reuses BACKLOG-2's mechanism.

**Description:**
- A built-in folder called **Waiting On** holds tasks that are blocked on someone else
- Tasks in Waiting On behave like scheduled tasks: they have an optional date
- When the date arrives, the task surfaces in Today automatically
- Tasks without a date stay in Waiting On until manually moved

**Acceptance criteria:**
- [ ] Waiting On appears in the sidebar
- [ ] Tasks can be created in or moved to Waiting On
- [ ] Date-triggered surfacing works identically to BACKLOG-2
- [ ] Surfaced tasks are visually distinguishable as coming from Waiting On (e.g. a tag or indicator)

---

### BACKLOG-4 — User-created folders

**Story points:** 8 — Folder CRUD (create, rename, delete), confirmation dialog for non-empty folder deletion, and task-move UI (`m` key + destination picker) are all new interaction patterns. Depends on sidebar from BACKLOG-3.

**Description:**
- Users can create custom folders through the TUI (beyond the built-ins: Today, Waiting On, Logbook)
- Folders appear in the sidebar
- Tasks can be created in or moved to any folder
- Folders can be renamed and deleted (deleting a non-empty folder requires confirmation)

**Acceptance criteria:**
- [ ] Keybinding to create a new folder from the sidebar (e.g. `N` while sidebar is focused)
- [ ] Folder name entry uses INSERT mode
- [ ] New folder appears in sidebar immediately and persists across restarts
- [ ] Tasks can be moved between folders (`m` to move, then select destination)
- [ ] Deleting a folder with tasks inside prompts: delete tasks too, or move to Inbox

---

### BACKLOG-5 — Repeating tasks (time-based, independent of completion)

**Story points:** 8 — Requires a task detail/edit view (none exists yet), a new RepeatRule data model with storage migration, and launch-time task-spawning logic. The edit view alone is a significant new UI component.

**Description:**
- A task can be marked as **repeating** with an interval: every N days / weeks / months / years
- On each due date, a **new task** with the same title, notes, and folder is created automatically
- This happens regardless of whether the previous instance was completed — the schedule is fixed to the calendar, not to completion
- The original task is not modified; a fresh copy appears in Today on the repeat date

**Acceptance criteria:**
- [ ] Task edit view has a repeat field: interval + unit (e.g. `7 days`, `1 month`)
- [ ] On app launch, any repeat tasks whose next due date has arrived generate a new task in Today
- [ ] The new task is a full copy (same title, notes, folder) with no repeat setting of its own (or repeat setting preserved, depending on user preference — clarify before implementing)
- [ ] Repeat schedule is stored on the source task and survives restarts
- [ ] Completing or deleting a repeating task does not cancel future instances

**Data model addition:**
```python
@dataclass
class RepeatRule:
    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    next_due: date
```

---

### BACKLOG-6 — Recurring tasks (completion-relative scheduling)

**Story points:** 5 — Incremental on BACKLOG-5: edit view and repeat infrastructure already exist, this adds a completion hook that spawns the next instance with a floating due date.

**Description:**
- A task can be marked as **recurring** with an offset: N days / weeks / months / years after completion
- When the task is marked complete, a **new task** with the same details is created, with its scheduled date set to `completion_date + offset`
- Unlike repeating (BACKLOG-5), the next instance's date floats relative to when the current one was done

**Acceptance criteria:**
- [ ] Task edit view allows selecting recurring mode distinct from repeating mode
- [ ] On task completion, a new task is automatically created with the computed scheduled date
- [ ] The new task appears in Today on its scheduled date (same mechanism as BACKLOG-2)
- [ ] Recurring setting is preserved on each generated task

**Distinction from BACKLOG-5:**

| | Repeating | Recurring |
|---|---|---|
| Schedule anchor | Fixed calendar date | Completion date |
| Missed instance | New task still appears on schedule | Deferred until you actually complete it |
| Example | "Pay rent — 1st of every month" | "Floss — 1 day after last done" |

---

### BACKLOG-7 — Someday folder

**Story points:** 3 — Simple folder type with no auto-promotion logic. Once the sidebar is built in BACKLOG-3, this is primarily adding a folder variant and ensuring tasks never surface automatically.

**Description:**
- A built-in folder called **Someday** for tasks with no specific date or urgency
- Tasks in Someday do not appear in Today unless explicitly moved there
- Someday is a standard GTD holding area — tasks live here until the user promotes them

**Acceptance criteria:**
- [ ] Someday appears in the sidebar as a built-in folder (below Today, above user-created folders)
- [ ] Tasks can be created directly in Someday or moved there from any other folder
- [ ] Tasks in Someday never surface in Today automatically (no date-based promotion)
- [ ] Tasks can be moved from Someday to Today or any other folder manually

---

### BACKLOG-8 — Global search across all folders

**Story points:** 8 — Real-time filter-as-you-type requires reactive updates on every keystroke, result grouping with separators across folders, match highlighting within labels, and navigate-to-folder on selection. All new UI patterns.

**Description:**
- A search mode that matches tasks by title or notes text across every folder simultaneously
- Results are ordered: active folders first (Today, Waiting On, Someday, user folders), Logbook results last
- Within each group, results are ordered by relevance (title match > notes match) then by recency

**Acceptance criteria:**
- [ ] `/` from any view opens a search prompt
- [ ] Results update incrementally as the user types (filter-as-you-type)
- [ ] Results are grouped: active folders first, Logbook last — with a visible separator
- [ ] Selecting a result navigates to that task in its folder and closes search
- [ ] `Esc` cancels search and returns to the previous view
- [ ] Search is case-insensitive; matches are highlighted in results

---

## Notes for AI Assistants

- BACKLOG-1 and BACKLOG-2 are **complete**. The full project structure exists (`pyproject.toml`, `gtd_tui/`, `tests/`). When implementing new features, extend the existing codebase rather than scaffolding from scratch.
- **TDD is required.** Write tests before or alongside every feature. Do not implement logic without a corresponding test.
- Always run `pytest` (or suggest it) after adding/modifying Python source files.
- Prefer **minimal, focused changes** — avoid adding speculative abstractions before the design stabilizes.
- The UI should be modeled after the **Things iPhone app** — reference its information architecture (Inbox, Today, Upcoming, Anytime, Someday, Projects, Areas, Logbook) when making design decisions.
- **Vi keybindings are a first-class requirement.** All navigation and editing actions must be reachable via vi-style keys. Implement modal state (NORMAL/INSERT) from the start — do not retrofit it later.
- Storage format decisions (JSON vs SQLite) should be confirmed with the user before implementation, as they affect migration complexity later.
- Default data directory should follow XDG conventions (`~/.local/share/gtd_tui/` on Linux) using the `platformdirs` package.
- Follow the security rules in the Security section — especially: no network calls, atomic file writes, `600` permissions on the data file, no `shell=True`.
