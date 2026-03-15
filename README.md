# Gtd_tui
GTD with a TUI interface

This code is written in Python. It will implement core GTD features roughly aligned with how the Things iPhone app works except it will work as a TUI.

## Installation

Requires Python 3.11+.

```bash
# Clone the repository
git clone <repo-url>
cd Gtd_tui

# Create and activate a virtual environment
python -m venv .venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

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
