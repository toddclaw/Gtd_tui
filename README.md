# Gtd_tui

A terminal user interface (TUI) for Getting Things Done (GTD), modeled after the Things iPhone app. Written in Python using the [Textual](https://github.com/Textualize/textual) framework.

---

## Overview

Gtd_tui gives you a keyboard-driven GTD workflow in your terminal. Tasks live in named folders and smart views, persist between sessions in a single JSON file, and are navigated entirely with vi-style keys. No mouse required.

The application follows the core GTD methodology: capture everything, process it into the right folder, schedule what needs a date, and review regularly. The folder structure mirrors the Things app: **Today**, **Upcoming**, **Waiting On**, **Someday**, user-created folders, and a **Logbook** for completed work.

---

## Features

### Views and Folders

| View / Folder | Description |
|---|---|
| **Inbox** | Quick-capture bucket; tasks never surface in Today automatically |
| **Today** | Smart view — shows tasks in the Today folder, plus tasks from any other folder whose scheduled date has arrived |
| **Upcoming** | Smart view — all tasks with a future scheduled date, sorted by date |
| **Waiting On** | Tasks blocked on someone else; optional follow-up date surfaces them in Today when the date arrives |
| **Someday** | Low-priority tasks with no date; never surface automatically |
| **User folders** | Create any number of named folders for projects or contexts |
| **Logbook** | Completed tasks, sorted by completion time (most recent first) |

### Task Management

- **Create tasks** with `o` (below selection) or `O` (above selection)
- **Title and notes** — each task has a one-line title and an optional multi-line notes field
- **Edit tasks** — press `Enter` to open a detail/edit view; edit title, date, notes, repeat, and recurring fields; `j`/`k` navigate between fields; changes save on close
- **Complete tasks** — press `x` or `Space`; completed tasks move to the Logbook with a timestamp
- **Delete tasks** — press `d` to delete the selected task
- **Schedule tasks** — press `s` to attach a date; supports `YYYY-MM-DD`, relative (`+3d`, `+1w`), and natural language (`tomorrow`, `next monday`, `in 2 weeks`, `someday`)
- **Reorder tasks** — `J` / `K` move the selected task down or up within its folder
- **Move tasks** — press `m` to move a task to any folder via the sidebar picker; `w` sends a task to Waiting On; `t` returns a Waiting On task to Today
- **Waiting On auto-scheduling** — new tasks added to Waiting On automatically get a scheduled date of today + 7 days; they surface in Today on that date with a `[W]` prefix
- **Visual mode bulk operations** — press `v` to enter VISUAL mode; extend the selection with `j`/`k`; then bulk-complete (`x`/`Space`), bulk-delete (`d`), bulk-schedule (`s`), bulk-move (`m`/`w`/`t`), or reorder the whole block (`J`/`K`); every bulk operation is a single undo step

### Keyboard Navigation (vi-style)

| Key | Action |
|---|---|
| `j` / `k` | Move cursor down / up |
| `H` / `M` / `L` | Jump to top / middle / bottom of list |
| `g g` | Jump to top of list |
| `G` | Jump to bottom of list |
| `Ctrl+d` / `Ctrl+u` | Half-page down / up |
| `h` / `l` | Focus sidebar / task list |
| `i` | Jump to Inbox |
| `1`–`9` | Jump to nth sidebar item |
| `J` / `K` | Move selected task down / up |
| `o` / `O` | Add task after / before selection |
| `Enter` | Open task detail / edit view |
| `x` / `Space` | Complete selected task |
| `d` | Delete selected task |
| `s` | Schedule selected task |
| `m` | Move task to a folder |
| `w` | Move task to Waiting On |
| `t` | Move task to Today (from Waiting On) |
| `v` | Enter VISUAL mode (bulk selection) |
| `u` | Undo last action |
| `Ctrl+R` | Redo last undone action |
| `/` | Global search |
| `n` / `N` | Next / previous search match |
| `q` | Quit |
| `:help` / `:h` | Show keybinding reference |

### Visual Mode (Bulk Operations)

Press `v` in NORMAL mode to enter VISUAL mode. Extend the selection with `j`/`k` — the anchor stays fixed while the cursor moves. Then apply any bulk operation:

| Key | Action |
|---|---|
| `x` / `Space` | Complete all selected tasks |
| `d` | Delete all selected tasks |
| `s` | Schedule all selected tasks (same date picker as normal `s`) |
| `m` | Move all selected tasks to a chosen folder |
| `w` | Move all selected tasks to Waiting On |
| `t` | Move all selected tasks to Today |
| `J` / `K` | Move the entire selected block down / up |
| `u` | Undo the bulk action (exits VISUAL mode) |
| `Esc` | Cancel selection, return to NORMAL mode |

Every bulk operation is recorded as a single undo step.

### Task Detail View

The detail view (opened with `Enter`) lets you edit all task fields in a single screen:

| Field | Notes |
|---|---|
| **Title** | One-line task name |
| **Date** | Scheduled date — same formats as `s` (`+7d`, `tomorrow`, `next monday`, etc.) |
| **Notes** | Multi-line free text |
| **Repeat** | Calendar-fixed schedule, e.g. `7 days`, `2 weeks` |
| **Recurring** | Completion-relative schedule, e.g. `1 day` (next instance spawns from completion date) |

Navigation within the detail view:

| Key | Action |
|---|---|
| `j` / `k` | Move to next / previous field (in COMMAND mode) |
| `i` / `a` | Enter INSERT mode at / after cursor |
| `o` / `O` | Edit from end / start on single-line fields; open new line below / above in notes |
| `Enter` | Confirm and advance to next field |
| `Esc` | Save and close |

### Folder Management (sidebar focused)

| Key | Action |
|---|---|
| `o` / `O` | Create new folder after / before selected |
| `N` | Create new folder at end |
| `r` | Rename selected folder |
| `d` | Delete selected folder (prompts if non-empty) |

### CLI Summary

Run `gtd-tui -s` (or `--summary`) to print today's tasks to stdout and exit — no TUI required. Useful for shell prompts and scripts:

```bash
gtd-tui -s
# Today (3):
#   - Review project proposal
#   - Send invoice
#     Don't forget to attach the time sheet
```

### Data and Privacy

- All data is stored locally in `~/.local/share/gtd_tui/data.json`
- Optional rotating backups: enable `[backup]` in `~/.config/gtd_tui/config.toml` — copies land in `~/.local/share/gtd_tui/backups` by default (encrypted databases stay encrypted)
- Optional spell check / capitalization: `[text]` section in the same config file (off by default)
- Writes are atomic (temp-file rename) with `600` permissions — owner read/write only
- No network access, no telemetry

---

## Installation

Requires Python 3.11+.

**Clipboard support** (for the `y` yank keybinding) requires a system clipboard tool:

| Platform | Install |
|---|---|
| Linux / X11 | `sudo apt-get install xclip` (or `xsel`) |
| Linux / Wayland | `sudo apt-get install wl-clipboard` |
| macOS / Windows | No extra install needed |

> **tmux users:** tmux may not inherit your `DISPLAY` variable. Add `set-environment -g DISPLAY ":1"` to `~/.tmux.conf` (replace `:1` with your actual display) and run `tmux source ~/.tmux.conf`.

**Recommended — using [uv](https://github.com/astral-sh/uv):**

```bash
git clone <repo-url>
cd Gtd_tui
uv sync
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
```

**Alternative — using pip:**

```bash
git clone <repo-url>
cd Gtd_tui
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**Set up pre-commit hooks (recommended for contributors):**

```bash
pre-commit install
# Optional but strongly recommended: run the full test suite before every push
# (commit hooks do not run pytest — only black, ruff, mypy, etc.)
pre-commit install --hook-type pre-push
```

The **pre-push** hook runs `python scripts/pre_push_check.py` (full `pytest`, `black --check`, `ruff check`, `mypy`). Use a shell where `python` is your dev environment (e.g. activate `.venv` before `git push`), or run the script manually:

```bash
python scripts/pre_push_check.py
```

## Running the Application

```bash
# Via the installed script
gtd-tui

# Or directly as a module
python -m gtd_tui
```

## Running the Tests

```bash
pytest
```

## Development

```bash
# Run all checks (matches CI and pre_push_check.py)
black --check .    # formatting
ruff check .       # linting
mypy gtd_tui/      # type checking
pytest             # tests — not run by commit hooks; run before every push

# Pre-commit at commit time: black, ruff, mypy, secrets, etc. — not pytest
pre-commit run --all-files

# One-shot gate before git push (recommended)
python scripts/pre_push_check.py
```

See **CLAUDE.md → Git Workflow** for contributor workflow: **Before starting work (branch sanity)** (right branch, up to date with remote), **Pre-push checklist** (full tests before push), **Protecting `main` on GitHub** (optional rulesets so changes go through PRs only), and **Closing a body of work** (reflection and optional follow-up improvements when working with an AI assistant).

**Releases:** Merging a release PR into `main` is not the end — you still need to bump `pyproject.toml`, create the `vX.Y.Z` tag, and push `main` + the tag (see **CLAUDE.md → Release Process**). If you use **`gh pr merge --auto`**, enable it only after **`python scripts/pre_push_check.py`** (or an equivalent full test run) has passed.
