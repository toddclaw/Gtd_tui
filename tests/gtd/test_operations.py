from datetime import date, timedelta

from gtd_tui.gtd.operations import (
    InvalidRepeatError,
    add_task,
    add_task_to_folder,
    add_waiting_on_task,
    complete_task,
    delete_task,
    edit_task,
    folder_tasks,
    insert_folder_task_after,
    insert_folder_task_before,
    insert_task_after,
    insert_task_before,
    insert_waiting_on_task_after,
    insert_waiting_on_task_before,
    logbook_tasks,
    move_block_down,
    move_block_up,
    move_task_down,
    move_task_up,
    move_to_today,
    move_to_waiting_on,
    parse_repeat_input,
    purge_logbook_task,
    schedule_task,
    scheduled_tasks,
    search_tasks,
    set_recur_rule,
    set_repeat_rule,
    someday_tasks,
    spawn_repeating_tasks,
    surfaced_waiting_on_tasks,
    today_tasks,
    unschedule_task,
    upcoming_tasks,
    waiting_on_tasks,
)
from gtd_tui.gtd.task import RecurRule, RepeatRule, Task


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


def test_today_tasks_excludes_logbook():
    tasks = add_task([], "Today task")
    tasks[0].folder_id = "logbook"
    tasks = add_task(tasks, "Still today")
    result = today_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Still today"


def test_today_tasks_excludes_someday():
    tasks = add_task([], "Someday task")
    tasks[0].folder_id = "someday"
    tasks = add_task(tasks, "Today task")
    result = today_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Today task"


def test_today_tasks_excludes_undated_waiting_on():
    """Undated WO tasks do not surface in Today (Things behaviour)."""
    tasks = add_waiting_on_task([], "Waiting without date")
    assert today_tasks(tasks) == []


def test_today_tasks_includes_dated_waiting_on():
    """WO tasks scheduled for today/overdue DO surface in Today."""
    tasks = add_waiting_on_task([], "WO due today")
    tasks = schedule_task(tasks, tasks[0].id, date.today())
    assert len(today_tasks(tasks)) == 1


def test_today_tasks_excludes_undated_custom_folder():
    """Undated tasks in custom folders do not appear in Today."""
    tasks = add_task_to_folder([], "custom-folder", "Custom task")
    assert today_tasks(tasks) == []


def test_today_tasks_includes_dated_custom_folder():
    """Custom-folder tasks scheduled for today/overdue DO appear in Today."""
    tasks = add_task_to_folder([], "custom-folder", "Custom task")
    tasks = schedule_task(tasks, tasks[0].id, date.today())
    assert len(today_tasks(tasks)) == 1


def test_today_tasks_today_folder_sorts_first():
    """'today'-folder tasks appear before tasks from other folders."""
    tasks = add_waiting_on_task([], "WO due today")
    tasks = schedule_task(tasks, tasks[0].id, date.today())
    tasks = add_task(tasks, "Today task")
    ordered = today_tasks(tasks)
    assert ordered[0].title == "Today task"
    assert ordered[1].title == "WO due today"


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


# ------------------------------------------------------------------ #
# delete_task                                                          #
# ------------------------------------------------------------------ #


def test_delete_task_moves_to_logbook():
    tasks = add_task([], "Unwanted task")
    task_id = tasks[0].id
    tasks = delete_task(tasks, task_id)
    assert today_tasks(tasks) == []
    lb = logbook_tasks(tasks)
    assert len(lb) == 1
    assert lb[0].title == "Unwanted task"


def test_delete_task_sets_is_deleted():
    tasks = add_task([], "Gone")
    task_id = tasks[0].id
    tasks = delete_task(tasks, task_id)
    assert logbook_tasks(tasks)[0].is_deleted is True


def test_delete_task_is_not_complete():
    tasks = add_task([], "Gone")
    task_id = tasks[0].id
    tasks = delete_task(tasks, task_id)
    assert logbook_tasks(tasks)[0].is_complete is False


def test_delete_task_unknown_id_is_noop():
    tasks = add_task([], "Task")
    result = delete_task(tasks, "nonexistent-id")
    assert len(today_tasks(result)) == 1


# ------------------------------------------------------------------ #
# purge_logbook_task                                                   #
# ------------------------------------------------------------------ #


def test_purge_logbook_task_removes_entry():
    tasks = add_task([], "Done task")
    task_id = tasks[0].id
    tasks = delete_task(tasks, task_id)  # moves to logbook
    tasks = purge_logbook_task(tasks, task_id)
    assert logbook_tasks(tasks) == []


def test_purge_logbook_task_does_not_remove_live_task():
    tasks = add_task([], "Active task")
    task_id = tasks[0].id
    result = purge_logbook_task(tasks, task_id)
    assert len(today_tasks(result)) == 1


