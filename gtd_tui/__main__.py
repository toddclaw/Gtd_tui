from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gtd_tui.app import GtdApp
from gtd_tui.gtd.dates import format_date
from gtd_tui.gtd.operations import today_tasks, upcoming_tasks
from gtd_tui.storage.file import load_tasks


def _print_summary(data_file: Path | None = None) -> None:
    """Print a plain-text summary of today's tasks to stdout and exit."""
    tasks = load_tasks(data_file)
    today = today_tasks(tasks)
    upcoming = upcoming_tasks(tasks)

    print(f"Today ({len(today)}):")
    for t in today:
        print(f"  - {t.title}")
        if t.notes:
            print(f"    {t.notes}")

    if upcoming:
        print(f"\nUpcoming ({len(upcoming)}):")
        for t in upcoming:
            date_str = format_date(t.scheduled_date) if t.scheduled_date else ""
            print(f"  - {t.title}  {date_str}")
            if t.notes:
                print(f"    {t.notes}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="gtd_tui", description="GTD TUI")
    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Print a summary of today's tasks and exit (no TUI)",
    )
    args = parser.parse_args()

    if args.summary:
        _print_summary()
        sys.exit(0)

    GtdApp().run()


if __name__ == "__main__":
    main()
