from datetime import date, timedelta

from gtd_tui.gtd.operations import (
    add_task,
    complete_task,
    logbook_tasks,
    schedule_task,
    scheduled_tasks,
    today_tasks,
    unschedule_task,
)
from gtd_tui.gtd.task import Task


def test_add_task_to_empty_list():
    result = add_task([], "First task")
    assert len(result) == 1
    assert result[0].title == "First task"
    assert result[0].folder_id == "today"
    assert result[0].position == 0


def test_add_task_goes_to_top():
    tasks = add_task([], "Old task")
    tasks = add_task(tasks, "New task")
    ordered = today_tasks(tasks)
    assert ordered[0].title == "New task"
    assert ordered[1].title == "Old task"


def test_add_task_with_notes():
    tasks = add_task([], "Call mom", notes="Ask about Sunday")
    assert tasks[0].notes == "Ask about Sunday"


def test_add_task_bumps_existing_positions():
    tasks = add_task([], "Existing")
    assert tasks[0].position == 0
    tasks = add_task(tasks, "New")
    existing = next(t for t in tasks if t.title == "Existing")
    assert existing.position == 1


def test_today_tasks_returns_only_today():
    tasks = add_task([], "Today task")
    tasks[0].folder_id = "logbook"
    tasks = add_task(tasks, "Still today")
    result = today_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Still today"


def test_today_tasks_sorted_by_position():
    tasks: list[Task] = []
    tasks = add_task(tasks, "C")
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["A", "B", "C"]


def test_complete_task_moves_to_logbook():
    tasks = add_task([], "Buy groceries")
    task_id = tasks[0].id
    tasks = complete_task(tasks, task_id)
    assert today_tasks(tasks) == []
    lb = logbook_tasks(tasks)
    assert len(lb) == 1
    assert lb[0].title == "Buy groceries"
    assert lb[0].is_complete


def test_complete_task_unknown_id_is_noop():
    tasks = add_task([], "Task")
    result = complete_task(tasks, "nonexistent-id")
    assert len(today_tasks(result)) == 1


def test_logbook_tasks_most_recent_first():
    tasks: list[Task] = []
    tasks = add_task(tasks, "First done")
    tasks = add_task(tasks, "Second done")
    first_id = next(t.id for t in tasks if t.title == "First done")
    second_id = next(t.id for t in tasks if t.title == "Second done")
    tasks = complete_task(tasks, first_id)
    tasks = complete_task(tasks, second_id)
    lb = logbook_tasks(tasks)
    assert lb[0].title == "Second done"
    assert lb[1].title == "First done"


def test_multiple_adds_maintain_correct_order():
    tasks: list[Task] = []
    for title in ["one", "two", "three", "four"]:
        tasks = add_task(tasks, title)
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["four", "three", "two", "one"]


# ------------------------------------------------------------------ #
# Scheduling                                                           #
# ------------------------------------------------------------------ #

def test_schedule_task_sets_date():
    tasks = add_task([], "Dentist")
    future = date.today() + timedelta(days=5)
    tasks = schedule_task(tasks, tasks[0].id, future)
    assert tasks[0].scheduled_date == future


def test_today_tasks_excludes_future_scheduled():
    tasks = add_task([], "Snoozed")
    future = date.today() + timedelta(days=5)
    tasks = schedule_task(tasks, tasks[0].id, future)
    assert today_tasks(tasks) == []


def test_today_tasks_includes_past_scheduled():
    tasks = add_task([], "Overdue")
    past = date.today() - timedelta(days=1)
    tasks = schedule_task(tasks, tasks[0].id, past)
    assert len(today_tasks(tasks)) == 1


def test_today_tasks_includes_task_scheduled_for_today():
    tasks = add_task([], "Due today")
    tasks = schedule_task(tasks, tasks[0].id, date.today())
    assert len(today_tasks(tasks)) == 1


def test_today_tasks_as_of_parameter():
    tasks = add_task([], "Scheduled task")
    target = date(2026, 4, 1)
    tasks = schedule_task(tasks, tasks[0].id, target)
    assert today_tasks(tasks, as_of=date(2026, 3, 31)) == []
    assert len(today_tasks(tasks, as_of=date(2026, 4, 1))) == 1
    assert len(today_tasks(tasks, as_of=date(2026, 4, 2))) == 1


def test_unschedule_task_clears_date():
    tasks = add_task([], "Snoozed")
    future = date.today() + timedelta(days=3)
    tasks = schedule_task(tasks, tasks[0].id, future)
    tasks = unschedule_task(tasks, tasks[0].id)
    assert tasks[0].scheduled_date is None


def test_unschedule_returns_task_to_today():
    tasks = add_task([], "Snoozed")
    future = date.today() + timedelta(days=3)
    task_id = tasks[0].id
    tasks = schedule_task(tasks, task_id, future)
    assert today_tasks(tasks) == []
    tasks = unschedule_task(tasks, task_id)
    assert len(today_tasks(tasks)) == 1


def test_scheduled_tasks_returns_future_only():
    tasks = add_task([], "Future")
    future_id = tasks[0].id  # capture before next add_task prepends
    tasks = add_task(tasks, "Active")
    future = date.today() + timedelta(days=7)
    tasks = schedule_task(tasks, future_id, future)
    result = scheduled_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Future"


def test_scheduled_tasks_excludes_past():
    tasks = add_task([], "Overdue")
    past = date.today() - timedelta(days=1)
    tasks = schedule_task(tasks, tasks[0].id, past)
    assert scheduled_tasks(tasks) == []


def test_scheduled_tasks_sorted_by_date():
    tasks: list[Task] = []
    tasks = add_task(tasks, "Later")
    tasks = add_task(tasks, "Sooner")
    later_id = next(t.id for t in tasks if t.title == "Later")
    sooner_id = next(t.id for t in tasks if t.title == "Sooner")
    tasks = schedule_task(tasks, later_id, date.today() + timedelta(days=10))
    tasks = schedule_task(tasks, sooner_id, date.today() + timedelta(days=3))
    result = scheduled_tasks(tasks)
    assert result[0].title == "Sooner"
    assert result[1].title == "Later"


def test_schedule_unknown_id_is_noop():
    tasks = add_task([], "Task")
    future = date.today() + timedelta(days=1)
    result = schedule_task(tasks, "bad-id", future)
    assert today_tasks(result) == [tasks[0]]