def test_purge_logbook_task_unknown_id_is_noop():
    tasks = add_task([], "Task")
    task_id = tasks[0].id
    tasks = delete_task(tasks, task_id)
    result = purge_logbook_task(tasks, "nonexistent-id")
    assert len(logbook_tasks(result)) == 1


# ------------------------------------------------------------------ #
# edit_task                                                            #
# ------------------------------------------------------------------ #


def test_edit_task_updates_title():
    tasks = add_task([], "Old title")
    task_id = tasks[0].id
    tasks = edit_task(tasks, task_id, "New title")
    assert tasks[0].title == "New title"


def test_edit_task_updates_notes():
    tasks = add_task([], "Task", notes="old notes")
    task_id = tasks[0].id
    tasks = edit_task(tasks, task_id, "Task", notes="new notes")
    assert tasks[0].notes == "new notes"


def test_edit_task_clears_notes_when_empty():
    tasks = add_task([], "Task", notes="some notes")
    task_id = tasks[0].id
    tasks = edit_task(tasks, task_id, "Task", notes="")
    assert tasks[0].notes == ""


def test_edit_task_unknown_id_is_noop():
    tasks = add_task([], "Task")
    result = edit_task(tasks, "bad-id", "New title")
    assert result[0].title == "Task"


def test_edit_task_preserves_other_fields():
    from datetime import date as dt

    tasks = add_task([], "Task")
    task_id = tasks[0].id
    tasks[0].scheduled_date = dt(2026, 5, 1)
    tasks[0].folder_id = "someday"
    tasks[0].position = 7
    tasks = edit_task(tasks, task_id, "Edited", notes="note")
    t = tasks[0]
    assert t.scheduled_date == dt(2026, 5, 1)
    assert t.folder_id == "someday"
    assert t.position == 7


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


def test_move_task_down_skips_snoozed_tasks():
    """J should swap with the next VISIBLE task, not a snoozed one in between."""
    tasks = add_task([], "A")
    tasks = add_task(tasks, "B")  # B pos=0, A pos=1 after add_task prepend
    # Snooze B so today_tasks returns only A
    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = schedule_task(tasks, b_id, date.today() + timedelta(days=5))
    tasks = add_task(tasks, "C")  # C pos=0, B pos=1, A pos=2
    # Visible order: C(pos=0), A(pos=2)   [B is snoozed]
    assert [t.title for t in today_tasks(tasks)] == ["C", "A"]
    c_id = next(t.id for t in tasks if t.title == "C")
    tasks = move_task_down(tasks, c_id)
    # C should now be after A — one press is enough
    assert [t.title for t in today_tasks(tasks)] == ["A", "C"]


def test_move_task_up_skips_snoozed_tasks():
    """K should swap with the previous VISIBLE task, not a snoozed one in between."""
    tasks: list[Task] = []
    tasks = add_task(tasks, "C")
    tasks = add_task(tasks, "B")
    tasks = add_task(tasks, "A")  # visible order: A, B, C
    b_id = next(t.id for t in tasks if t.title == "B")
    tasks = schedule_task(tasks, b_id, date.today() + timedelta(days=5))
    # Visible order: A, C   [B snoozed]
    assert [t.title for t in today_tasks(tasks)] == ["A", "C"]
    c_id = next(t.id for t in tasks if t.title == "C")
    tasks = move_task_up(tasks, c_id)
    assert [t.title for t in today_tasks(tasks)] == ["C", "A"]


def test_move_task_up_in_custom_folder():
    tasks = add_task_to_folder([], "projects", "First")
    tasks = add_task_to_folder(tasks, "projects", "Second")
    # order: First, Second (by position 0, 1)
    second_id = next(t.id for t in tasks if t.title == "Second")
    tasks = move_task_up(tasks, second_id)
    ordered = folder_tasks(tasks, "projects")
    assert [t.title for t in ordered] == ["Second", "First"]


def test_move_task_down_in_custom_folder():
    tasks = add_task_to_folder([], "projects", "First")
    tasks = add_task_to_folder(tasks, "projects", "Second")
    first_id = next(t.id for t in tasks if t.title == "First")
    tasks = move_task_down(tasks, first_id)
    ordered = folder_tasks(tasks, "projects")
    assert [t.title for t in ordered] == ["Second", "First"]


def test_move_does_not_affect_other_folders():
    tasks = add_task_to_folder([], "projects", "P1")
    tasks = add_task_to_folder(tasks, "projects", "P2")
    tasks = add_task(tasks, "T1")
    p2_id = next(t.id for t in tasks if t.title == "P2")
    tasks = move_task_up(tasks, p2_id)
    # projects reordered, today unaffected
    assert [t.title for t in folder_tasks(tasks, "projects")] == ["P2", "P1"]
    assert today_tasks(tasks)[0].title == "T1"


