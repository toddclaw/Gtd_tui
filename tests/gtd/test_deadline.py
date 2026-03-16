"""Tests for deadline operations and display logic."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from gtd_tui.gtd.operations import (
    clear_deadline,
    deadline_status,
    set_deadline,
    weekly_review_tasks,
)
from gtd_tui.gtd.task import Task


# ---------------------------------------------------------------------------
# set_deadline / clear_deadline
# ---------------------------------------------------------------------------


def test_set_deadline_stores_date() -> None:
    task = Task(title="T")
    tasks = set_deadline([task], task.id, date(2026, 12, 1))
    assert tasks[0].deadline == date(2026, 12, 1)


def test_set_deadline_noop_for_unknown_id() -> None:
    task = Task(title="T")
    tasks = set_deadline([task], "nonexistent", date(2026, 12, 1))
    assert tasks[0].deadline is None


def test_clear_deadline_removes_date() -> None:
    task = Task(title="T", deadline=date(2026, 12, 1))
    tasks = clear_deadline([task], task.id)
    assert tasks[0].deadline is None


def test_clear_deadline_noop_when_already_none() -> None:
    task = Task(title="T")
    tasks = clear_deadline([task], task.id)
    assert tasks[0].deadline is None


# ---------------------------------------------------------------------------
# deadline_status
# ---------------------------------------------------------------------------


def test_deadline_status_none_when_no_deadline() -> None:
    task = Task(title="T")
    assert deadline_status(task, as_of=date(2026, 3, 16)) is None


def test_deadline_status_overdue_yesterday() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today - timedelta(days=1))
    result = deadline_status(task, as_of=today)
    assert result is not None
    text, status = result
    assert status == "overdue"
    assert "1d overdue" in text


def test_deadline_status_overdue_many_days() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today - timedelta(days=10))
    _, status = deadline_status(task, as_of=today)  # type: ignore[misc]
    assert status == "overdue"


def test_deadline_status_due_today() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today)
    text, status = deadline_status(task, as_of=today)  # type: ignore[misc]
    assert status == "soon"
    assert "today" in text


def test_deadline_status_due_in_1_day() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today + timedelta(days=1))
    text, status = deadline_status(task, as_of=today)  # type: ignore[misc]
    assert status == "soon"
    assert "1d left" in text


def test_deadline_status_due_in_3_days() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today + timedelta(days=3))
    _, status = deadline_status(task, as_of=today)  # type: ignore[misc]
    assert status == "soon"


def test_deadline_status_due_in_4_days() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today + timedelta(days=4))
    text, status = deadline_status(task, as_of=today)  # type: ignore[misc]
    assert status == "ok"
    assert "4d left" in text


def test_deadline_status_text_contains_formatted_date() -> None:
    today = date(2026, 3, 16)
    task = Task(title="T", deadline=today + timedelta(days=5))
    text, _ = deadline_status(task, as_of=today)  # type: ignore[misc]
    # format_date renders something like "Mar 21 Sun"
    assert "Mar" in text


# ---------------------------------------------------------------------------
# weekly_review_tasks
# ---------------------------------------------------------------------------


def _completed_task(title: str, days_ago: int, as_of: date) -> Task:
    t = Task(title=title, folder_id="logbook")
    t.completed_at = datetime.combine(as_of - timedelta(days=days_ago), datetime.min.time())
    return t


def test_weekly_review_returns_tasks_completed_in_last_7_days() -> None:
    today = date(2026, 3, 16)
    recent = _completed_task("Recent", 3, today)
    old = _completed_task("Old", 10, today)
    result = weekly_review_tasks([recent, old], as_of=today)
    assert len(result) == 1
    assert result[0].title == "Recent"


def test_weekly_review_includes_task_completed_exactly_7_days_ago() -> None:
    today = date(2026, 3, 16)
    boundary = _completed_task("Boundary", 7, today)
    result = weekly_review_tasks([boundary], as_of=today)
    assert len(result) == 1


def test_weekly_review_excludes_deleted_tasks() -> None:
    today = date(2026, 3, 16)
    deleted = _completed_task("Deleted", 1, today)
    deleted.is_deleted = True
    result = weekly_review_tasks([deleted], as_of=today)
    assert result == []


def test_weekly_review_excludes_non_logbook_tasks() -> None:
    today = date(2026, 3, 16)
    active = Task(title="Active", folder_id="today")
    result = weekly_review_tasks([active], as_of=today)
    assert result == []


def test_weekly_review_empty_when_no_completions() -> None:
    result = weekly_review_tasks([], as_of=date(2026, 3, 16))
    assert result == []


def test_weekly_review_sorted_most_recent_first() -> None:
    today = date(2026, 3, 16)
    t1 = _completed_task("A", 1, today)
    t2 = _completed_task("B", 3, today)
    t3 = _completed_task("C", 5, today)
    result = weekly_review_tasks([t3, t1, t2], as_of=today)
    assert [t.title for t in result] == ["A", "B", "C"]
