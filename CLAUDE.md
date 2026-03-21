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

# Install pre-commit hooks (black/ruff/mypy at commit time; pytest is NOT run on commit)
pre-commit install
pre-commit install --hook-type pre-push   # optional: full tests + linters before git push

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
- **Headless Pilot tests** that send keys to the main screen (e.g. `o`, `v`, `Enter` on a task) assume the **task list** has focus. Production default is `startup_focus_sidebar=true` (sidebar focused). Pass `config=CFG_TASK_LIST_FOCUS` from `tests.cfg` (or `replace(load_config(), startup_focus_sidebar=False)`) when constructing `GtdApp` unless the test explicitly drives the sidebar first.

---

## Git Workflow

### Branching

- Development happens on feature branches: `claude/<description>-<id>`
- Do not push directly to `master`/`main`

### Protecting `main` on GitHub (pull requests only)

To block direct pushes and merges to `main` so all changes go through pull requests:

1. Open the repository on GitHub → **Settings** → **Code and automation** → **Rules** → **Rulesets** (or **Branches** → **Branch protection rules** on older UIs).
2. **New ruleset** (or **Add rule**), target branch `main` (or `refs/heads/main`).
3. Enable **Require a pull request before merging** (set minimum approvals if you want reviews).
4. Enable **Block force pushes** (usually on by default for protected branches).
5. Optionally **Require status checks to pass** (e.g. your CI workflow) before merge.
6. To prevent admins from bypassing: under ruleset enforcement, disable **Allow bypass** for the roles that should not skip rules.

GitHub does not store this in the repo; each maintainer with admin access must configure it once per repository.

### Before starting work (branch sanity)

**Wrong-branch mistakes** (e.g. implementing a release fix on a stale feature branch, or mixing two PRs) waste time and confuse history. **Before writing code or committing**, confirm the following:

1. **Intended branch** — Run `git branch --show-current` and verify the name matches the work (e.g. the open PR branch for a release, or a new `claude/…` branch branched from current `main`). If you are not on the right branch: `git stash` (if needed), `git checkout <correct-branch>`, then `git stash pop`.
2. **Sync with remote** — Run `git fetch origin` then `git status -sb`. If you are **behind** `origin/<branch>`, pull before editing so you do not build on outdated code or fight avoidable merge conflicts:
   - `git pull origin <branch>`  
   - or `git pull --rebase origin <branch>` if your team prefers rebase.
3. **Tracking** — Optional: `git branch -vv` shows whether the current branch tracks the right remote (e.g. `[origin/claude/my-feature]`). After creating a new branch, set upstream on first push: `git push -u origin <branch>`.