# ------------------------------------------------------------------ #
# Waiting On folder                                                    #
# ------------------------------------------------------------------ #


def test_add_waiting_on_task_creates_in_correct_folder():
    tasks = add_waiting_on_task([], "Call Alice")
    assert len(tasks) == 1
    assert tasks[0].title == "Call Alice"
    assert tasks[0].folder_id == "waiting_on"


def test_add_waiting_on_task_does_not_appear_in_today():
    # Undated WO tasks do not surface in Today — they need a date to show up.
    tasks = add_waiting_on_task([], "Waiting task")
    assert today_tasks(tasks) == []


def test_waiting_on_tasks_returns_all():
    """Waiting On view shows all WO tasks regardless of date."""
    tasks = add_waiting_on_task([], "No date task")
    tasks = add_waiting_on_task(tasks, "Future date task")
    tasks = add_waiting_on_task(tasks, "Past date task")
    future_id = next(t.id for t in tasks if t.title == "Future date task")
    past_id = next(t.id for t in tasks if t.title == "Past date task")
    tasks = schedule_task(tasks, future_id, date.today() + timedelta(days=5))
    tasks = schedule_task(tasks, past_id, date.today() - timedelta(days=1))
    result = waiting_on_tasks(tasks)
    assert len(result) == 3
    assert all(t.folder_id == "waiting_on" for t in result)


def test_waiting_on_tasks_sorted_by_position():
    """Waiting On view sorts by position, not by date (enables J/K reordering)."""
    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "First added")
    tasks = add_waiting_on_task(tasks, "Second added")
    tasks = add_waiting_on_task(tasks, "Third added")
    # Assign a past date to "Second added" — should still appear second (position order).
    second_id = next(t.id for t in tasks if t.title == "Second added")
    tasks = schedule_task(tasks, second_id, date.today() - timedelta(days=1))
    result = waiting_on_tasks(tasks)
    assert result[0].title == "First added"
    assert result[1].title == "Second added"
    assert result[2].title == "Third added"


def test_add_waiting_on_task_accepts_explicit_task_id():
    tasks = add_waiting_on_task([], "Call Alice", task_id="fixed-id")
    assert tasks[0].id == "fixed-id"


def test_add_waiting_on_task_assigns_sequential_positions():
    """Each new WO task gets the next position after existing WO tasks."""
    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "First")
    tasks = add_waiting_on_task(tasks, "Second")
    tasks = add_waiting_on_task(tasks, "Third")
    wo = waiting_on_tasks(tasks)
    assert [t.title for t in wo] == ["First", "Second", "Third"]
    assert wo[0].position < wo[1].position < wo[2].position


def test_move_to_waiting_on_inserts_at_top():
    """A task moved to Waiting On is inserted at position 0 (top of the list)."""
    tasks = add_waiting_on_task([], "Already here")
    tasks = add_task(tasks, "Moving over")
    moving_id = next(t.id for t in tasks if t.title == "Moving over")
    tasks = move_to_waiting_on(tasks, moving_id)
    wo = waiting_on_tasks(tasks)
    assert wo[0].title == "Moving over"
    assert wo[1].title == "Already here"


def test_move_task_up_in_waiting_on():
    """J/K reordering works in Waiting On folder."""
    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "Alpha")
    tasks = add_waiting_on_task(tasks, "Beta")
    beta_id = next(t.id for t in tasks if t.title == "Beta")
    tasks = move_task_up(tasks, beta_id)
    result = waiting_on_tasks(tasks)
    assert result[0].title == "Beta"
    assert result[1].title == "Alpha"


def test_move_task_down_in_waiting_on():
    """J/K reordering works in Waiting On folder."""
    tasks: list[Task] = []
    tasks = add_waiting_on_task(tasks, "Alpha")
    tasks = add_waiting_on_task(tasks, "Beta")
    alpha_id = next(t.id for t in tasks if t.title == "Alpha")
    tasks = move_task_down(tasks, alpha_id)
    result = waiting_on_tasks(tasks)
    assert result[0].title == "Beta"
    assert result[1].title == "Alpha"


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
    # Moved to WO without a date — no longer in Today.
    assert today_tasks(tasks) == []


def test_move_to_waiting_on_unknown_id_is_noop():
    tasks = add_task([], "Task")
    result = move_to_waiting_on(tasks, "bad-id")
    assert len(today_tasks(result)) == 1  # original task still in Today


def test_add_waiting_on_task_has_default_scheduled_date():
    tasks = add_waiting_on_task([], "Call Alice")
    expected = date.today() + timedelta(days=7)
    assert tasks[0].scheduled_date == expected


