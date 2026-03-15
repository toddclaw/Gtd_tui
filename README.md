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
| **Today** | Smart view — shows tasks in the Today folder, plus tasks from any other folder whose scheduled date has arrived |
| **Upcoming** | Smart view — all tasks with a future scheduled date, sorted by date |
| **Waiting On** | Tasks blocked on someone else; optional follow-up date surfaces them in Today when the date arrives |
| **Someday** | Low-priority tasks with no date; never surface automatically |
| **User folders** | Create any number of named folders for projects or contexts |
| **Logbook** | Completed tasks, sorted by completion time (most recent first) |

### Task Management

- **Create tasks** with `o` (below selection) or `O` (above selection)
- **Title and notes** — each task has a one-line title and an optional multi-line notes field
- **Edit tasks** — press `Enter` to open a detail/edit view for any task; changes save on close
- **Complete tasks** — press `x` or `Space`; completed tasks move to the Logbook with a timestamp
- **Schedule tasks** — press `s` to attach a date; supports `YYYY-MM-DD`, relative (`+3d`, `+1w`), and natural language (`tomorrow`, `next monday`, `in 2 weeks`)
- **Reorder tasks** — `J` / `K` move the selected task down or up within its folder
- **Move tasks** — press `m` to move a task to any folder via the sidebar picker; `w` sends a task to Waiting On; `t` returns a Waiting On task to Today

### Keyboard Navigation (vi-style)

| Key | Action |
|---|---|
| `j` / `k` | Move cursor down / up |
| `g g` | Jump to top of list |
| `G` | Jump to bottom of list |
| `h` / `l` | Focus sidebar / task list |
| `1`–`9` | Jump to nth sidebar item |
| `J` / `K` | Move selected task down / up |
| `o` / `O` | Add task after / before selection |
| `Enter` | Open task detail / edit view |
| `x` / `Space` | Complete selected task |
| `s` | Schedule selected task |
| `m` | Move task to a folder |
| `w` | Move task to Waiting On |
| `t` | Move task to Today (from Waiting On) |
| `u` | Undo last action |
| `Ctrl+R` | Redo last undone action |
| `q` | Quit |
| `:help` | Show keybinding reference |

### Folder Management (sidebar focused)

| Key | Action |
|---|---|
| `N` | Create new folder |
| `r` | Rename selected folder |
| `d` | Delete selected folder (prompts if non-empty) |

### Data and Privacy

- All data is stored locally in `~/.local/share/gtd_tui/data.json`
- Writes are atomic (temp-file rename) with `600` permissions — owner read/write only
- No network access, no telemetry

---

## Installation

Requires Python 3.11+.

```bash
# Clone the repository
git clone <repo-url>
cd Gtd_tui

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# Install the package and all dependencies (including dev tools)
pip install -e ".[dev]"
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
