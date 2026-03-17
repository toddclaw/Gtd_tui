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
- **Clipboard tool** (for the `y` yank keybinding):
  - Linux/X11: `sudo apt-get install xclip` (or `xsel`)
  - Linux/Wayland: `sudo apt-get install wl-clipboard`
  - macOS/Windows: no extra install needed
  - **tmux note:** tmux may not inherit `DISPLAY`. Add `set-environment -g DISPLAY ":1"` to `~/.tmux.conf` if `y` reports clipboard unavailable.

### Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd Gtd_tui

# Recommended: use uv (generates reproducible environment from uv.lock)
uv sync
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# Alternative: use pip directly
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Install pre-commit hooks (enforces black/ruff/mypy at commit time)
pre-commit install

# Run the application
python -m gtd_tui

# Run tests
pytest

# Format code
black .

# Lint
ruff check .

# Type check
mypy gtd_tui/

# Run all pre-commit checks manually
pre-commit run --all-files
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

### Release Process

When the user asks to make a release (e.g. "release v1.3.0" or "merge and tag"), follow these steps in order — do not skip any:

1. **Commit pending changes** on the current feature branch (if any uncommitted work exists)
2. **Push the feature branch** to remote: `git push origin <branch>`
3. **Checkout main**: `git checkout main`
4. **Merge the feature branch**: `git merge <branch> --no-ff -m "Merge branch '<branch>' — v<X.Y.Z>"`
5. **Bump version** in `pyproject.toml`: `version = "X.Y.Z"`
6. **Commit the version bump**: `git commit -m "Bump version to X.Y.Z"`
7. **Create annotated tag**: `git tag -a vX.Y.Z HEAD -m "vX.Y.Z — <short summary of changes>"`
8. **Push main**: `git push origin main`
9. **Push tags**: `git push origin vX.Y.Z`
10. **Return to feature branch**: `git checkout <branch>`

GitHub Actions will automatically build the wheel and publish the release once the tag arrives.

---

## Key Files Reference

| File | Purpose |
|---|---|
| `README.md` | User-facing project description |
| `CLAUDE.md` | This file — AI assistant conventions |
| `BACKLOG.md` | Feature backlog with all story details |
| `pyproject.toml` | Package metadata and dependencies |
| `gtd_tui/__main__.py` | Entry point — keep thin |
| `gtd_tui/app.py` | Application state, event loop |
| `gtd_tui/ui.py` | All TUI rendering logic |

---

## Feature Backlog

See [BACKLOG.md](BACKLOG.md) for the full feature backlog.

## Notes for AI Assistants

- BACKLOG-1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22 are **complete**. BACKLOG-23 is pending. The full project structure exists (`pyproject.toml`, `gtd_tui/`, `tests/`). When implementing new features, extend the existing codebase rather than scaffolding from scratch.
- **TDD is required.** Write tests before or alongside every feature. Do not implement logic without a corresponding test.
- Always run `pytest` (or suggest it) after adding/modifying Python source files.
- Prefer **minimal, focused changes** — avoid adding speculative abstractions before the design stabilizes.
- The UI should be modeled after the **Things iPhone app** — reference its information architecture (Inbox, Today, Upcoming, Anytime, Someday, Projects, Areas, Logbook) when making design decisions.
- **Vi keybindings are a first-class requirement.** All navigation and editing actions must be reachable via vi-style keys. Implement modal state (NORMAL/INSERT) from the start — do not retrofit it later.
- Storage format decisions (JSON vs SQLite) should be confirmed with the user before implementation, as they affect migration complexity later.
- Default data directory should follow XDG conventions (`~/.local/share/gtd_tui/` on Linux) using the `platformdirs` package.
- Follow the security rules in the Security section — especially: no network calls, atomic file writes, `600` permissions on the data file, no `shell=True`.