def test_move_to_waiting_on_sets_default_scheduled_date():
    tasks = add_task([], "Buy milk")
    task_id = tasks[0].id
    tasks = move_to_waiting_on(tasks, task_id)
    expected = date.today() + timedelta(days=7)
    assert tasks[0].scheduled_date == expected


def test_move_to_waiting_on_preserves_existing_scheduled_date():
    tasks = add_task([], "Already scheduled")
    task_id = tasks[0].id
    custom_date = date.today() + timedelta(days=14)
    tasks = schedule_task(tasks, task_id, custom_date)
    tasks = move_to_waiting_on(tasks, task_id)
    assert tasks[0].scheduled_date == custom_date


def test_insert_waiting_on_task_after_places_between():
    tasks = add_waiting_on_task([], "First")
    tasks = add_waiting_on_task(tasks, "Third")
    first_id = next(t.id for t in tasks if t.title == "First")
    tasks = insert_waiting_on_task_after(tasks, first_id, "Second")
    wo = waiting_on_tasks(tasks)
    assert [t.title for t in wo] == ["First", "Second", "Third"]


def test_insert_waiting_on_task_before_places_between():
    tasks = add_waiting_on_task([], "First")
    tasks = add_waiting_on_task(tasks, "Third")
    third_id = next(t.id for t in tasks if t.title == "Third")
    tasks = insert_waiting_on_task_before(tasks, third_id, "Second")
    wo = waiting_on_tasks(tasks)
    assert [t.title for t in wo] == ["First", "Second", "Third"]


def test_insert_waiting_on_task_after_sets_scheduled_date():
    tasks = add_waiting_on_task([], "Anchor")
    anchor_id = tasks[0].id
    tasks = insert_waiting_on_task_after(tasks, anchor_id, "New")
    new_task = next(t for t in tasks if t.title == "New")
    assert new_task.scheduled_date == date.today() + timedelta(days=7)


def test_insert_waiting_on_task_after_unknown_anchor_falls_back():
    tasks = add_waiting_on_task([], "Existing")
    tasks = insert_waiting_on_task_after(tasks, "no-such-id", "Appended")
    wo = waiting_on_tasks(tasks)
    assert wo[-1].title == "Appended"


# ------------------------------------------------------------------ #
# Generic folder positional insertion                                 #
# ------------------------------------------------------------------ #


def test_insert_folder_task_after_places_between():
    tasks = add_task_to_folder([], "someday", "First")
    tasks = add_task_to_folder(tasks, "someday", "Third")
    first_id = next(t.id for t in tasks if t.title == "First")
    tasks = insert_folder_task_after(tasks, "someday", first_id, "Second")
    result = folder_tasks(tasks, "someday")
    assert [t.title for t in result] == ["First", "Second", "Third"]


def test_insert_folder_task_before_places_between():
    tasks = add_task_to_folder([], "someday", "First")
    tasks = add_task_to_folder(tasks, "someday", "Third")
    third_id = next(t.id for t in tasks if t.title == "Third")
    tasks = insert_folder_task_before(tasks, "someday", third_id, "Second")
    result = folder_tasks(tasks, "someday")
    assert [t.title for t in result] == ["First", "Second", "Third"]


def test_insert_folder_task_after_unknown_anchor_falls_back():
    tasks = add_task_to_folder([], "someday", "Existing")
    tasks = insert_folder_task_after(tasks, "someday", "no-such-id", "Appended")
    result = folder_tasks(tasks, "someday")
    assert result[-1].title == "Appended"


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
    assert len(waiting_on_tasks(result)) == 1


# ------------------------------------------------------------------ #
# Upcoming smart view                                                  #
# ------------------------------------------------------------------ #


def test_upcoming_tasks_returns_future_dated():
    tasks = add_task([], "Future")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=3))
    tasks = add_task(tasks, "Active")
    result = upcoming_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Future"


def test_upcoming_tasks_includes_waiting_on_future():
    tasks = add_waiting_on_task([], "WO future")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=5))
    result = upcoming_tasks(tasks)
    assert len(result) == 1


def test_upcoming_tasks_excludes_someday():
    tasks = add_task_to_folder([], "someday", "Someday task")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=3))
    assert upcoming_tasks(tasks) == []


def test_upcoming_tasks_excludes_past():
    tasks = add_task([], "Overdue")
    tasks = schedule_task(tasks, tasks[0].id, date.today() - timedelta(days=1))
    assert upcoming_tasks(tasks) == []


