"""Tests for __main__ CLI entry point."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path


def test_summary_flag_prints_today_tasks(tmp_path: Path, capsys) -> None:
    """--summary prints today's tasks to stdout and exits with code 0."""
    from gtd_tui.__main__ import _print_summary
    from gtd_tui.gtd.operations import add_task
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Morning run")
    save_data(tasks, [], data_file=data_file)

    _print_summary(data_file=data_file)

    captured = capsys.readouterr()
    assert "Morning run" in captured.out
    assert "Today" in captured.out


def test_summary_empty_list(tmp_path: Path, capsys) -> None:
    """--summary with no tasks prints Today (0) and no task lines."""
    from gtd_tui.__main__ import _print_summary
    from gtd_tui.storage.file import save_data

    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    _print_summary(data_file=data_file)

    captured = capsys.readouterr()
    assert "Today" in captured.out
    assert "Morning run" not in captured.out
