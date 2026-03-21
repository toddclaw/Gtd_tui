#!/usr/bin/env python3
"""Run the full quality gate before pushing (tests + format + lint + types).

Uses the same interpreter as this script, so activate your dev venv first::

    source .venv/bin/activate   # or: uv run python scripts/pre_push_check.py

Exit status is non-zero if any step fails.

After substantive work, see CLAUDE.md → Closing a body of work (reflection and follow-up).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(phase: str, argv: list[str]) -> None:
    print(f"\n=== {phase} ===", flush=True)
    subprocess.run(argv, cwd=ROOT, check=True)


def main() -> int:
    py = sys.executable
    try:
        _run("pytest (full suite)", [py, "-m", "pytest", "-q", "tests/"])
        _run("black --check", [py, "-m", "black", "--check", "."])
        _run("ruff check", [py, "-m", "ruff", "check", "."])
        _run("mypy", [py, "-m", "mypy", "gtd_tui/"])
    except subprocess.CalledProcessError:
        print(
            "\npre_push_check: FAILED — fix errors above before pushing.",
            file=sys.stderr,
        )
        return 1
    print("\n=== All pre-push checks passed ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