def test_upcoming_tasks_sorted_by_date():
    tasks: list[Task] = []
    tasks = add_task(tasks, "Later")
    tasks = add_task(tasks, "Sooner")
    later_id = next(t.id for t in tasks if t.title == "Later")
    sooner_id = next(t.id for t in tasks if t.title == "Sooner")
    tasks = schedule_task(tasks, later_id, date.today() + timedelta(days=10))
    tasks = schedule_task(tasks, sooner_id, date.today() + timedelta(days=3))
    result = upcoming_tasks(tasks)
    assert result[0].title == "Sooner"
    assert result[1].title == "Later"


def test_upcoming_tasks_as_of_parameter():
    tasks = add_task([], "Task")
    target = date(2026, 4, 1)
    tasks = schedule_task(tasks, tasks[0].id, target)
    assert upcoming_tasks(tasks, as_of=date(2026, 3, 31)) == [tasks[0]]
    assert upcoming_tasks(tasks, as_of=date(2026, 4, 1)) == []


# ------------------------------------------------------------------ #
# Someday folder                                                       #
# ------------------------------------------------------------------ #


def test_someday_tasks_returns_someday_folder():
    tasks = add_task_to_folder([], "someday", "Park this")
    result = someday_tasks(tasks)
    assert len(result) == 1
    assert result[0].title == "Park this"


def test_someday_tasks_never_in_today():
    tasks = add_task_to_folder([], "someday", "Parked")
    assert today_tasks(tasks) == []


def test_someday_tasks_with_date_not_in_upcoming():
    tasks = add_task_to_folder([], "someday", "Someday with date")
    tasks = schedule_task(tasks, tasks[0].id, date.today() + timedelta(days=3))
    assert upcoming_tasks(tasks) == []


# ------------------------------------------------------------------ #
# parse_repeat_input                                                   #
# ------------------------------------------------------------------ #


def test_parse_repeat_input_days():
    assert parse_repeat_input("7 days") == (7, "days")


def test_parse_repeat_input_day_singular():
    assert parse_repeat_input("1 day") == (1, "days")


def test_parse_repeat_input_abbreviation_d():
    assert parse_repeat_input("7d") == (7, "days")


def test_parse_repeat_input_weeks():
    assert parse_repeat_input("2 weeks") == (2, "weeks")


def test_parse_repeat_input_abbreviation_w():
    assert parse_repeat_input("2w") == (2, "weeks")


def test_parse_repeat_input_months():
    assert parse_repeat_input("1 month") == (1, "months")


def test_parse_repeat_input_abbreviation_m():
    assert parse_repeat_input("3m") == (3, "months")


def test_parse_repeat_input_years():
    assert parse_repeat_input("1 year") == (1, "years")


def test_parse_repeat_input_abbreviation_y():
    assert parse_repeat_input("2y") == (2, "years")


def test_parse_repeat_input_empty_returns_none():
    assert parse_repeat_input("") is None
    assert parse_repeat_input("   ") is None


def test_parse_repeat_input_invalid_raises():
    import pytest

    with pytest.raises(InvalidRepeatError):
        parse_repeat_input("every week")
    with pytest.raises(InvalidRepeatError):
        parse_repeat_input("0 days")
    with pytest.raises(InvalidRepeatError):
        parse_repeat_input("2 fortnights")


# ------------------------------------------------------------------ #
# set_repeat_rule                                                      #
# ------------------------------------------------------------------ #


def test_set_repeat_rule_stores_rule():
    tasks = add_task([], "Daily standup")
    task_id = tasks[0].id
    rule = RepeatRule(interval=1, unit="days", next_due=date(2026, 4, 1))
    tasks = set_repeat_rule(tasks, task_id, rule)
    assert tasks[0].repeat_rule == rule


def test_set_repeat_rule_clears_rule():
    tasks = add_task([], "Task")
    task_id = tasks[0].id
    rule = RepeatRule(interval=7, unit="days", next_due=date(2026, 4, 1))
    tasks = set_repeat_rule(tasks, task_id, rule)
    tasks = set_repeat_rule(tasks, task_id, None)
    assert tasks[0].repeat_rule is None


def test_set_repeat_rule_unknown_id_is_noop():
    tasks = add_task([], "Task")
    rule = RepeatRule(interval=7, unit="days", next_due=date(2026, 4, 1))
    result = set_repeat_rule(tasks, "bad-id", rule)
    assert result[0].repeat_rule is None


# ------------------------------------------------------------------ #
# spawn_repeating_tasks                                                #
# ------------------------------------------------------------------ #

_TODAY = date(2026, 3, 15)  # fixed reference date for all spawn tests


def _task_with_rule(title: str, interval: int, unit: str, next_due: date) -> list:
    """Create a repeating task in the 'projects' folder (not Today) so that the
    spawned copy is the only instance of the title visible in Today."""
    tasks = add_task_to_folder([], "projects", title)
    rule = RepeatRule(interval=interval, unit=unit, next_due=next_due)
    return set_repeat_rule(tasks, tasks[0].id, rule)


