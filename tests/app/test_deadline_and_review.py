"""Integration tests for BACKLOG-19 (Weekly Review) and BACKLOG-20 (Deadline)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from textual.widgets import Label, ListItem, ListView

from gtd_tui.app import GtdApp, TaskDetailScreen, WeeklyReviewScreen
from gtd_tui.gtd.operations import add_task, complete_task, set_deadline
from gtd_tui.storage.file import save_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app_with_tasks(tmp_path: Path, *titles: str) -> GtdApp:
    data_file = tmp_path / "data.json"
    tasks: list = []
    for title in reversed(titles):
        tasks = add_task(tasks, title)
    save_data(tasks, [], data_file=data_file)
    return GtdApp(data_file=data_file)


def _app_with_deadline(tmp_path: Path, title: str, deadline: date) -> GtdApp:
    data_file = tmp_path / "data.json"
    tasks = add_task([], title)
    tasks = set_deadline(tasks, tasks[0].id, deadline)
    save_data(tasks, [], data_file=data_file)
    return GtdApp(data_file=data_file)


# ---------------------------------------------------------------------------
# BACKLOG-19: Weekly Review
# ---------------------------------------------------------------------------


async def test_W_opens_weekly_review_screen(tmp_path: Path) -> None:
    async with _app_with_tasks(tmp_path, "T").run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WeeklyReviewScreen)


async def test_escape_closes_weekly_review(tmp_path: Path) -> None:
    async with _app_with_tasks(tmp_path, "T").run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WeeklyReviewScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(pilot.app.screen, WeeklyReviewScreen)


async def test_weekly_review_empty_message_when_no_completions(tmp_path: Path) -> None:
    from textual.widgets import Static
    async with _app_with_tasks(tmp_path, "T").run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        content = str(pilot.app.screen.query_one(Static).render())
        assert "No tasks" in content


async def test_weekly_review_shows_recently_completed_task(tmp_path: Path) -> None:
    from textual.widgets import Static
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Buy milk")
    tasks = complete_task(tasks, tasks[0].id)
    save_data(tasks, [], data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        content = str(pilot.app.screen.query_one(Static).render())
        assert "Buy milk" in content


async def test_weekly_review_does_not_show_old_completions(tmp_path: Path) -> None:
    from textual.widgets import Static
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Ancient task")
    task = tasks[0]
    task.folder_id = "logbook"
    task.completed_at = datetime.now() - timedelta(days=10)
    save_data(tasks, [], data_file=data_file)
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        content = str(pilot.app.screen.query_one(Static).render())
        assert "Ancient task" not in content


async def test_W_works_from_sidebar_focus(tmp_path: Path) -> None:
    async with _app_with_tasks(tmp_path, "T").run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")   # focus sidebar
        await pilot.pause()
        await pilot.press("W")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WeeklyReviewScreen)


# ---------------------------------------------------------------------------
# BACKLOG-20: Deadline field
# ---------------------------------------------------------------------------


async def test_deadline_label_overdue_shown_in_task_list(tmp_path: Path) -> None:
    yesterday = date.today() - timedelta(days=1)
    async with _app_with_deadline(tmp_path, "Overdue task", yesterday).run_test() as pilot:
        await pilot.pause()
        task_list = pilot.app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        assert any("overdue" in lbl for lbl in labels)


async def test_deadline_label_soon_shown_in_task_list(tmp_path: Path) -> None:
    soon = date.today() + timedelta(days=2)
    async with _app_with_deadline(tmp_path, "Due soon", soon).run_test() as pilot:
        await pilot.pause()
        task_list = pilot.app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        assert any("left" in lbl or "today" in lbl for lbl in labels)


async def test_no_deadline_label_when_unset(tmp_path: Path) -> None:
    async with _app_with_tasks(tmp_path, "No deadline").run_test() as pilot:
        await pilot.pause()
        task_list = pilot.app.query_one("#task-list", ListView)
        labels = [str(item.query_one(Label).render()) for item in task_list.children]
        assert not any("overdue" in lbl or "left" in lbl for lbl in labels)


async def test_set_deadline_via_detail_screen(tmp_path: Path) -> None:
    async with _app_with_tasks(tmp_path, "T").run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")   # open detail
        await pilot.pause()
        assert isinstance(pilot.app.screen, TaskDetailScreen)

        await pilot.press("enter")   # title → date
        await pilot.pause()
        await pilot.press("enter")   # date → deadline
        await pilot.pause()

        # Type '+7d' in the Deadline field
        await pilot.press("i")
        await pilot.press("+", "7", "d")
        await pilot.press("escape")  # insert → command
        await pilot.pause()
        await pilot.press("escape")  # save and close
        await pilot.pause()
        assert not isinstance(pilot.app.screen, TaskDetailScreen)

        task = next(t for t in pilot.app._all_tasks if t.folder_id != "logbook")
        assert task.deadline == date.today() + timedelta(days=7)


async def test_clear_deadline_via_detail_screen(tmp_path: Path) -> None:
    deadline = date.today() + timedelta(days=5)
    async with _app_with_deadline(tmp_path, "T", deadline).run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")   # open detail
        await pilot.pause()

        await pilot.press("enter")   # title → date (no scheduled_date, enters empty)
        await pilot.pause()
        await pilot.press("enter")   # date → deadline
        await pilot.pause()

        # Deadline field has value "2026-…"; enter INSERT, select-all, delete, Esc
        await pilot.press("i")       # COMMAND → INSERT at cursor
        await pilot.pause()
        # Use ctrl+a equivalent: 0 (go to start) then D (delete to end) in COMMAND
        await pilot.press("escape")  # back to COMMAND
        await pilot.press("0")       # move to start
        await pilot.press("D")       # delete to end of line → empty string
        await pilot.pause()
        await pilot.press("escape")  # save and close
        await pilot.pause()
        assert not isinstance(pilot.app.screen, TaskDetailScreen)

        task = next(t for t in pilot.app._all_tasks if t.folder_id != "logbook")
        assert task.deadline is None
