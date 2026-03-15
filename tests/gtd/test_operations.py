from datetime import date, timedelta

from gtd_tui.gtd.operations import (
    add_task,
    add_waiting_on_task,
    complete_task,
    insert_task_after,
    insert_task_before,
    logbook_tasks,
    move_task_down,
    move_task_up,
    move_to_today,
    move_to_waiting_on,
    schedule_task,
    scheduled_tasks,
    surfaced_waiting_on_tasks,
    today_tasks,
    unschedule_task,
    waiting_on_tasks,
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


# ------------------------------------------------------------------ #
# Reordering                                                           #
# ------------------------------------------------------------------ #

def test_move_task_up_swaps_with_previous():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["A", "B"]

    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = move_task_up(tasks, b_id)
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["B", "A"]


def test_move_task_up_at_top_is_noop():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    a_id = next(t.id for t in tasks if t.title == "A")
    result = move_task_up(tasks, a_id)
    assert [t.title for t in today_tasks(result)] == ["A", "B"]


def test_move_task_up_unknown_id_is_noop():
    tasks = add_task([], "Only")
    result = move_task_up(tasks, "bad-id")
    assert today_tasks(result) == [tasks[0]]


def test_move_task_down_swaps_with_next():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["A", "B"]

    a_id = next(t.id for t in tasks if t.title == "A")
    tasks = move_task_down(tasks, a_id)
    ordered = today_tasks(tasks)
    assert [t.title for t in ordered] == ["B", "A"]


def test_move_task_down_at_bottom_is_noop():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    b_id = next(t.id for t in tasks if t.title == "B")
    result = move_task_down(tasks, b_id)
    assert [t.title for t in today_tasks(result)] == ["A", "B"]


def test_move_task_down_unknown_id_is_noop():
    tasks = add_task([], "Only")
    result = move_task_down(tasks, "bad-id")
    assert today_tasks(result) == [tasks[0]]


# ------------------------------------------------------------------ #
# Positional insertion                                                 #
# ------------------------------------------------------------------ #

def test_insert_task_after_places_below_anchor():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    # order: A B
    a_id = next(t.id for t in tasks if t.title == "A")
    tasks = insert_task_after(tasks, a_id, "new")
    assert [t.title for t in today_tasks(tasks)] == ["A", "new", "B"]


def test_insert_task_after_at_last_position():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = insert_task_after(tasks, b_id, "new")
    assert [t.title for t in today_tasks(tasks)] == ["A", "B", "new"]


def test_insert_task_before_places_above_anchor():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    # order: A B
    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = insert_task_before(tasks, b_id, "new")
    assert [t.title for t in today_tasks(tasks)] == ["A", "new", "B"]


def test_insert_task_before_at_first_position():
    tasks: list[Task] = []
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")
    a_id = next(t.id for t in tasks if t.title == "A")
    tasks = insert_task_before(tasks, a_id, "new")
    assert [t.title for t in today_tasks(tasks)] == ["new", "A", "B"]


def test_insert_task_after_uses_provided_task_id():
    tasks = add_task([], "A")
    a_id = tasks[0].id
    tasks = insert_task_after(tasks, a_id, "new", task_id="fixed-id")
    new_task = next(t for t in tasks if t.title == "new")
    assert new_task.id == "fixed-id"


def test_insert_task_before_uses_provided_task_id():
    tasks = add_task([], "A")
    a_id = tasks[0].id
    tasks = insert_task_before(tasks, a_id, "new", task_id="fixed-id")
    new_task = next(t for t in tasks if t.title == "new")
    assert new_task.id == "fixed-id"


def test_add_task_uses_provided_task_id():
    tasks = add_task([], "A", task_id="fixed-id")
    assert tasks[0].id == "fixed-id"


def test_move_preserves_other_tasks():
    tasks: list[Task] = []
    for title in ["C", "B", "A"]:
        tasks = add_task(tasks, title)
    # order: A B C
    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = move_task_up(tasks, b_id)
    assert [t.title for t in today_tasks(tasks)] == ["B", "A", "C"]


# ------------------------------------------------------------------ #
# Waiting On folder                                                    #
# ------------------------------------------------------------------ #

def test_add_waiting_on_task_creates_in_correct_folder():
    tasks = add_waiting_on_task([], "Call Alice")
    assert len(tasks) == 1
    assert tasks[0].title == "Call Alice"
    assert tasks[0].folder_id == "waiting_on"


def test_add_waiting_on_task_does_not_appear_in_today():
    tasks = add_waiting_on_task([], "Waiting task")
    assert today_tasks(tasks) == []


def test_waiting_on_tasks_returns_unsurfaced():
    tasks = add_waiting_on_task([], "No date task")
    tasks = add_waiting_on_task(tasks, "Future date task")
    future_id = next(t.id for t in tasks if t.title == "Future date task")
    tasks = schedule_task(tasks, future_id, date.today() + timedelta(days=5))
    result = waiting_on_tasks(tasks)
    assert len(result) == 2
    assert all(t.folder_id == "waiting_on" for t in result)


def test_waiting_on_tasks_excludes_surfaced():
    tasks = add_waiting_on_task([], "Surfaced task")
    tasks = schedule_task(tasks, tasks[0].id, date.today() - timedelta(days=1))
    assert waiting_on_tasks(tasks) == []


def test_waiting_on_tasks_no_date_sorts_first():
    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "Has date")
    tasks = add_waiting_on_task(tasks, "No date")
    has_date_id = next(t.id for t in tasks if t.title == "Has date")
    tasks = schedule_task(tasks, has_date_id, date.today() + timedelta(days=3))
    result = waiting_on_tasks(tasks)
    assert result[0].title == "No date"
    assert result[1].title == "Has date"