def test_spawn_creates_copy_when_due():
    tasks = _task_with_rule("Weekly review", 7, "days", _TODAY)
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    today_list = today_tasks(result)
    titles = [t.title for t in today_list]
    assert "Weekly review" in titles


def test_spawn_copy_has_no_repeat_rule():
    tasks = _task_with_rule("Weekly review", 7, "days", _TODAY)
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    copies = [
        t for t in result if t.title == "Weekly review" and t.folder_id == "today"
    ]
    assert len(copies) == 1
    assert copies[0].repeat_rule is None


def test_spawn_advances_next_due():
    tasks = _task_with_rule("Weekly review", 7, "days", _TODAY)
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    original = next(t for t in result if t.id == original_id)
    assert original.repeat_rule is not None
    assert original.repeat_rule.next_due == _TODAY + timedelta(days=7)


def test_spawn_skips_future_tasks():
    future = _TODAY + timedelta(days=1)
    tasks = _task_with_rule("Future repeat", 7, "days", future)
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    assert len(result) == len(tasks)  # no new task added


def test_spawn_handles_multiple_missed_periods():
    """If the app wasn't opened for 2+ intervals, spawn one copy and advance past all."""
    two_weeks_ago = _TODAY - timedelta(days=14)
    tasks = _task_with_rule("Daily", 7, "days", two_weeks_ago)
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    # Exactly one copy spawned
    copies = [t for t in result if t.title == "Daily" and t.folder_id == "today"]
    assert len(copies) == 1
    # next_due is now in the future
    original = next(t for t in result if t.id == original_id)
    assert original.repeat_rule.next_due > _TODAY


def test_spawn_no_rule_task_unchanged():
    tasks = add_task([], "Plain task")
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    assert len(result) == 1
    assert result[0].folder_id == "today"


def test_spawn_positions_copy_at_top_of_today():
    tasks = add_task([], "Existing task")
    existing_id = tasks[0].id
    tasks += _task_with_rule("Repeater", 7, "days", _TODAY)
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    ordered = today_tasks(result)
    assert ordered[0].title == "Repeater"
    existing = next(t for t in result if t.id == existing_id)
    assert existing.position > 0


def test_spawn_multiple_repeaters_all_placed_at_top():
    tasks = add_task([], "Existing")
    tasks += _task_with_rule("Alpha", 7, "days", _TODAY)
    tasks += _task_with_rule("Beta", 7, "days", _TODAY)
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    today_list = today_tasks(result)
    top_titles = {t.title for t in today_list[:2]}
    assert {"Alpha", "Beta"} == top_titles


def test_spawn_monthly_advances_correctly():
    next_due = date(2026, 2, 28)
    tasks = _task_with_rule("Monthly", 1, "months", next_due)
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    original = next(t for t in result if t.id == original_id)
    assert original.repeat_rule.next_due == date(2026, 3, 28)


def test_spawn_yearly_advances_correctly():
    next_due = date(2026, 1, 1)
    tasks = _task_with_rule("Yearly", 1, "years", next_due)
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    original = next(t for t in result if t.id == original_id)
    assert original.repeat_rule.next_due == date(2027, 1, 1)


def test_spawn_today_folder_task_gets_scheduled_date():
    """A repeat-rule task in the 'today' folder gets scheduled_date = next_due after
    spawning so it no longer appears in Today's active list — only in Upcoming.
    This prevents the user from accidentally completing the template task."""
    tasks = add_task([], "Daily habit")  # folder_id="today"
    rule = RepeatRule(interval=1, unit="days", next_due=_TODAY)
    tasks = set_repeat_rule(tasks, tasks[0].id, rule)
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    original = next(t for t in result if t.id == original_id)
    expected_next = _TODAY + timedelta(days=1)
    assert original.scheduled_date == expected_next
    # The original must NOT appear in Today's active list (its date is now in the future).
    assert original not in today_tasks(result, as_of=_TODAY)
    # The spawned copy (no repeat_rule) must appear in Today.
    copies = [t for t in result if t.title == "Daily habit" and t.repeat_rule is None]
    assert len(copies) == 1
    assert copies[0] in today_tasks(result, as_of=_TODAY)


def test_spawn_non_today_folder_task_unchanged_scheduled_date():
    """A repeat-rule task NOT in the 'today' folder is not given a scheduled_date."""
    tasks = _task_with_rule("Weekly review", 7, "days", _TODAY)  # folder="projects"
    original_id = tasks[0].id
    result = spawn_repeating_tasks(tasks, as_of=_TODAY)
    original = next(t for t in result if t.id == original_id)
    assert original.scheduled_date is None


# ------------------------------------------------------------------ #
# search_tasks                                                         #
# ------------------------------------------------------------------ #