For **release or PR-specific fixes**, explicitly name the target branch in the task (e.g. “work on `claude/vim-movement-folder-management` for PR #13”) and re-check step 1 after any `git checkout`.

### Commit Messages

Use clear, imperative commit messages:

```
Add inbox task capture with keyboard shortcut
Fix project deletion leaving orphaned tasks
Refactor storage layer to use JSON serialization
```

### Pre-push checklist

**Mandatory before every push.** Do not push until every item below passes. Commit-time `pre-commit` runs **black**, **ruff**, and **mypy** only — it does **not** run **pytest**, so a green commit hook does **not** mean tests pass.

1. **Full test suite** — `pytest` or `pytest tests/` (same as CI). The suite takes a few minutes; run it anyway.
2. **Format / lint / types** — `black --check .`, `ruff check .`, `mypy gtd_tui/` (or `pre-commit run --all-files` for the same checks pre-commit enforces at commit).
3. **Convenience script** — from the repo root with dev dependencies installed: `python scripts/pre_push_check.py` (runs steps 1–2 in order, using the current interpreter — activate `.venv` first).
4. **Optional automation** — install the pre-push hook so `git push` runs the same gate: `pre-commit install && pre-commit install --hook-type pre-push`. The hook invokes `python scripts/pre_push_check.py`; ensure the `python` on your PATH when Git runs hooks is the one with dev extras (e.g. activate `.venv` before pushing, or configure your shell so `python` resolves to `.venv/bin/python` in this repo).
5. **Quick sanity** — `git status` shows only intentional changes; you are on the intended branch (`git branch --show-current`).

**Why this matters:** CI on `main` / PRs runs **pytest** plus linters. Pushing without a local full `pytest` run has caused broken test suites to land on remote branches.

### Feature Work Checklist

Follow this order for every piece of work:

**Before starting:**
- [ ] **Branch sanity** — complete [Before starting work (branch sanity)](#before-starting-work-branch-sanity): correct branch name for this task/PR, `git fetch origin`, `git status -sb`, pull or rebase if behind remote
- [ ] Confirm with `git branch --show-current` (and `git branch -vv` if unsure about upstream)

**Implementation:**
- [ ] Write tests first (TDD), then implementation
- [ ] `black .` — code is formatted
- [ ] `ruff check .` — no lint warnings
- [ ] `mypy .` — no type errors
- [ ] `pytest` — all tests pass

**After implementation:**
- [ ] **Update `BACKLOG.md`** — mark the completed item ✅ DONE and check off all acceptance criteria
- [ ] **Update `:help`** — if any new keybindings were added, add them to `HelpScreen._HELP_TEXT` in `gtd_tui/app.py`
- [ ] **Update `CLAUDE.md`** — if new prerequisites, conventions, or key files were introduced
- [ ] **Update `CHANGELOG.md`** (or create it if absent) — add a bullet under `[Unreleased]` describing the change
- [ ] **Pre-push checklist** — complete [Pre-push checklist](#pre-push-checklist) before `git push`
- [ ] **Closure** — complete [Closing a body of work](#closing-a-body-of-work-reflection-and-follow-up) (reflection + suggestions; implement only what the user selects next) *(AI assistants: required end-of-task)*

### Closing a body of work (reflection and follow-up)

**Applies after every coherent body of work** (feature, bugfix, release prep, substantial docs — not trivial one-line answers).

Before treating the task as finished, the assistant should:

1. **Reflect briefly** — What went well? What was unclear, slow, or error-prone? (e.g. wrong branch, missing tests, scope creep.)
2. **Offer suggestions** — Give the user **a few concrete options** (typically 2–4) for how a similar request could go better next time (process, tests, docs, tooling, or code structure).
3. **Wait for selection** — **Do not implement** any suggestion in the same turn unless the user explicitly asked you to choose. End with an invitation: e.g. “Reply with **A**, **B**, **C**, or **none** (or describe another tweak), and I’ll implement the one you pick.”
4. **Next turn** — When the user names a choice, implement that suggestion (or acknowledge **none**).

This keeps improvements user-driven and avoids piling on unrequested changes.

### Release Process

When the user asks to make a release (e.g. "release v1.3.0" or "merge and tag"), follow these steps in order — do not skip any:

**Merging the release PR is not the end of the release.** After the PR lands on `main`, you must still **bump `pyproject.toml`**, **commit on `main`**, **tag `vX.Y.Z`**, and **push `main` + the tag** (steps 6–11). Until the tag is pushed, the versioned wheel/GitHub release does not ship. Do not treat the PR merge as “released” if those steps are pending.

**`gh pr merge --auto`:** Enable **auto-merge only after** step 2 (**`pre_push_check`**) has passed locally (or you have equivalent proof the full suite is green). Do not turn on auto-merge while the branch is untested — CI on the PR helps, but the checklist still expects a full `pytest` run before merge.

0. **Branch sanity** — You must be on the **release PR branch** (not `main`, not an unrelated `claude/…` branch). Run `git branch --show-current`, `git fetch origin`, and `git pull origin <branch>` so local matches the PR you intend to ship.
1. **Commit pending changes** on the current feature branch (if any uncommitted work exists)
2. **Pre-push checklist** — run `python scripts/pre_push_check.py` (or full `pytest` + linters per [Pre-push checklist](#pre-push-checklist)); do not push with failing tests
3. **Push the feature branch** to remote: `git push origin <branch>`
4. **Open a pull request** from the feature branch into `main` (skip if the release PR already exists — push updates the existing PR):
   - Use `gh pr create` with a title of the form `Release vX.Y.Z`
   - The PR body must include:
     - A one-paragraph summary of all changes being merged (synthesised from the commit log and `CHANGELOG.md [Unreleased]` section)
     - A bulleted list of every BACKLOG item completed (title only, not acceptance criteria)
     - The version being released
   - Example: `gh pr create --title "Release vX.Y.Z" --body "$(cat <<'EOF'\n...\nEOF\n)"`
5. **Merge the pull request** (only after step 2 is green): `gh pr merge <number> --merge --subject "Merge branch '<branch>' — vX.Y.Z"`
   (use `--merge` for a standard merge commit, preserving full history). If you use **`gh pr merge --auto`**, queue it **after** step 2 — never enable auto-merge before the full test suite has passed.
6. **Checkout main and pull**: `git checkout main && git pull origin main`
7. **Bump version** in `pyproject.toml`: `version = "X.Y.Z"`
8. **Commit the version bump**: `git commit -m "Bump version to X.Y.Z"`
9. **Create annotated tag**: `git tag -a vX.Y.Z HEAD -m "vX.Y.Z — <short summary of changes>"`
10. **Push main**: `git push origin main`
11. **Push tags**: `git push origin vX.Y.Z`
12. **Return to feature branch**: `git checkout <branch>`

GitHub Actions will automatically build the wheel and publish the release once the tag arrives.

**GitHub Release body:** The release workflow runs `scripts/reorder_changelog_section.py` on the tagged version’s `CHANGELOG.md` section. It orders subsections **Added** → **Changed** → **Fixed** (then Deprecated / Removed / Security), and sorts **Added** bullets with BACKLOG references and bold lead-ins first. Keep `[Unreleased]` entries in normal Keep a Changelog form; the script shapes what users see on the GitHub Release page.

---

## Key Files Reference

| File | Purpose |
|---|---|
| `README.md` | User-facing project description |
| `CLAUDE.md` | This file — AI assistant conventions |
| `AGENTS.md` | Short agent checklist (branch sanity, closure); points to CLAUDE.md |
| `BACKLOG.md` | Feature backlog with all story details |
| `CHANGELOG.md` | Release notes — update for every feature/fix |
| `scripts/reorder_changelog_section.py` | Release workflow: reorder changelog section for GitHub Release body |
| `pyproject.toml` | Package metadata and dependencies |
| `gtd_tui/__main__.py` | Entry point — keep thin |
| `gtd_tui/app.py` | Application state, event loop |
| `gtd_tui/config.py` | `config.toml` loading (`[backup]`, `[text]`, UI, timeout, etc.) |
| `gtd_tui/storage/rotating_backup.py` | Throttled rotating copies of `data.json` (or encrypted blob) |
| `gtd_tui/text/processing.py` | Spell check and capitalization for submitted text |
| `gtd_tui/ui.py` | All TUI rendering logic |
| `scripts/pre_push_check.py` | Full pytest + black + ruff + mypy before push (see Pre-push checklist) |

---

## Feature Backlog

See [BACKLOG.md](BACKLOG.md) for the full feature backlog.

## Notes for AI Assistants

- **Before editing:** Follow [Before starting work (branch sanity)](#before-starting-work-branch-sanity) — confirm `git branch --show-current`, `git fetch` + `git pull` on the correct branch (especially for release/PR-specific work). Do not assume the workspace is on the right branch.
- **After substantive work:** Follow [Closing a body of work](#closing-a-body-of-work-reflection-and-follow-up) — reflect, propose a few improvements, let the user pick one to implement next (do not auto-implement suggestions without their choice).
- BACKLOG-1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 30, 31, 32, 33, 53, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72 are **complete**. BACKLOG-23 is pending. The full project structure exists (`pyproject.toml`, `gtd_tui/`, `tests/`). When implementing new features, extend the existing codebase rather than scaffolding from scratch.
- **TDD is required.** Write tests before or alongside every feature. Do not implement logic without a corresponding test.
- Always run `pytest` (or suggest it) after adding/modifying Python source files.
- Prefer **minimal, focused changes** — avoid adding speculative abstractions before the design stabilizes.
- The UI should be modeled after the **Things iPhone app** — reference its information architecture (Inbox, Today, Upcoming, Anytime, Someday, Projects, Areas, Logbook) when making design decisions.
- **Vi keybindings are a first-class requirement.** All navigation and editing actions must be reachable via vi-style keys. Implement modal state (NORMAL/INSERT) from the start — do not retrofit it later.
- Storage format decisions (JSON vs SQLite) should be confirmed with the user before implementation, as they affect migration complexity later.
- Default data directory should follow XDG conventions (`~/.local/share/gtd_tui/` on Linux) using the `platformdirs` package.
- Follow the security rules in the Security section — especially: no network calls, atomic file writes, `600` permissions on the data file, no `shell=True`.
