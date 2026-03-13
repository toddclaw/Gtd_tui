from gtd_tui.gtd.operations import add_task, complete_task, logbook_tasks, today_tasks
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