def test_search_matches_title():
    tasks = add_task([], "Buy groceries")
    results = search_tasks(tasks, "groceries")
    assert len(results) == 1
    assert results[0][0].title == "Buy groceries"


def test_search_matches_notes():
    tasks = add_task([], "Meeting", notes="discuss quarterly budget")
    results = search_tasks(tasks, "budget")
    assert len(results) == 1
    assert results[0][1] == "notes"


def test_search_case_insensitive():
    tasks = add_task([], "Buy Milk")
    assert len(search_tasks(tasks, "milk")) == 1
    assert len(search_tasks(tasks, "MILK")) == 1
    assert len(search_tasks(tasks, "Milk")) == 1


def test_search_empty_query_returns_empty():
    tasks = add_task([], "Some task")
    assert search_tasks(tasks, "") == []
    assert search_tasks(tasks, "   ") == []


def test_search_no_match_returns_empty():
    tasks = add_task([], "Buy groceries")
    assert search_tasks(tasks, "dentist") == []


def test_search_returns_match_type_title():
    tasks = add_task([], "Budget review")
    results = search_tasks(tasks, "budget")
    assert results[0][1] == "title"


def test_search_title_match_before_notes_match():
    tasks: list = []
    tasks = add_task(tasks, "Budget review")
    tasks = add_task(tasks, "Meeting", notes="discuss budget")
    results = search_tasks(tasks, "budget")
    assert results[0][1] == "title"
    assert results[1][1] == "notes"


def test_search_active_before_logbook():
    tasks = add_task([], "Buy milk")
    tasks = add_task(tasks, "Buy bread")
    logbook_id = tasks[-1].id
    tasks = complete_task(tasks, logbook_id)
    results = search_tasks(tasks, "buy")
    # active results appear first in the list
    active_indices = [i for i, r in enumerate(results) if r[0].folder_id != "logbook"]
    logbook_indices = [i for i, r in enumerate(results) if r[0].folder_id == "logbook"]
    assert max(active_indices) < min(logbook_indices)


def test_search_logbook_only_when_no_active_match():
    tasks = add_task([], "Buy milk")
    task_id = tasks[0].id
    tasks = complete_task(tasks, task_id)
    results = search_tasks(tasks, "buy")
    assert len(results) == 1
    assert results[0][0].folder_id == "logbook"


def test_search_does_not_return_unmatched():
    tasks: list = []
    tasks = add_task(tasks, "Buy groceries")
    tasks = add_task(tasks, "Call dentist")
    results = search_tasks(tasks, "groceries")
    titles = [r[0].title for r in results]
    assert "Buy groceries" in titles
    assert "Call dentist" not in titles


# ---------------------------------------------------------------------------
# BACKLOG-6: Recurring tasks (completion-relative scheduling)
# ---------------------------------------------------------------------------


def test_complete_recurring_task_spawns_new_task():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert len(active) == 1
    assert active[0].title == "Floss"


def test_complete_recurring_task_new_task_has_correct_scheduled_date():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    completed = next(t for t in tasks if t.folder_id == "logbook")
    active = [t for t in tasks if t.folder_id != "logbook"]
    expected = completed.completed_at.date() + timedelta(days=1)
    assert active[0].scheduled_date == expected


def test_complete_recurring_task_preserves_recur_rule():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert active[0].recur_rule == rule


def test_complete_recurring_weekly_task_scheduled_date():
    tasks = add_task([], "Weekly review")
    rule = RecurRule(interval=1, unit="weeks")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    completed = next(t for t in tasks if t.folder_id == "logbook")
    active = [t for t in tasks if t.folder_id != "logbook"]
    expected = completed.completed_at.date() + timedelta(weeks=1)
    assert active[0].scheduled_date == expected


def test_complete_task_without_recur_rule_does_not_spawn():
    tasks = add_task([], "One-off task")
    tasks = complete_task(tasks, tasks[0].id)
    assert all(t.folder_id == "logbook" for t in tasks)