def test_surfaced_waiting_on_tasks_returns_due():
    tasks = add_waiting_on_task([], "Due task")
    tasks = schedule_task(tasks, tasks[0].id, date.today() - timedelta(days=1))
    result = surfaced_waiting_on_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Due task"


def test_surfaced_waiting_on_tasks_excludes_future():
    tasks = add_waiting_on_task([], "Future task")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=1))
    assert surfaced_waiting_on_tasks(tasks) == []


def test_surfaced_waiting_on_tasks_excludes_no_date():
    tasks = add_waiting_on_task([], "No date task")
    assert surfaced_waiting_on_tasks(tasks) == []


def test_surfaced_waiting_on_tasks_as_of_parameter():
    tasks = add_waiting_on_task([], "Task")
    target = date(2026, 4, 1)
    tasks = schedule_task(tasks, tasks[0].id, target)
    assert surfaced_waiting_on_tasks(tasks, as_of=date(2026, 3, 31)) == []
    assert len(surfaced_waiting_on_tasks(tasks, as_of=date(2026, 4, 1))) == 1


def test_move_to_waiting_on_changes_folder():
    tasks = add_task([], "Buy milk")
    task_id = tasks[0].id
    tasks = move_to_waiting_on(tasks, task_id)
    assert tasks[0].folder_id == "waiting_on"
    assert today_tasks(tasks) == []


def test_move_to_waiting_on_unknown_id_is_noop():
    tasks = add_task([], "Task")
    result = move_to_waiting_on(tasks, "bad-id")
    assert len(today_tasks(result)) == 1


def test_move_to_today_changes_folder():
    tasks = add_waiting_on_task([], "WO task")
    task_id = tasks[0].id
    tasks = move_to_today(tasks, task_id)
    assert tasks[0].folder_id == "today"
    assert len(today_tasks(tasks)) == 1


def test_move_to_today_clears_scheduled_date():
    tasks = add_waiting_on_task([], "WO task")
    task_id = tasks[0].id
    tasks = schedule_task(tasks, task_id, date.today() + timedelta(days=5))
    tasks = move_to_today(tasks, task_id)
    assert tasks[0].scheduled_date is None


def test_move_to_today_inserts_at_top():
    tasks = add_task([], "Existing Today task")
    tasks = add_waiting_on_task(tasks, "WO task")
    wo_id = next(t.id for t in tasks if t.folder_id == "waiting_on")
    tasks = move_to_today(tasks, wo_id)
    ordered = today_tasks(tasks)
    assert ordered[0].title == "WO task"
    assert ordered[1].title == "Existing Today task"


def test_move_to_today_unknown_id_is_noop():
    tasks = add_waiting_on_task([], "WO task")
    result = move_to_today(tasks, "bad-id")
    assert waiting_on_tasks(result) == [tasks[0]]