def test_complete_repeat_rule_task_spawns_new_template():
    """Completing a task with a repeat_rule spawns a new template so the repeat
    schedule is not lost. The new template has a future scheduled_date so it
    only appears in Upcoming, not in Today's active list."""
    tasks = add_task([], "Weekly review")
    rule = RepeatRule(
        interval=7, unit="days", next_due=date.today() + timedelta(days=7)
    )
    tasks = set_repeat_rule(tasks, tasks[0].id, rule)
    task_id = tasks[0].id
    tasks = complete_task(tasks, task_id)
    completed = next(t for t in tasks if t.id == task_id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert completed.folder_id == "logbook"
    assert len(active) == 1
    template = active[0]
    assert template.repeat_rule is not None
    assert template.repeat_rule.next_due > date.today()
    assert template.scheduled_date is not None
    assert template.scheduled_date > date.today()
    # Template must not appear in Today's active list (it has a future date).
    assert template not in today_tasks(tasks)
    # Template must appear in Upcoming.
    assert template in upcoming_tasks(tasks)


def test_complete_repeat_rule_task_advances_past_today_if_overdue():
    """If next_due is today or in the past, it must be advanced until strictly future."""
    tasks = add_task([], "Daily habit")
    yesterday = date.today() - timedelta(days=1)
    rule = RepeatRule(interval=1, unit="days", next_due=yesterday)
    tasks = set_repeat_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert len(active) == 1
    assert active[0].scheduled_date is not None
    assert active[0].scheduled_date > date.today()


def test_complete_recurring_task_new_task_in_today_folder():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=3, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert active[0].folder_id == "today"


def test_set_recur_rule_stores_rule_on_task():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=2, unit="weeks")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    assert tasks[0].recur_rule == rule


def test_set_recur_rule_can_clear_rule():
    tasks = add_task([], "Floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = set_recur_rule(tasks, tasks[0].id, None)
    assert tasks[0].recur_rule is None


def test_complete_recurring_task_new_task_notes_preserved():
    tasks = add_task([], "Floss", notes="Use waxed floss")
    rule = RecurRule(interval=1, unit="days")
    tasks = set_recur_rule(tasks, tasks[0].id, rule)
    tasks = complete_task(tasks, tasks[0].id)
    active = [t for t in tasks if t.folder_id != "logbook"]
    assert active[0].notes == "Use waxed floss"


# ---------------------------------------------------------------------------
# BACKLOG-21: created_at is set on task creation
# ---------------------------------------------------------------------------


def test_add_task_sets_created_at():
    from datetime import datetime

    tasks = add_task([], "Buy milk")
    assert tasks[0].created_at is not None
    assert isinstance(tasks[0].created_at, datetime)


def test_insert_task_after_sets_created_at():
    from gtd_tui.gtd.operations import insert_task_after

    tasks = add_task([], "First")
    anchor_id = tasks[0].id
    tasks = insert_task_after(tasks, anchor_id, "Second")
    new_task = next(t for t in tasks if t.title == "Second")
    assert new_task.created_at is not None


def test_add_task_to_folder_sets_created_at():
    from gtd_tui.gtd.operations import add_task_to_folder

    tasks = add_task_to_folder([], "myfolder", "Widget")
    assert tasks[0].created_at is not None


# ---------------------------------------------------------------------------
# move_block_down / move_block_up
# ---------------------------------------------------------------------------


def _make_today_tasks(*titles: str) -> list:
    """Create today tasks with titles in display order (first title = top)."""
    tasks: list = []
    for title in reversed(titles):
        tasks = add_task(tasks, title)
    return tasks


def _titles(tasks: list) -> list[str]:
    return [t.title for t in sorted(tasks, key=lambda t: t.position)]


def test_move_block_down_moves_block_as_unit():
    tasks = _make_today_tasks("A", "B", "C", "D", "E")
    ids = {t.id for t in tasks if t.title in ("B", "C", "D")}
    tasks = move_block_down(tasks, ids)
    assert _titles(tasks) == ["A", "E", "B", "C", "D"]


def test_move_block_up_moves_block_as_unit():
    tasks = _make_today_tasks("A", "B", "C", "D", "E")
    ids = {t.id for t in tasks if t.title in ("B", "C", "D")}
    tasks = move_block_up(tasks, ids)
    assert _titles(tasks) == ["B", "C", "D", "A", "E"]


def test_move_block_down_noop_at_boundary():
    tasks = _make_today_tasks("A", "B", "C")
    ids = {t.id for t in tasks if t.title in ("B", "C")}
    tasks = move_block_down(tasks, ids)
    assert _titles(tasks) == ["A", "B", "C"]


def test_move_block_up_noop_at_boundary():
    tasks = _make_today_tasks("A", "B", "C")
    ids = {t.id for t in tasks if t.title in ("A", "B")}
    tasks = move_block_up(tasks, ids)
    assert _titles(tasks) == ["A", "B", "C"]


def test_move_block_down_single_task():
    tasks = _make_today_tasks("A", "B", "C")
    ids = {t.id for t in tasks if t.title == "A"}
    tasks = move_block_down(tasks, ids)
    assert _titles(tasks) == ["B", "A", "C"]


def test_move_block_up_single_task():
    tasks = _make_today_tasks("A", "B", "C")
    ids = {t.id for t in tasks if t.title == "C"}
    tasks = move_block_up(tasks, ids)
    assert _titles(tasks) == ["A", "C", "B"]
